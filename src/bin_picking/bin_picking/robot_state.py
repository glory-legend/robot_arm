# -*- coding: utf-8 -*-
"""/joint_states 구독과 팔·손가락 관절 상태 조회.

RobotStateMixin 은 IntegratedPickPlace 에 섞이는 책임 단위다(상태는 노드가 소유).
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




class RobotStateMixin:

    # =========================================================
    # 공통 유틸 (콜백 / 대기)
    # =========================================================
    def _joint_state_cb(self, msg):
        self._joint_state = msg
        # 그리퍼 손가락 실측 위치도 같이 뽑아 둔다 — 파지 성공/빈손 판정의 근거.
        for n, p in zip(msg.name, msg.position):
            if n == self.GRIPPER_JOINT:
                self._finger_pos = float(p)
                self._finger_seq += 1
                break

    def _arm_joint_positions(self):
        """최신 /joint_states에서 팔 7관절을 순서대로 추림. 하나라도 없으면 None."""
        if self._joint_state is None:
            return None
        lookup = dict(zip(self._joint_state.name, self._joint_state.position))
        if not all(j in lookup for j in self.ARM_JOINTS):
            return None
        return {j: lookup[j] for j in self.ARM_JOINTS}

    def _format_joint_report(self, target=None):
        """현재 팔 자세를 사람이 읽기 좋은 표로. target(dict)이 있으면 목표/Δ도."""
        current = self._arm_joint_positions()
        if current is None:
            return '  (관절 상태 수신 전 — /joint_states 미도착)'
        lines = []
        for idx, j in enumerate(self.ARM_JOINTS, start=1):
            cur = current[j]
            seg = f'  J{idx} {j}: {cur:+.3f} rad ({math.degrees(cur):+6.1f}°)'
            if target is not None and j in target:
                tgt = target[j]
                seg += (f' | 목표 {tgt:+.3f} rad ({math.degrees(tgt):+6.1f}°)'
                        f' | Δ {cur - tgt:+.3f} rad')
            lo, hi = self.JOINT_LIMITS.get(j, (None, None))
            if lo is not None:
                if cur < lo or cur > hi:
                    seg += f'  ⛔ 한계 초과 [{lo:.3f}, {hi:.3f}]'
                elif cur - lo < self.LIMIT_MARGIN:
                    seg += f'  ⚠ 하한 근접 (여유 {cur - lo:.3f})'
                elif hi - cur < self.LIMIT_MARGIN:
                    seg += f'  ⚠ 상한 근접 (여유 {hi - cur:.3f})'
            lines.append(seg)
        return '\n'.join(lines)

    # =========================================================
    # Cartesian 경로 (ex05) — 현재 관절 상태를 start_state로
    # =========================================================
    def _current_arm_state(self):
        """/joint_states 최신값에서 팔 관절만 추려 RobotState 구성"""
        rs = RobotState()
        # ⚠ 기본 is_diff=False 면 MoveIt 이 start_state 의 attached body 를 전부
        #   지운다 → 파지한 볼트가 Cartesian 충돌검사에서 사라진다(리프트/놓기
        #   구간에서 볼트가 통 벽을 훑어도 fraction 1.0 으로 통과).
        rs.is_diff = True
        js = JointState()
        names, positions = [], []

        # start_state 에 팔 7관절뿐 아니라 그리퍼 손가락 2관절까지 넣는다.
        # ⚠ 이게 빠지면(예전 버그: allowed_joints 를 만들어 두고 필터는 ARM_JOINTS
        #   를 그대로 씀) Cartesian 충돌검사가 '미리 좁혀 둔 그리퍼'를 못 보고
        #   기본(만개) 폭으로 판단한다 → 무더기 하강이 이웃과 충돌해 fraction 이
        #   99.5% 게이트에 못 미쳐 잘린다. 하강 전 move_gripper 로 좁힌 개구가
        #   여기 실측값으로 반영돼야 MoveIt 이 '좁으니 내려갈 수 있다'고 판단한다.
        allowed_joints = self.ARM_JOINTS + self.GRIPPER_STATE_JOINTS

        for n, p in zip(self._joint_state.name, self._joint_state.position):
            if n in allowed_joints:
                names.append(n)
                positions.append(p)

        js.name = names
        js.position = positions
        rs.joint_state = js
        return rs

    def _arm_state_from(self, joint_dict):
        """주어진 관절 dict 로 RobotState 구성 — plan-only 롤아웃의 '가상 시작
        자세'용. 실제 팔은 안 움직이고, 이 자세에서 하강을 계획하면 어떤 결과가
        나올지 시뮬레이션만 한다. 그리퍼는 좁힌 폭(현재 실측)을 이어 붙인다."""
        rs = RobotState()
        rs.is_diff = True
        js = JointState()
        names = list(joint_dict.keys())
        positions = [float(v) for v in joint_dict.values()]
        # 손가락 실측도 함께 실어 좁힌 개구가 충돌검사에 반영되게 한다
        if self._joint_state is not None:
            for n, p in zip(self._joint_state.name, self._joint_state.position):
                if n in self.GRIPPER_STATE_JOINTS:
                    names.append(n)
                    positions.append(float(p))
        js.name = names
        js.position = positions
        rs.joint_state = js
        return rs
