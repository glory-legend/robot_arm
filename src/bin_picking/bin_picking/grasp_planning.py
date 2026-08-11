# -*- coding: utf-8 -*-
"""파지 계획: 그리퍼 개구·접근 기울기·통 벽/도달성 판정.

GraspPlanningMixin 은 IntegratedPickPlace 에 섞이는 책임 단위다(상태는 노드가 소유).
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




class GraspPlanningMixin:

    def _wall_reach_along(self, p, d):
        """파지점 p 에서 방향 d(단위벡터)로 손가락이 갈 때, 통 벽에 막히기까지의
        '경로 길이'. 막히지 않으면 inf.

        수직 접근에서는 d 가 수평이라 예전처럼 xy 레이캐스트 그대로다. 기울인
        접근에서는 d 에 z 성분이 생기므로 두 가지를 더 따진다:
          1) 수평 성분이 |d_h| 뿐이므로, 수평거리 t 를 벌려면 경로는 t/|d_h| 만큼
             가야 한다(경로 길이 = 개구 단위와 같은 단위여야 한다).
          2) 그 지점에서 손가락 끝 높이가 벽 상단(BIN_WALL_TOP)을 넘었으면 벽에
             막히지 않는다 → inf. TCP 는 손가락 '끝'이고 손가락은 위로 뻗으므로,
             끝이 벽을 넘었으면 손가락 전체가 넘은 것이라 보수적으로 안전하다.
             ★ 이것이 벽에 붙은 볼트를 기울여서 집을 수 있게 되는 원리다.
        """
        d = np.asarray(d, dtype=float)
        nh = float(np.linalg.norm(d[:2]))
        if nh < 1e-9:
            return float('inf')          # 수평 성분 없음 → 벽에 닿지 않는다
        t = self._ray_rect_travel(p[:2], d[:2] / nh, (BIN_XYZ[0], BIN_XYZ[1]),
                                  self.BIN_INNER_HALF)
        if t is None:
            return float('inf')          # 통 밖(외부 pose 등) → 벽 제약 없음
        s = t / nh                       # 수평거리 t 를 벌기 위한 경로 길이
        if p[2] + s * float(d[2]) >= self.BIN_WALL_TOP:
            return float('inf')          # 벽 상단을 넘어선다 → 막히지 않는다
        return s

    def _grasp_aperture(self, pos, axis, target_id=None, approach=None):
        """[동적 개구 최적화] 이 파지점에서 실제로 쓸 수 있는 손가락 개구(m).

        손가락 닫힘축 y_tool 위에서만 생각하면 된다(손가락은 그 축으로만 벌어진다).
        개구 a 일 때 손가락 바깥면은 파지점 p 에서 (a + FINGER_HALF_W) 만큼 떨어진
        두 점 p ± (a + FINGER_HALF_W)·y_tool 이다.

        1) 벽 제약 — p 에서 ±y_tool 로 통 안쪽 사각형까지 레이캐스트해 t± 를 얻고
             a_wall = min(t+, t-) - FINGER_HALF_W - GRASP_SAFETY
           (좁은 쪽이 양손가락을 다 결정한다. 그리퍼는 대칭으로 벌어지므로.)
        2) 이웃 제약 (닫힘 스윕) — 손가락은 착지 후 '닫히면서' y_tool 축을 따라
           안쪽으로 이동하므로, 최종 착지점 하나가 아니라 그 이동 구간 전체를
           봐야 한다. 개구 a 에서 각 손가락 바깥면이 훑는 구간은 선분이다:
             s_start = a + FINGER_HALF_W          (미리 벌려둔 상태)
             s_end   = GRIPPER_CLOSED + FINGER_HALF_W  (닫힘 완료)
             오른쪽 스윕 = p + s_start·y_tool → p + s_end·y_tool  (왼쪽은 −)
           이 두 스윕 선분이 모든 이웃 볼트 축 선분에서
             거리 ≥ BOLT_RADIUS + SWEEP_SAFETY
           를 만족해야 한다(선분–선분 최단거리 = _seg_seg_dist).
           ※ 점 판정만 하면 13mm 옆에 '평행하게' 누운 이웃을 손가락이 타넘어
             착지해 통과해버리고, 정작 닫을 때 그 이웃을 쓸어낸다.
           ※ 대상 볼트 자신은 반드시 제외한다 — 스윕은 정의상 대상을 관통한다
             (그게 파지다). target_id / APERTURE_SELF_TOL 로 걸러진다.
           ※ [R2] 손가락 팁은 x_tool 방향으로도 폭이 있는 '사각 평면'이다. 예전엔
             중심선 하나로 근사했지만(평행 이웃엔 영향이 적다는 이유), 비스듬히
             누운 이웃이나 벽 모서리에는 팁 모서리가 먼저 닿는다. 그래서 x_tool
             방향 ±FINGER_TIP_HALF_X 로 평행이동한 3벌의 스윕선으로 면을 근사한다.
        3) 탐색 — a_wall 에서 APERTURE_STEP 씩 낮추며 2)를 처음 통과하는 값 채택.
           GRASP_MIN_OPEN 밑으로 내려가면 들어갈 자리가 없는 것 → None.

        반환: (채택 개구 a, 벽 상한 a_wall) / 불가능하면 None
        """
        # 닫힘축 y_tool 뿐 아니라 팁의 볼트축 방향 폭(x_tool)까지 쓰려면 전체
        # 파지 프레임이 필요하다. _finger_axis_for 는 이 프레임의 y 원소일 뿐이라,
        # 여기서는 프레임을 통째로 받아 x_tool 을 사각 팁 근사에 쓴다.
        frame = self._grasp_frame(axis, approach)
        if frame is None:
            return None
        x_tool, y_tool, _z_tool = frame
        p = np.asarray(pos, dtype=float)
        half_x = self.FINGER_TIP_HALF_X

        # --- 1) 벽 제약 (사각 팁: 양쪽 모서리 각각에서 양 손가락 방향으로) ---
        # 팁이 평면이므로 파지점 p 하나가 아니라 볼트축 방향 두 모서리
        # p ± half_x·x_tool 에서 레이캐스트해, 어느 모서리든 벽에 먼저(=더 짧게)
        # 닿는 값을 취한다. 모서리가 벽에 먼저 걸리는 것을 보수적으로 반영.
        corners = (p + half_x * x_tool, p - half_x * x_tool)
        reach = min(min(self._wall_reach_along(c, y_tool),
                        self._wall_reach_along(c, -y_tool))
                    for c in corners)
        # ⚠ 개구 상한은 '만개의 물리 개구(m)'다. GRIPPER_OPEN 은 컨트롤러 지령값
        #   이라 각도 구동 그리퍼(Robotiq)에선 만개가 0.0rad → 그대로 상한에 쓰면
        #   모든 개구가 0 으로 잘려 항상 None 이 된다. 물리 개구로 변환한
        #   GRIPPER_OPEN_HALFWIDTH 를 쓴다(프랑카는 항등 변환이라 값 동일).
        if not math.isfinite(reach):
            wall_cap = self.GRIPPER_OPEN_HALFWIDTH   # 벽에 막히지 않음 → 만개까지 허용
        else:
            wall_cap = reach - self.FINGER_HALF_W - self.GRASP_SAFETY
        wall_cap = min(wall_cap, self.GRIPPER_OPEN_HALFWIDTH)
        # 1e-9 여유: 하한과 정확히 같은 값이 부동소수 오차로 탈락하지 않게
        # (아래 탐색 루프의 종료 조건과 같은 기준을 쓴다)
        if wall_cap < self.GRASP_MIN_OPEN - 1e-9:
            return None                     # 벽만으로도 이미 자리가 없다

        # --- 2) 이웃 선분 수집 (센싱/폴백 동일 경로) ---
        segs = []
        for bid, (npos, nquat) in self._all_bolt_poses().items():
            if target_id and bid == target_id:
                continue
            d = math.dist(pos[:2], npos[:2])
            if d <= self.APERTURE_SELF_TOL:
                continue                    # 대상 자신(id 매칭 실패 대비)
            if d > self.APERTURE_SCAN_R:
                continue
            segs.append(self._bolt_segment(npos, nquat))
        need = BOLT_RADIUS + self.SWEEP_SAFETY
        # 닫힘 완료 시 손가락 바깥면 위치(파지 끝점). 스윕의 안쪽 끝이다.
        # ⚠ 여기서 더하는 값은 전부 '물리 개구(m)'다. GRIPPER_CLOSED 는 컨트롤러
        #   지령값이라 각도 구동 그리퍼(Robotiq)에선 rad(0.79) 이므로, 그대로
        #   더하면 ~0.79m 짜리 스윕이 되어 모든 이웃과 충돌 판정 → 전 후보 탈락.
        #   반드시 물리 개구로 변환한 GRIPPER_CLOSED_HALFWIDTH 를 쓴다.
        #   (프랑카 핸드는 항등 변환이라 수치 동일 → 기존 동작 불변.)
        s_end = self.GRIPPER_CLOSED_HALFWIDTH + self.FINGER_HALF_W

        # --- 3) '목표 개구'에서 시작해 한 칸씩 낮추며 이웃까지 통과하는 첫 값 ---
        # 시작점을 벽 상한이 아니라 min(벽 상한, 목표 개구)로 잡는다. 벽이 넉넉해도
        # 만개로 내려가지 않고 타이트한 폭(GRASP_PREGRASP_OPEN)으로 진입 → 무더기
        # 속 하강에서 손가락이 이웃과 부딪힐 여지를 크게 줄인다. 목표 개구는
        # GRASP_MIN_OPEN 보다 크므로 이 시작값은 항상 하한 이상이다.
        a = min(wall_cap, self.GRASP_PREGRASP_OPEN)
        while a >= self.GRASP_MIN_OPEN - 1e-9:
            s_start = a + self.FINGER_HALF_W
            # 개구를 줄이면 s_start 가 작아져 스윕이 짧아지고 바깥쪽 이웃이
            # 스윕에서 빠진다 → 하향 탐색이 단조롭게 '더 안전해지는' 방향이다.
            # [R2] 사각 팁 근사: 중심선 하나가 아니라 볼트축(x_tool) 방향으로
            # -half_x, 0, +half_x 만큼 평행이동한 3개의 스윕선(각 손가락마다)으로
            # 팁의 '면'을 표현한다. 이 6개 선 전부가 모든 이웃 축선분에서 need
            # 이상 떨어져야 통과 → 팁 모서리가 이웃을 스치는 경우까지 걸러낸다.
            sweeps = []
            for ox in (-half_x, 0.0, half_x):
                base = p + ox * x_tool
                sweeps.append((base + s_start * y_tool, base + s_end * y_tool))
                sweeps.append((base - s_start * y_tool, base - s_end * y_tool))
            if all(self._seg_seg_dist(f0, f1, sa, sb) >= need
                   for (f0, f1) in sweeps
                   for (sa, sb) in segs):
                return (a, wall_cap)
            a -= self.APERTURE_STEP
        return None

    # ---------- 기울인 접근방향 탐색 (Issue D) ----------
    @classmethod
    def _wall_side_sign(cls, pos, y_tool):
        """±y_tool 중 '가까운 벽' 쪽이 어느 쪽인지 (+1 이면 +y_tool 쪽).

        기울일 때 들어올려야 하는 손가락이 바로 이쪽 손가락이다.
        """
        p = np.asarray(pos, dtype=float)
        center = (BIN_XYZ[0], BIN_XYZ[1])
        t_p = cls._ray_rect_travel(p[:2], np.asarray(y_tool[:2]), center,
                                   cls.BIN_INNER_HALF)
        t_m = cls._ray_rect_travel(p[:2], -np.asarray(y_tool[:2]), center,
                                   cls.BIN_INNER_HALF)
        if t_p is None or t_m is None:
            return 1.0
        return 1.0 if t_p <= t_m else -1.0

    @classmethod
    def _preferred_tilt_sign(cls, axis, y_tool, wall_sign):
        """벽쪽 손가락을 '위로' 들어올리는 기울기 부호(+1/−1).

        볼트 축 a 둘레로 θ 만큼 돌리면 (a·y_tool = 0 이므로)
          y(θ) = y_tool·cosθ + (a×y_tool)·sinθ
        이고, 수직 접근에서는 y_tool 의 z 성분이 0 이라
          y(θ)_z = (a×y_tool)_z · sinθ.
        벽쪽 손가락(wall_sign·y)의 z 가 양수가 되려면
          sign(θ) = sign(wall_sign · (a×y_tool)_z).
        """
        a = cls._unit(axis)
        if a is None:
            return 1.0
        cz = float(np.cross(a, np.asarray(y_tool, dtype=float))[2])
        if abs(cz) < 1e-9:
            return 1.0
        return 1.0 if wall_sign * cz > 0.0 else -1.0

    def _tilt_allowed(self, pos):
        """[기울임 게이트] 이 볼트를 기울여 접근해도 되나.

        바닥에 누운 볼트(중심 ~0.010)는 손끝이 TCP보다 9.5mm 아래라 기울이면
        한쪽 손끝이 바닥을 1.6~2.9mm 파고든다(θ=15~30°) → 충돌. '다른 볼트 위에
        확실히 얹힌' 볼트(중심 ≥ TILT_MIN_CENTER_Z)만 기울여야 손끝이 바닥 위에
        남는다. (사용자 지시 + 서브에이전트 기하 확정)
        """
        return float(pos[2]) >= self.TILT_MIN_CENTER_Z

    def _approach_candidates(self, pos, axis):
        """접근방향 후보열: 수직 먼저, 그 다음 '벽 반대쪽으로' 기울인 것부터.

        ★ 바닥 볼트(_tilt_allowed=False)는 수직 후보만 반환한다 — 기울이면 손끝이
          바닥에 박히므로. 들린 볼트만 기울임 후보를 붙인다.
        반환: [(각도°, 접근방향 3벡터), ...]
        """
        cands = [(0.0, np.asarray(self.APPROACH_DOWN, dtype=float))]
        if not self._tilt_allowed(pos):
            return cands                          # ★ 바닥 볼트: 수직만
        y0 = self._finger_axis_for(axis)          # 수직 접근 기준 닫힘축
        if y0 is None:
            return cands
        sign = self._preferred_tilt_sign(
            axis, y0, self._wall_side_sign(pos, y0))
        for deg in self.TILT_CANDIDATES_DEG:
            for s in (sign, -sign):
                th = math.radians(s * deg)
                cands.append((s * deg,
                              self._rotate_about(self.APPROACH_DOWN, axis, th)))
        return cands

    def _plan_grasp_approach(self, pos, axis, target_id=None, exclude_degs=()):
        """[Issue D] 개구가 확보되는 첫 접근방향을 찾는다(수직 → 기울임 순).

        exclude_degs: 이미 실패해서 건너뛸 기울기(round(deg)) 집합 — 같은 자세
        무의미 반복 방지(_tried_approaches)가 넘겨준다.
        반환 (각도°, 접근방향, 개구, 벽상한) / 전부 실패하면 None.
        후보 수가 5개로 고정이라 실시간 루프에서도 비용이 무시할 만하다.
        """
        for deg, approach in self._approach_candidates(pos, axis):
            if round(deg) in exclude_degs:
                continue
            ap = self._grasp_aperture(pos, axis, target_id, approach=approach)
            if ap is not None:
                return (deg, approach, ap[0], ap[1])
        return None

    def _in_bin(self, pos, bin_xyz=BIN_XYZ):
        """pos 가 해당 통 안(아직 안 집은 볼트)인지."""
        return (abs(pos[0] - bin_xyz[0]) <= 0.12
                and abs(pos[1] - bin_xyz[1]) <= 0.10
                and pos[2] < 0.06)

    def _reach_ok(self, pos):
        """[도달성 필터, 2D] 이 볼트가 수직 파지의 도달권 안인가.
        수직 아래 파지는 워크스페이스가 좁다: 좌우 |y−중심|≤REACH_Y_MAX(≈61 성공/
        68 실패), 앞뒤 x≤REACH_X_FAR(≈0.45, 그 밖은 하강이 깊이 부족으로 정체).
        둘 중 하나라도 벗어난 '구석' 볼트는 못 잡으므로 후보 열거 전에 스킵한다
        (사후 블랙리스트로 볼트당 ~60초 낭비하던 것 제거). _in_bin(±0.10)은 너무
        넓어 구석을 통과시키므로 이 가드를 따로 둔다."""
        return (abs(pos[1] - BIN_XYZ[1]) <= self.REACH_Y_MAX
                and pos[0] <= self.REACH_X_FAR)
