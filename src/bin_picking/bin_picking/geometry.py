# -*- coding: utf-8 -*-
"""순수 수학: 볼트 축·회전·파지 좌표계·선분거리·레이캐스트 (ROS 무의존).

GeometryMixin 은 IntegratedPickPlace 에 섞이는 책임 단위다(상태는 노드가 소유).
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




class GeometryMixin:

    # =========================================================
    # 볼트 자세 / 파지 각도 수학
    # =========================================================
    @staticmethod
    def bolt_axis_from_quat(quat):
        """볼트 자세(쿼터니언) → 축 단위벡터. 볼트 로컬 +X 가 축이다."""
        m = tf_transformations.quaternion_matrix(list(quat))
        return np.array([m[0][0], m[1][0], m[2][0]])

    @staticmethod
    def _unit(v):
        """단위벡터화. 길이 0 이면 None."""
        a = np.asarray(v, dtype=float)
        n = float(np.linalg.norm(a))
        return None if n < 1e-9 else a / n

    @classmethod
    def _rotate_about(cls, vec, axis, theta):
        """[순수] 로드리게스 회전 — vec 을 axis 둘레로 theta(rad) 만큼 돌린다.

          v' = v cosθ + (â×v) sinθ + â (â·v)(1−cosθ)
        """
        a = cls._unit(axis)
        v = np.asarray(vec, dtype=float)
        if a is None:
            return v
        c, s = math.cos(theta), math.sin(theta)
        return v * c + np.cross(a, v) * s + a * float(np.dot(a, v)) * (1.0 - c)

    @classmethod
    def _grasp_frame(cls, axis, approach=None):
        """[순수] 볼트 축 + 접근방향 → 파지 좌표계 (x_tool, y_tool, z_tool).

          z_tool = normalize(approach)   # 접근(하강) 방향. 기본 (0,0,-1)
          y_tool = normalize(z_tool × axis)   # 손가락 닫힘축 → 항상 볼트축과 수직
          x_tool = y_tool × z_tool

        [불변식] x_tool 은 y_tool 과 z_tool 모두에 수직이므로,
          x_tool = ±normalize(axis − (axis·z_tool)·z_tool)
        즉 '볼트 축을 접근평면에 정사영한 방향'이다. 따라서
          ∠(x_tool, axis) = arccos(√(1 − c²)),  c = axis·z_tool
        이고, 접근방향을 '볼트 축 둘레로' 돌리면 c 가 보존되므로(회전축이 axis)
        이 어긋난 각도는 기울기와 무관하게 일정하다.
        → 바닥에 누운 볼트(c=0)에서는 어떤 기울기에서도 x_tool == 볼트축(정확).
          기울어져 얹힌 볼트에서도 오차는 θ=0(수직 접근)일 때와 똑같다.
        attach_bolt 의 '볼트축 = hand X' 전제가 기울여도 깨지지 않는 근거다.

        축이 접근방향과 거의 평행하면(옆에서 감쌀 수 없음) None.
        ※ |z_tool × axis| 역시 axis 둘레 회전에 불변이므로, 이 '수직 볼트 거부'
          판정은 어떤 기울기 후보에서도 같은 답을 준다.
        """
        a = cls._unit(axis)
        z_tool = cls._unit(cls.APPROACH_DOWN if approach is None else approach)
        if a is None or z_tool is None:
            return None
        y_tool = np.cross(z_tool, a)
        ny = float(np.linalg.norm(y_tool))
        if ny < 0.20:          # 축이 접근방향과 거의 평행 → 파지 불가
            return None
        y_tool = y_tool / ny
        x_tool = np.cross(y_tool, z_tool)
        return x_tool, y_tool, z_tool

    @classmethod
    def _finger_axis_for(cls, axis, approach=None):
        """볼트 축(+접근방향) → 손가락 '닫힘 축' y_tool (단위벡터).

        grasp_quat_for_axis 와 똑같은 프레임(_grasp_frame)을 쓰므로, 파지 자세와
        개구 계산이 절대 서로 어긋날 수 없다.
        ※ 수직 접근에서는 y_tool 의 z 성분이 정확히 0(수평)이지만, 기울인
          접근에서는 0 이 아니다 → 벽 판정이 2D 라 가정하면 안 된다
          (_wall_reach_along 이 그 일반화를 담당한다).
        """
        f = cls._grasp_frame(axis, approach)
        return None if f is None else f[1]

    def grasp_quat_for_axis(self, axis, approach=None):
        """볼트 축에 맞춘 파지 자세(쿼터니언). approach 로 접근방향을 기울일 수 있다.

          R = [x_tool | y_tool | z_tool] → 쿼터니언   (프레임 정의는 _grasp_frame)

        수직 접근 + 눕힌 볼트(yaw θ)면 기존 euler(π,0,θ) 와 정확히 같은 값이다.
        볼트가 거의 수직으로 서 있으면 None → '옆에서 감쌀 수 없음'.
        """
        f = self._grasp_frame(axis, approach)
        if f is None:
            return None
        x_tool, y_tool, z_tool = f
        m = np.identity(4)
        m[0:3, 0] = x_tool
        m[0:3, 1] = y_tool
        m[0:3, 2] = z_tool
        q = tf_transformations.quaternion_from_matrix(m)
        return Quaternion(x=q[0], y=q[1], z=q[2], w=q[3])

    # ---- 순수 기하 헬퍼 (ROS 없이 단독 검증 가능) ----
    @staticmethod
    def _point_seg_dist(p, a, b):
        """점 p 와 선분 ab 사이의 최단거리. 볼트를 '축 선분'으로 볼 때 쓴다.

        투영계수 t = ((p-a)·(b-a)) / |b-a|² 를 [0,1] 로 클램프 → 선분 위 최근접점.
        """
        p = np.asarray(p, dtype=float)
        a = np.asarray(a, dtype=float)
        b = np.asarray(b, dtype=float)
        ab = b - a
        denom = float(np.dot(ab, ab))
        if denom < 1e-12:                    # 길이 0 → 점-점 거리
            return float(np.linalg.norm(p - a))
        t = float(np.clip(np.dot(p - a, ab) / denom, 0.0, 1.0))
        return float(np.linalg.norm(p - (a + t * ab)))

    @staticmethod
    def _seg_seg_dist(p1, q1, p2, q2):
        """선분 p1q1 과 선분 p2q2 사이의 최단거리 (표준 clamped 파라메트릭 해법).

        f(s,t) = |(p1 + s·d1) − (p2 + t·d2)|² 를 s,t ∈ [0,1] 에서 최소화한다.
        내부 최소점은 denom = a·e − b² 로 풀리지만, 두 선분이 평행하면 denom≈0
        이라 해가 무수히 많다 → s=0 으로 고정한 뒤 t 를 클램프하고, 클램프된 t 로
        s 를 다시 풀어 경계 위 최적점을 얻는다(퇴화: 길이 0 선분도 같은 경로로 처리).

        손가락 '스윕 구간'과 이웃 볼트 '축 선분'의 간섭 판정에 쓴다.
        """
        p1 = np.asarray(p1, dtype=float)
        q1 = np.asarray(q1, dtype=float)
        p2 = np.asarray(p2, dtype=float)
        q2 = np.asarray(q2, dtype=float)
        d1, d2, r = q1 - p1, q2 - p2, p1 - p2
        a = float(np.dot(d1, d1))      # |d1|²
        e = float(np.dot(d2, d2))      # |d2|²
        f = float(np.dot(d2, r))
        eps = 1e-12

        def clamp(v):
            return 0.0 if v < 0.0 else (1.0 if v > 1.0 else v)

        if a <= eps and e <= eps:              # 둘 다 점
            return float(np.linalg.norm(r))
        if a <= eps:                           # 선분1 이 점
            s, t = 0.0, clamp(f / e)
        else:
            c = float(np.dot(d1, r))
            if e <= eps:                       # 선분2 가 점
                t, s = 0.0, clamp(-c / a)
            else:
                b = float(np.dot(d1, d2))
                denom = a * e - b * b
                # denom≈0 → 평행. s=0 으로 두고 t 쪽에서 해를 찾는다.
                s = clamp((b * f - c * e) / denom) if denom > eps else 0.0
                t = (b * s + f) / e
                # t 가 구간을 벗어나면 t 를 경계에 고정하고 s 를 다시 푼다
                if t < 0.0:
                    t, s = 0.0, clamp(-c / a)
                elif t > 1.0:
                    t, s = 1.0, clamp((b - c) / a)
        return float(np.linalg.norm((p1 + s * d1) - (p2 + t * d2)))

    @staticmethod
    def _ray_rect_travel(p_xy, d_xy, center_xy, half_xy):
        """축정렬 사각형(통 안쪽 단면) '안'의 점 p 에서 방향 d 로 갈 때
        벽에 닿기까지의 거리 t(≥0). 슬래브(slab) 교차의 단순 버전.

        각 축마다 d>0 이면 (hi-p)/d, d<0 이면 (lo-p)/d 가 그 축 벽까지의 거리이고,
        먼저 닿는 쪽이 답이므로 둘 중 최소를 취한다. p 가 사각형 밖이면 None.
        """
        t_max = float('inf')
        for i in (0, 1):
            lo = center_xy[i] - half_xy[i]
            hi = center_xy[i] + half_xy[i]
            if p_xy[i] < lo or p_xy[i] > hi:
                return None                  # 통 밖 → 벽 제약 판단 불가
            d = d_xy[i]
            if d > 1e-9:
                t_max = min(t_max, (hi - p_xy[i]) / d)
            elif d < -1e-9:
                t_max = min(t_max, (lo - p_xy[i]) / d)
        return max(0.0, t_max)

    @classmethod
    def _bolt_segment(cls, pos, quat):
        """볼트 6D 자세 → 축 선분의 두 끝점 (numpy 3벡터 2개).

        _bolt_world_co 와 똑같은 무게중심 보정(off)을 써서, 이 선분이 씬에 등록된
        충돌 실린더와 정확히 같은 구간을 덮게 한다(모델 이중화 방지).
        """
        axis = cls.bolt_axis_from_quat(quat)
        center = np.asarray(pos, dtype=float) + ((BOLT_LEN / 2.0) - 0.020) * axis
        half = (BOLT_LEN / 2.0) * axis
        return center - half, center + half

    @classmethod
    def _grasp_z_for(cls, bolt_center_z):
        """[순수 계산] 볼트 중심 z → 실제로 내려갈 TCP z.

        ★ TCP(fr3_hand_tcp)는 파지 고무패드의 '정중앙'이다(손끝이 아니다 — 손끝은
          TCP보다 TCP_TO_FINGERTIP=9.5mm 아래). 패드가 샤프트를 대칭으로 감싸려면
          TCP 를 볼트 중심에 두는 게 이상적이다.
        단, 바닥에 누운 볼트는 손끝이 통 바닥에 막혀 TCP 가 GRASP_FLOOR_Z(0.015)
          아래로는 못 내려간다. 그 높이에서도 패드 span [TCP−9, TCP+9.5]mm 가
          샤프트(0.006~0.014)를 덮으므로 파지엔 충분하다.

        예) 바닥 볼트 중심 0.010 → max(0.015, 0.010) = 0.015 (바닥 한계 지배)
            얹힌 볼트 중심 0.024 → max(0.015, 0.024) = 0.024 (패드 중심=볼트 중심)
        """
        return max(cls.GRASP_FLOOR_Z, bolt_center_z)

    # ---------- 하강 완주 판정 (Issue A, 순수 계산) ----------
    @staticmethod
    def _fraction_to_z(z_from, z_to, fraction):
        """달성률 → 그 지점의 TCP z (수직 하강 기준). 로그/자가검증용."""
        return z_from + (z_to - z_from) * fraction

    @classmethod
    def _descent_reached(cls, achieved_z, target_z):
        """실측 TCP z 가 목표에 '실제로' 도달했는가.

        아래로 내려가는 동작이므로 목표보다 낮은 건 문제없고(바닥 한계가 따로
        막는다), 목표보다 GRASP_Z_TOL 이상 '높이' 멈춘 것만 실패다.
        """
        if achieved_z is None:
            return False              # 관측 불가 → 보수적으로 실패
        return achieved_z <= target_z + cls.GRASP_Z_TOL

    def _joint_margin(self, joint_dict):
        """관절해가 한계에서 얼마나 떨어졌나(최솟값, rad). 클수록 안전."""
        if not joint_dict:
            return 0.0
        ms = []
        for j, v in joint_dict.items():
            lo, hi = self.JOINT_LIMITS.get(j, (None, None))
            if lo is not None:
                ms.append(min(v - lo, hi - v))
        return min(ms) if ms else 0.0

    # =========================================================
    # Pose 헬퍼
    # =========================================================
    @staticmethod
    def euler_to_quaternion(roll, pitch, yaw):
        q = tf_transformations.quaternion_from_euler(roll, pitch, yaw)
        return Quaternion(x=q[0], y=q[1], z=q[2], w=q[3])

    @staticmethod
    def error_name(code_val):
        """MoveItErrorCodes 정수값 → 상수 이름 (디버깅용)"""
        for k, v in MoveItErrorCodes.__dict__.items():
            if k.isupper() and isinstance(v, int) and v == code_val:
                return k
        return str(code_val)

    @classmethod
    def _finger_width_is_grasp(cls, width):
        """[순수 판정] 손가락 실측 위치 → 물체를 물었는가.

        허공이면 지령값(GRIPPER_CLOSED=0.002)까지 그대로 닫히고, M8 샤프트를
        물면 그 반경(0.004) 부근에서 멈춘다 → 중점 0.003 을 경계로 가른다.
        상한(0.009)은 '아예 닫히지 않음'(pre-grasp 개구에 그대로 머묾)을 거른다.
        """
        if width is None:
            return False          # 관측 불가 → 보수적으로 실패 처리
        return cls.GRASP_DETECT_MIN <= width <= cls.GRASP_DETECT_MAX
