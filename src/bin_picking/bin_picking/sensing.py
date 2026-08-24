# -*- coding: utf-8 -*-
"""볼트 6D 자세 구독과 외부 비전 입력. _all_bolt_poses 단일 입구 소유.

SensingMixin 은 IntegratedPickPlace 에 섞이는 책임 단위다(상태는 노드가 소유).
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




class SensingMixin:

    # ---- gz 프레임 이름 → 볼트 id (순수 함수, ROS 없이 검증 가능) ----
    @classmethod
    def _bolt_id_from_frame(cls, name):
        """gz 프레임 이름에서 'bolt_<숫자>' id 를 뽑는다. 없으면 None.

        브리지가 주는 이름은 환경에 따라 제각각이다:
          'bolt_3' / '/bolt_3' / 'bolt_3::bolt' / 'world/bolt_3/bolt'
        예전 필터는 정확히 'bolt_<숫자>' 인 것만 받아, 링크 스코프 이름이 오면
        전부 조용히 버려졌다(= 센싱 0개 → BOLT_LAYOUT 폴백으로 운전).
        'bolt_bin'/'drop_bin' 은 숫자가 아니므로 자연히 걸러진다.
        """
        if not name:
            return None
        m = cls.BOLT_ID_RE.search(name.lstrip('/'))
        return m.group(1) if m else None

    def _log_frame_diag(self, msg, topic_bid):
        """[진단] 실제로 수신되는 프레임 이름을 처음 한 번만 INFO 로 덤프."""
        if self._frame_diag_done:
            return
        for t in msg.transforms:
            pair = (f'{self.POSE_TOPIC_FMT.format(topic_bid)}: '
                    f'{t.header.frame_id or "(빈)"} -> '
                    f'{t.child_frame_id or "(빈)"}')
            if pair not in self._frame_diag:
                if len(self._frame_diag) >= self.FRAME_DIAG_MAX:
                    break
                self._frame_diag.append(pair)
        self._frame_diag_n += 1
        # 토픽이 볼트 수만큼 있으므로, 모든 토픽이 한 번씩 울릴 여유를 준다.
        need = max(self.FRAME_DIAG_CALLBACKS, 2 * len(BOLT_LAYOUT))
        if (self._frame_diag_n < need
                and len(self._frame_diag) < self.FRAME_DIAG_MAX):
            return
        self._frame_diag_done = True
        names = '\n  '.join(self._frame_diag)
        self.get_logger().info(
            f'[센싱 진단] {self.POSE_TOPIC_FMT.format("bolt_<n>")} 에서 실제로 '
            f'수신한 프레임 이름 {len(self._frame_diag)}종 '
            f'(topic: parent -> child):\n'
            f'  {names}\n'
            f'  → 이 중 bolt_<숫자> 로 인식된 볼트: '
            f'{sorted(self._bolt_sensed) or "없음"}')

    def _bolt_pose_cb(self, msg, topic_bid):
        """/model/<볼트>/pose(TFMessage)에서 그 볼트의 실제 6D 자세를 추림.

        topic_bid 는 구독 토픽에서 온 볼트 id — 프레임 이름과 달리 절대 비지
        않으므로 이것을 신원의 최종 근거로 삼는다.
        """
        self._log_frame_diag(msg, topic_bid)
        got = False
        for t in msg.transforms:
            # ⚠ 부모가 볼트면(예: 'bolt_0' -> 'bolt_0::bolt') 그 값은 '모델 기준
            #   링크 자세'(≈원점)이지 월드 좌표가 아니다. 그대로 받으면 실제 월드
            #   위치를 (0,0,0) 으로 덮어써 통 밖으로 팔을 보낸다.
            #   월드(또는 이름 없는) 부모의 항목만 신뢰한다.
            if self._bolt_id_from_frame(t.header.frame_id) is not None:
                continue
            # child 이름이 있으면 토픽과 같은 볼트인지 교차 검증한다. 이름이
            # 비어 있어도(브리지가 못 채워도) 토픽이 신원을 확정하므로 받는다.
            child_bid = self._bolt_id_from_frame(t.child_frame_id)
            if child_bid is not None and child_bid != topic_bid:
                continue
            tr = t.transform.translation
            q = t.transform.rotation
            self._bolt_sensed[topic_bid] = ((tr.x, tr.y, tr.z),
                                            (q.x, q.y, q.z, q.w))
            self._sense_seq += 1
            got = True
        if got and not self._sensing_logged:
            self._sensing_logged = True
            self.get_logger().info(
                '볼트 위치 센싱 수신 시작 — 실제 6D 자세로 집습니다(폴백 아님)')

    def _ext_pose_cb(self, msg):
        """[외부 비전 입력] 최적 볼트 6D 자세 수신."""
        self._ext_pose = msg
        self._ext_pose_fresh = True

    # ---- 볼트 실제 위치 기반 조회 ----
    def _bolt_pose(self, i):
        """볼트 i 의 (위치, 쿼터니언). 센싱값 우선, 없으면 BOLT_LAYOUT 폴백."""
        p = self._bolt_sensed.get(f'bolt_{i}')
        if p is not None:
            return p
        dx, dy, dz, yaw = BOLT_LAYOUT[i]
        q = tf_transformations.quaternion_from_euler(0.0, 0.0, yaw)
        return ((BIN_XYZ[0] + dx, BIN_XYZ[1] + dy,
                 BIN_XYZ[2] + BOLT_REST_Z + dz),
                (q[0], q[1], q[2], q[3]))

    def _all_bolt_poses(self):
        """모든 볼트의 {id: (pos, quat)}. 센싱이 하나라도 있으면 센싱값,
        전혀 없으면 BOLT_LAYOUT 폴백.

        ⚠ 이 함수가 이웃 판정의 '유일한' 입구다. 예전엔 _bolt_sensed 를 직접
        돌았기 때문에, pose 브리지가 없는 폴백 모드에서 이웃이 항상 0개로 보였다
        → 하강 전 임시 제거가 no-op 이 되어 13mm 옆 이웃과 충돌하며
        fraction 87.5% 에서 하강이 죽었다. 두 모드에서 동일하게 동작해야 한다.
        """
        if self._bolt_sensed:
            return dict(self._bolt_sensed)
        return {f'bolt_{i}': self._bolt_pose(i)
                for i in range(len(BOLT_LAYOUT))}

    def _match_sensed_bolt(self, pos, tol=0.04):
        """주어진 위치와 가장 가까운(tol 이내) 센싱 볼트 id. 없으면 None."""
        best, best_d = None, tol
        for bid, (p, _q) in self._all_bolt_poses().items():   # 폴백 모드 포함
            if bid in self._picked:
                continue
            d = math.dist(pos[:2], p[:2])
            if d < best_d:
                best, best_d = bid, d
        return best

    def _trigger_cb(self, _msg):
        self._trigger_received = True

    def _wait_for_trigger(self, prompt):
        """/next_step 토픽 메시지가 올 때까지 블로킹 대기"""
        self.get_logger().info(prompt)
        self._trigger_received = False
        while rclpy.ok() and not self._trigger_received:
            rclpy.spin_once(self, timeout_sec=0.1)
        if not rclpy.ok():
            raise KeyboardInterrupt('종료 신호 수신 — 시퀀스 중단')
