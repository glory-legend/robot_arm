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
        # duration 미지정 시 모드별 기본값(자동 학습 모드에서는 더 빠르게)
        if duration_sec is None:
            duration_sec = self._grip_dur
        pos = float(max(0.0, min(self.GRIPPER_OPEN, position)))
        g = FollowJointTrajectory.Goal()
        g.trajectory = JointTrajectory()
        g.trajectory.joint_names = [self.GRIPPER_JOINT]
        pt = JointTrajectoryPoint()
        pt.positions = [pos]
        pt.time_from_start = Duration(
            sec=int(duration_sec),
            nanosec=int((duration_sec - int(duration_sec)) * 1e9),
        )
        g.trajectory.points.append(pt)
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
        code_val = result.result.error_code
        # 주의: 실물/실제 물체 파지 시에는 GOAL_TOLERANCE_VIOLATED가
        # "물체 두께에서 멈춤 = 파지 성공"일 수 있으므로 판정을 뒤집어야 함.
        self.get_logger().info(f'gripper {pos * 1000:.1f}mm (code={code_val})')
        return code_val == 0

    def gripper_open(self):
        return self.move_gripper(self.GRIPPER_OPEN)

    def gripper_close(self):
        return self.move_gripper(self.GRIPPER_CLOSED)

    def _sample_finger(self, settle_sec=None, timeout=2.0):
        """닫힘이 '안정된 뒤'의 fr3_finger_joint1 실측 위치를 읽는다.

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
        detail = (f'손가락 {w * 1000:.2f}mm '
                  f'(성공 범위 {self.GRASP_DETECT_MIN * 1000:.1f}~'
                  f'{self.GRASP_DETECT_MAX * 1000:.1f}mm, '
                  f'허공 기준 {self.GRIPPER_CLOSED * 1000:.1f}mm)')
        if ok:
            self.get_logger().info(f'[파지 판정] 성공 — {detail}')
        else:
            self.get_logger().error(
                f'[파지 판정] 실패(빈손 또는 미폐쇄) — {detail}')
        return ok
