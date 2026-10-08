# -*- coding: utf-8 -*-
"""그리퍼 제어(FollowJointTrajectory)와 파지 성공 판정.

GripperMixin 은 IntegratedPickPlace 에 섞이는 책임 단위다(상태는 노드가 소유).
"""
import json
import math
import os
import random
import re
import sys
import threading
import time
import xml.etree.ElementTree as ET

import numpy as np
import rclpy
import tf_transformations
from rclpy.action import ActionClient
from rclpy.node import Node
from rclpy.parameter import Parameter
from rclpy.parameter_client import AsyncParameterClient
from rclpy.qos import DurabilityPolicy, QoSProfile, ReliabilityPolicy

from builtin_interfaces.msg import Duration
from control_msgs.action import FollowJointTrajectory
from geometry_msgs.msg import Point, Pose, PoseStamped, Quaternion, Vector3
from moveit_msgs.action import ExecuteTrajectory, MoveGroup
from moveit_msgs.msg import (
    AttachedCollisionObject,
    BoundingVolume,
    CollisionObject,
    Constraints,
    JointConstraint,
    MotionPlanRequest,
    MoveItErrorCodes,
    OrientationConstraint,
    PlanningOptions,
    PlanningScene,
    PositionConstraint,
    RobotState,
)
from moveit_msgs.srv import (
    ApplyPlanningScene,
    GetCartesianPath,
    GetPositionFK,
    GetPositionIK,
)
from sensor_msgs.msg import JointState
from shape_msgs.msg import SolidPrimitive
from std_msgs.msg import ColorRGBA, Empty
from tf2_msgs.msg import TFMessage
from trajectory_msgs.msg import JointTrajectory, JointTrajectoryPoint
from visualization_msgs.msg import Marker, MarkerArray

# 볼트 통/볼트 자산 (SDF 스폰과 동일한 배치를 planning-scene에 재사용)
from bin_picking.bolt_scene import (
    BIN_OUTER,
    BIN_THICK,
    BIN_XYZ,
    BOLT_LAYOUT,
    BOLT_LEN,
    BOLT_RADIUS,
    BOLT_REST_Z,
    DROP_BIN_XYZ,
    LAYOUT_SOURCE,
    bin_collision_object,
    bolt_collision_objects,
    drop_bin_collision_object,
    object_ids as bolt_object_ids,
)

# 학습형 파지 선택기(ROS 무의존). 임포트 자체가 실패해도(파일 없음 등) 데모는
# 기존 휴리스틱으로 굴러가야 하므로 감싸 둔다 → GraspSelector=None 이면 R3 경로 비활성.
try:
    from bin_picking.grasp_selector import GraspSelector
    _SELECTOR_IMPORT_ERR = ''
except Exception as _exc:                       # noqa: BLE001
    GraspSelector = None
    _SELECTOR_IMPORT_ERR = repr(_exc)




class GripperMixin:

    # =========================================================
    # 그리퍼 (ex07)
    # =========================================================
    def move_gripper(self, position, duration_sec=None):
        """그리퍼를 지령 위치로 보낸다.

        goal 을 어떻게 만들고 결과를 어떻게 읽는지는 그리퍼 액션 타입마다 달라서
        `gripper_adapters.py` 의 어댑터가 맡는다(FollowJointTrajectory /
        GripperCommand). 여기 남는 것은 어느 그리퍼에서나 같은 부분 —
        지령값 클램프, goal 수락 대기, 결과 대기, 로깅 — 뿐이다.
        """
        # duration 미지정 시 모드별 기본값(자동 학습 모드에서는 더 빠르게)
        if duration_sec is None:
            duration_sec = self._grip_dur
        # ⚠ 클램프 범위를 open/closed 두 지령값에서 직접 구한다.
        #   예전엔 max(0.0, min(GRIPPER_OPEN, pos)) 였는데, 이는 '열림 지령이 더
        #   크고 0 이 유효 하한'이라는 프랑카 핸드의 관습을 가정한 것이다.
        #   관절값이 커질수록 닫히는 그리퍼(Robotiq 2F 계열: 0=만개, 0.79=닫힘)
        #   에서는 모든 지령이 뭉개져 그리퍼가 사실상 한 자세로 굳는다.
        lo, hi = self.ROBOT_PROFILE.gripper.command_range()
        pos = float(max(lo, min(hi, position)))
        g = self._gripper_adapter.build_goal(pos, duration_sec)
        sf = self._gripper_client.send_goal_async(g)
        handle = self._spin_future(sf, self.ACCEPT_TIMEOUT)
        if handle is None or not handle.accepted:
            self.get_logger().error('gripper goal 거부/타임아웃')
            return False
        rf = handle.get_result_async()
        result = self._spin_future(rf, self.RESULT_TIMEOUT)
        if result is None:
            self.get_logger().error('gripper 결과 타임아웃 — 컨트롤러 무응답')
            return False
        ok, detail = self._gripper_adapter.interpret(result)
        # ⚠ 지령값(pos)에 1000 을 곱해 'mm' 로 찍으면 안 된다. 그건 관절 단위가
        #   미터인 프랑카 핸드에서만 맞고, 각도 그리퍼에서는 rad×1000 이라는
        #   무의미한 숫자가 된다(Robotiq 실행에서 '완전 개방'이 "0.0mm" 로 찍혔다).
        #   사람이 읽는 값은 항상 **물리 개구**로 통일한다.
        hw = self._finger_halfwidth(pos)
        self.get_logger().info(
            f'gripper 개구 {2.0 * hw * 1000:.1f}mm '
            f'(지령 {pos:.4f}, {detail})')
        return ok

    def gripper_open(self):
        return self.move_gripper(self.GRIPPER_OPEN)

    def gripper_close(self):
        return self.move_gripper(self.GRIPPER_CLOSED)

    def _sample_finger(self, settle_sec=None, timeout=2.0):
        """닫힘이 '안정된 뒤'의 그리퍼 구동 관절(GRIPPER_JOINT) 실측 위치를 읽는다.

        닫히는 도중 값을 읽으면 아직 크게 벌어져 있어 무조건 '파지 성공'으로
        오판한다 → (1) settle 만큼 스핀하며 기다리고, (2) 그 이후에 새로 도착한
        /joint_states 를 2회 더 받아 확실히 최신 표본만 쓴다.
        """
        self._spin_sleep(self.GRASP_SETTLE_SEC if settle_sec is None
                         else settle_sec)
        start_seq = self._finger_seq
        end = time.time() + timeout
        while time.time() < end and self._finger_seq < start_seq + 2:
            rclpy.spin_once(self, timeout_sec=0.05)
        return self._finger_pos

    def check_grasp_success(self):
        """파지 성공 여부를 손가락 실측 위치로 판정. 액션 error_code 는 못 쓴다.

        FollowJointTrajectory 의 GOAL_TOLERANCE_VIOLATED 는 '볼트를 물어서 못
        닫힘'과 '허공에서 다 닫힘' 양쪽에서 모두 나므로 구분에 쓸 수 없다.
        """
        w = self._sample_finger()
        if w is None:
            self.get_logger().error(
                f'[파지 판정] /joint_states 에 {self.GRIPPER_JOINT} 없음 — '
                f'판정 불가, 실패로 처리합니다')
            return False
        ok = self._finger_width_is_grasp(w)
        # 판정과 같은 단위(물리 개구 m)로 찍는다 — 관절 단위가 다른 그리퍼에서
        # 로그와 판정 기준이 어긋나 "왜 실패로 봤는지" 못 읽는 일을 막는다.
        hw = self._finger_halfwidth(w)
        detail = (f'손가락 {hw * 1000:.2f}mm '
                  f'(성공 범위 {self.GRASP_DETECT_MIN * 1000:.1f}~'
                  f'{self.GRASP_DETECT_MAX * 1000:.1f}mm, '
                  f'허공 기준 '
                  f'{self._finger_halfwidth(self.GRIPPER_CLOSED) * 1000:.1f}mm)')
        if ok:
            self.get_logger().info(f'[파지 판정] 성공 — {detail}')
        else:
            self.get_logger().error(
                f'[파지 판정] 실패(빈손 또는 미폐쇄) — {detail}')
        return ok
