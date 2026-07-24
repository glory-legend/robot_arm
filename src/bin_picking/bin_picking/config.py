# -*- coding: utf-8 -*-
"""빈피킹 데모의 모든 상수(로봇/파지깊이/개구/도달성/학습 등).

PickPlaceConfig 를 노드가 상속하므로 self.X/cls.X 참조가 그대로 동작한다.
값과 유도 주석은 원본 그대로 — 이 주석들이 "왜 이 값인지"의 자산이다.
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




class PickPlaceConfig:
    # ---------- 로봇 / 그리퍼 상수 (ex07) ----------
    PLANNING_GROUP = 'fr3_arm'
    REFERENCE_FRAME = 'fr3_link0'
    END_EFFECTOR_LINK = 'fr3_hand_tcp'
    ARM_JOINTS = ['fr3_joint1', 'fr3_joint2', 'fr3_joint3',
                  'fr3_joint4', 'fr3_joint5', 'fr3_joint6', 'fr3_joint7']

    GRIPPER_JOINT = 'fr3_finger_joint1'   # joint2는 mimic — 명령에 넣지 않음
    GRIPPER_ACTION = '/fr3_gripper_controller/follow_joint_trajectory'
    GRIPPER_OPEN = 0.04
    # 완전 0.0으로 닫으면 시뮬레이션 물리 오차로 finger 관절이 한계를
    # 미세하게 벗어나(-0.0001 등) 이후 MoveGroup 계획이 즉시 실패할 수 있음.
    # 0.002 → 0.0015: 볼트(샤프트 반경 4mm)를 문 상태에서 지령-실측 편차가
    # 커질수록 위치 제어기가 더 세게 조인다 → 더 타이트한 파지(운반 중 미끄럼
    # 방지). 0 근접의 관절 한계 이탈 문제는 여전히 피한다.
    # ※ GRASP_DETECT_MIN 이 이 값에서 유도되므로 판정 경계도 자동 보정된다.
    GRIPPER_CLOSED = 0.0015

    # ---------- 파지 성공 판정 (빈손 오탐 방지) ----------
    # 액션 error_code 로는 '볼트를 물고 멈춤'과 '허공에서 끝까지 닫힘'을 구분할 수
    # 없다(GOAL_TOLERANCE_VIOLATED 는 양쪽 모두에서 난다). 그래서 /joint_states 의
    # fr3_finger_joint1 '실측 위치'로 판정한다. 이 관절값은 손가락 하나의 중심
    # 이격이므로, 물체를 물면 그 물체의 '반경'에서 멈춘다.
    #   허공         → 지령값 GRIPPER_CLOSED(0.002) 까지 그대로 닫힘
    #   M8 샤프트 파지 → 샤프트 반경 0.004 부근에서 정지
    BOLT_SHAFT_RADIUS = 0.004   # SDF m8_bolt 샤프트 반경. bolt_scene.BOLT_RADIUS
                                # (0.007)는 머리를 감싼 '보수적 충돌' 반경이라
                                # 파지 판정에는 쓰면 안 된다.
    # 임계값 = (허공 0.002 + 샤프트 0.004) / 2 = 0.003 — 두 모집단의 중점.
    # 물리 오차(±0.5mm)를 감안해도 어느 쪽으로도 넘어가지 않는 위치다.
    GRASP_DETECT_MIN = (GRIPPER_CLOSED + BOLT_SHAFT_RADIUS) / 2.0   # 0.003
    # 상한: 머리(반경 0.0065)를 물어도 통과해야 하고, '아예 닫히지 않음'
    # (pre-grasp 개구 12mm 이상에 머물러 있음)은 걸러야 한다 → 0.0065 + 2.5mm
    GRASP_DETECT_MAX = 0.009
    # 0.8 → 0.4: 파지 판정을 '손끝 폭'이 아니라 '리프트 후 볼트 상승'(지상진실)로
    # 바꿔서, 닫힘 후 손끝 정착을 오래 기다릴 필요가 없다(그 값은 참고용 로그).
    # gripper_close 액션은 이미 완료를 기다리므로 0.4 면 충분히 안정된다.
    GRASP_SETTLE_SEC = 0.4      # 닫힘 안정 대기(샘플링 전)

    MARKER_TOPIC = '/pick_place_markers'

    # ---------- 시나리오 상수 ----------
    # 집는 통(bolt_bin)의 무더기에서 볼트를 하나씩 집어, 놓는 통(drop_bin) 안의
    # '빈 슬롯' 위에서 툭 떨어뜨린다(바닥까지 내려가지 않음).
    # 볼트 좌표는 가능하면 Gazebo 실제 6D 자세(pose 브리지)를 쓰고, 없으면
    # BOLT_LAYOUT(bolt_scene 공유)로 폴백한다.
    # 볼트별 pose 토픽 (spawn_bolts.launch.py 의 POSE_TOPIC_FMT 와 동일해야 함).
    # m8_bolt 모델의 PosePublisher 플러그인이 볼트마다 자기 월드 자세를 발행하고,
    # 런치가 볼트당 브리지를 하나씩 띄운다. 토픽 이름 자체가 볼트 신원이므로
    # 프레임 이름이 비어 오더라도 어느 볼트인지 절대 헷갈리지 않는다.
    POSE_TOPIC_FMT = '/model/{}/pose'
    # ---------- 파지 깊이 (재유도: 이전 상수는 바닥에 끼여 하강이 잘렸다) ----------
    # [기하 사실]
    #   통 바닥 충돌박스 상면  BIN_FLOOR_TOP = BIN_XYZ.z + BIN_THICK = 0.005
    #   통 벽 상단            BIN_WALL_TOP  = BIN_XYZ.z + BIN_OUTER.z = 0.025
    #   바닥에 누운 볼트 중심 = 바닥상면 + 샤프트반경 = 0.005 + 0.004 = 0.009
    #                        (실측 센싱값은 z ≈ 0.010 — 거의 일치)
    #   그 볼트의 샤프트는 z = 0.006 ~ 0.014 를 차지한다.
    #
    # [이전 설정이 틀린 이유]
    #   GRASP_DEPTH_OFFSET(4mm) 를 무조건 빼서 목표 z = 0.010-0.004 = 0.006 →
    #   바닥 한계 0.007 로 클램프. 바닥 충돌박스 상면(0.005)과 겨우 2mm 차이라
    #   하강 마지막 구간이 충돌/역기구학 한계에 걸려 잘렸다(달성률 93.3%).
    #   게다가 '더 깊이'는 바닥에 누운 볼트에서는 물리적으로 불가능하다 —
    #   샤프트 아래에는 바닥밖에 없다.
    #
    # [재유도]
    #   TCP(fr3_hand_tcp)는 손가락 '끝' 평면이고 손가락은 거기서 위로 뻗는다.
    #   따라서 TCP 를 볼트 중심 z 에 두면 손가락이 샤프트 상반부(중심~+4mm)를
    #   옆에서 문다 → 원기둥 측면 파지로 충분하다. 굳이 중심 아래로 내려갈
    #   이유가 없고, 내려가면 바닥만 긁는다.
    #   깊이 파고들기는 '다른 볼트 위에 얹힌' 볼트에만 적용한다(아래 _grasp_z_for).
    BIN_FLOOR_TOP = BIN_XYZ[2] + BIN_THICK            # = 0.005
    BIN_WALL_TOP = BIN_XYZ[2] + BIN_OUTER[2]          # = 0.025
    # 바닥에 '그냥 누운' 볼트의 기준 중심 z. 이보다 높으면 무언가에 얹힌 것이다.
    BOLT_REST_CENTER_Z = BIN_FLOOR_TOP + BOLT_SHAFT_RADIUS   # = 0.009
    GRASP_DEPTH_OFFSET = 0.004       # (레거시, 아래 _grasp_z_for 에서 미사용)
    # ★★ [근본원인 수정 — 서브에이전트 냉정 분석으로 확정] ★★
    # fr3_hand_tcp(TCP)는 손끝이 아니라 손끝(고무패드 최저면)보다 9.5mm '위'다.
    # URDF franka_hand.xacro 추적: finger_joint origin(0.0584)+rubber-tip 박스
    # 중심(0.04525)+박스반높이(0.00925)=손끝 0.1129 vs tcp_xyz 0.1034 → 0.0095.
    # 예전 코드는 'TCP=손끝'으로 착각해 목표 z 를 바닥 아래로 잡았고(물리 불가),
    # 물리 바닥이 손끝을 막아 TCP 가 늘 목표보다 9.5mm 위에서 멈췄다(로그 실측
    # 0.0147~0.0148 = 바닥상면 0.005 + 오프셋 0.0095, 0.2mm 오차로 일치).
    TCP_TO_FINGERTIP = 0.0095        # TCP z − 손끝(패드 최저면) z
    GRASP_FLOOR_CLEAR = 0.0005       # 손끝이 통 바닥 상면 위로 남길 여유(0.5mm)
    # 하드 바닥 TCP: 손끝이 바닥 상면 위 GRASP_FLOOR_CLEAR 를 유지하는 TCP 높이.
    #   = 바닥상면 + 손끝오프셋 + 여유 = 0.005 + 0.0095 + 0.0005 = 0.015
    GRASP_FLOOR_Z = BIN_FLOOR_TOP + TCP_TO_FINGERTIP + GRASP_FLOOR_CLEAR    # 0.015
    # ---------- 하강 완주 검증 (Issue A) ----------
    # MIN_FRACTION(0.9) 은 '이동' 구간에는 맞지만 '파지 하강'에는 치명적이다.
    # 0.45 → 0.009 하강(0.441m)에서 93.3% 는 TCP z ≈ 0.0385 — 볼트보다 29mm
    # 위다. 거기서 손가락을 닫으면 반드시 빈손이다.
    # → 하강 전용으로 훨씬 엄격한 게이트를 쓰고, 실행 뒤 FK 로 실제 도달 z 까지
    #   재확인한다(계획상 100% 라도 컨트롤러가 못 따라갔을 수 있으므로).
    GRASP_MIN_FRACTION = 0.995       # 하강 전용 fraction 게이트
    GRASP_Z_TOL = 0.003              # 실행 후 실측 TCP z 허용 초과분(3mm)
    # ---------- 적응형 하강 깊이 ----------
    # 바닥 충돌모델을 유지한 채 '계획이 통과하는 가장 깊은 z'를 탐색한다.
    # 원래 목표가 계획상 막히면(바닥/기구학 무엇이든) 2mm 씩 올려 재계획하되,
    # 손가락이 샤프트 상반부(중심~+4mm)를 물 수 없는 높이까지는 안 올라간다.
    GRASP_RAISE_STEP = 0.002         # 하강 목표 상향 재계획 간격
    # 0.002 → 0.006: 적응형 하강 z_cap = 볼트중심 + 이 값. 바닥 볼트의 목표
    # grasp_z 가 이제 0.015(=GRASP_FLOOR_Z)이므로 0.002(z_cap=0.012)면 while
    # 루프가 목표를 못 돌린다. 0.006(z_cap=0.016)이면 0.015 를 허용한다.
    GRASP_MAX_ABOVE = 0.006
    # 하강 직전 자세 재취득(3b) 허용 오차. 이보다 많이 움직였으면 접근 자세/개구가
    # 더 이상 유효하지 않으므로 이번 시도를 깨끗이 취소하고 다음 사이클에 재계획.
    POSE_REFRESH_TOL = 0.004
    # 놓기: 놓는 통 '안'의 빈 슬롯 위에서 툭 떨어뜨린다(바닥까지 안 내려감).
    DROP_Z = 0.040                   # 놓는 순간 TCP 높이 — 통 벽(0.025) 위
                                     # (너무 높으면 볼트가 튀어 통 밖으로 나감)
    DROP_SLOT_DX = 0.070             # 놓는 통 안 슬롯 간격 (x)
    DROP_SLOT_DY = 0.060             # 놓는 통 안 슬롯 간격 (y)
    SLOT_CLEAR_R = 0.055             # 볼트 반길이×2(0.050)+여유 — 이 안에 있으면 '자리 참'
    # 손가락 반경(0.050) + 이웃 볼트 반길이(0.025). 중심간 거리로 판정하므로
    # 이보다 작으면 이웃 몸통 끝이 손가락 영역 안으로 들어온다.
    PICK_CLEAR_R = 0.075             # 파지 하강 전 임시 제거할 이웃 반경
    MAX_PICK_RETRY = 3               # 같은 볼트 연속 실패 허용 횟수(무한 재시도 방지)
    # ---------- 블랙리스트: '진전 없는' 재시도 상한 (Issue C) ----------
    # '연속 실패'를 그냥 세면, 사이 사이에 다른 볼트를 성공적으로 집어 무더기가
    # 바뀌었는데도 벌점이 쌓여 멀쩡한 볼트를 버리게 된다. 반대로 매번 리셋하면
    # 아무것도 성공하지 못하는 상황에서 영원히 같은 볼트를 재시도한다.
    # → '마지막 성공 파지 이후'(= 같은 진전 epoch 안에서)의 실패만 센다.
    #   무더기가 실제로 바뀌면(성공 파지) epoch 가 올라 스트릭이 리셋되고,
    #   아무 진전이 없으면 상한에 도달해 영구 블랙리스트로 간다 → 루프가 끝난다.
    MAX_NO_PROGRESS = 3

    # ---------- 동적 그리퍼 개구(aperture) 최적화 상수 ----------
    # '최적 파지 자세'에는 위치·각도뿐 아니라 '얼마나 벌리고 내려갈지'도 포함된다.
    # 항상 만개(40mm/손가락)로 내려가면 벽 근처/이웃이 가까운 볼트에서 손가락이
    # 먼저 부딪힌다. → 벽 제약과 이웃 제약을 풀어 개구를 좁혀서 내려간다.
    # 통 안쪽 사각형 반치수(레이캐스트 대상). 외형/2 - 벽두께 = (0.115, 0.095)
    BIN_INNER_HALF = (BIN_OUTER[0] / 2.0 - BIN_THICK,
                      BIN_OUTER[1] / 2.0 - BIN_THICK)
    # [SRDF/URDF 준수] 손끝 팁 반폭(닫힘축 Y 방향). URDF franka_hand.xacro 의
    # 팁 패드 collision box(22e-3 x 8.8e-3 x 3.8e-3)에서 닫힘축=8.8mm → 반 4.4mm.
    # 임의 튜닝값(6/10mm)이 아니라 실제 모델 치수를 그대로 쓴다.
    FINGER_HALF_W = 0.0044
    # ---------- 사각(평면) 손가락 팁 기하 (R2) ----------
    # 실제 Franka Hand 팁은 중심선(선분)이 아니라 '사각/직사각 평면'이다. 닫힘축
    # (y_tool)뿐 아니라 볼트 축 방향(x_tool)으로도 폭이 있어(팁 약 18mm), 그 모서리가
    # 벽/이웃에 먼저 스치면 하강 Cartesian 달성률이 떨어진다. 그래서 벽 레이캐스트와
    # 이웃 스윕을 x_tool 방향으로 ±이 반폭만큼 평행이동해 팁 '면'을 근사한다.
    # [SRDF/URDF 준수] URDF 팁 패드 축방향(X)=22mm → 반 11mm.
    FINGER_TIP_HALF_X = 0.011
    GRASP_SAFETY = 0.003     # 벽/접근에 대한 여유 (3mm)
    # 손가락이 '닫히는 동안' 훑는 구간(스윕)에 대한 여유. 하강 중 충돌은 팔이
    # 통을 들이받는 크래시지만, 닫으면서 이웃을 스치는 건 상대적으로 경미하므로
    # GRASP_SAFETY 보다 완화해 잡는다(너무 엄격하면 빽빽한 무더기에서 집을 수
    # 있는 볼트가 거의 없어진다 — 아래 트레이드오프 주석 참고).
    SWEEP_SAFETY = 0.0015    # 스윕 전용 여유 (1.5mm)
    GRASP_MIN_OPEN = 0.009   # 개구 하한. 손가락 팁 반폭 6mm + 샤프트 반경 4mm 를
                             # 감안한 최소 — 이보다 좁으면 샤프트를 밀어낸다.
    # 파지 '목표' 개구(pre-grasp). 벽/이웃이 더 좁히라고 강제하지 않는 한, 항상
    # 이 타이트한 폭으로 내려간다. 예전엔 벽/이웃에 '처음 닿는' 폭(최대 40mm)을
    # 그대로 썼는데, 그러면 빽빽한 무더기에서 손가락이 이웃과 부딪혀 하강
    # Cartesian 이 중간(≈93%)에서 잘렸다.
    # 18→12→10mm 로 더 조였다: 손가락 팁 반폭 6mm 기준, 개구 10mm 면 손가락
    # 안쪽면이 파지점에서 4mm(=샤프트 반경)로 샤프트에 딱 붙어 내려간다. 닫힘
    # 이동거리가 최소라 닫는 동안 볼트가 밀려 구를 틈이 없고(진짜 타이트),
    # 손가락 옆폭도 좁아 벽/이웃과의 충돌 여지가 준다.
    GRASP_PREGRASP_OPEN = 0.010
    APERTURE_STEP = 0.004    # 이웃 회피용 개구 하향 탐색 간격 (4mm)
    APERTURE_SCAN_R = 0.090  # 개구 제약을 검사할 이웃 볼트 탐색 반경(xy)
    APERTURE_SELF_TOL = 0.006  # 이 거리 안의 볼트는 '대상 자신'으로 보고 제외
                               # (외부 pose 로 id 매칭이 안 된 경우 대비)
    # ---------- 비수직(6D) 접근 방향 탐색 (Issue D) ----------
    # 항상 z_tool=(0,0,-1) 로만 내려가면, 벽에 붙은 볼트는 벽쪽 손가락이 먼저
    # 닿아 개구가 안 나온다('그리퍼가 들어갈 공간이 없음').
    # ⚠ 물리 주의: 접근방향을 '볼트 축과 정렬'하면 원기둥 끝면으로 들이받는
    #   꼴이라 절대 집을 수 없다. 우리가 원하는 건 손가락 닫힘축을 볼트 축과
    #   수직으로 유지한 채(=지금 그대로) '기울여서' 접근하는 것이다.
    # 구현: 접근방향을 '볼트 축 a 를 회전축으로' 돌린다.
    #   - a 를 축으로 도는 회전은 a·z_tool 을 보존한다 → x_tool 과 볼트 축의
    #     어긋난 각도가 기울기와 무관하게 일정하다(θ=0 일 때와 정확히 동일).
    #     즉 attach_bolt 의 '볼트축 = hand X' 전제가 기울여도 그대로 유지된다.
    #   - 동시에 손가락 닫힘축 y_tool 이 a 둘레로 같이 돌아 수평면에서 들린다
    #     → 벽쪽 손가락이 벽 '위로' 넘어가 개구 여유가 생긴다. 바로 우리가
    #       원하는 효과다(통 벽 높이는 20mm 밖에 안 된다).
    TILT_CANDIDATES_DEG = (15.0, 30.0)   # 크기만. 부호는 '벽 반대쪽'으로 자동 선택
    # [수직 선호 프라이어] 학습 랭킹에서 기울임 후보에 얹는 점수 페널티(도당).
    # 기울임은 손목을 크게 꺾어 관절 한계 실패 위험이 커진다(과거 로그의
    # J7 ±170° 실패들). 학습 초기엔 모델 점수가 노이즈라 수직과 기울임이
    # 비슷한 점수로 나오는데, 그때마다 굳이 기울여 들어가는 것을 막는다.
    # [사용자 지시: 수직이 되면 무조건 수직] 페널티를 대폭 키운다. 15°=0.30,
    # 30°=0.60 감점 → 기울인 후보는 웬만한 점수 우위(관절여유 등)로도 수직을
    # 못 이긴다. 결과적으로 '수직으로 집을 수 있는 볼트'가 항상 먼저 선택되고,
    # 기울임은 수직이 아예 불가능한(벽에 딱 붙은) 볼트에서만 채택된다.
    TILT_PRIOR_PENALTY = 0.02
    EXT_POSE_TOPIC = '/next_bolt_pose'   # 외부 비전이 최적 볼트 6D 자세를 던지는 곳
    EXT_POSE_WAIT = 3.0              # 외부 자세 대기 시간(초). 없으면 자체 선택
    STEP_BY_STEP = True              # True면 사이클마다 /next_step 대기(수동 진행)
                                     # False면 연속 자동 운전
    # ---------- 학습형 파지 선택기 (R1~R4) ----------
    # True 이고 선택기가 준비(ready)되면, '어느 볼트를 어느 각도로' 집을지를
    # SGDClassifier 성공확률 랭킹으로 고른다. False 로 끄면 완전히 기존 동작
    # (_select_topmost_bolt 휴리스틱)으로 돌아간다 — 회귀 안전장치.
    USE_LEARNED_SELECTOR = True
    SELECTOR_REFIT_EVERY = 20        # 이 횟수마다 attempts.jsonl 전체 재적합 + 저장
    WARM_START_EPOCHS = 300          # warm start 배치 반복(에폭) 수
    # ---------- plan-only 롤아웃(내부 시뮬레이션 기반 선택) ----------
    # 볼트를 실제로 집으러 가기 '전에', 후보들을 팔을 움직이지 않고 계획만
    # 해본다(plan_only=True + compute_cartesian 은 실행 없이 fraction 만 반환).
    # 그 결과(접근 도달성/하강 달성률/관절 여유)를 실제로 시뮬레이션해 점수화한
    # 뒤, '이긴 후보 하나만' 실제로 실행한다 → 실패할 움직임은 화면에서 안 보이고,
    # 최종 최적 동작만 보여진다. 사용자 요구: "백그라운드로 수십~수백 번 시뮬 후
    # 최적만 실행". (로봇 궤적 계획은 서비스 호출이라 '수천 번'은 학습 쪽 얘기.)
    ROLLOUT_ENABLE = True
    ROLLOUT_TOPK = 12                # 학습/기하 점수 상위 몇 개까지 실제로 계획-시뮬
    ROLLOUT_MIN_FRACTION = 0.995     # 시뮬 하강이 이 이상이면 '직선 통과'로 인정
    # ---------- 도달성 사전 필터 / 기울임 게이트 (서브에이전트 확정) ----------
    # 수직 파지의 좌우 도달 한계는 |y − 통중심| ≈ 61(성공)~68(실패)mm. 이보다
    # 좌우로 먼 '구석' 볼트는 어떤 접근으로도 못 잡으므로, 후보 열거 전에 조기
    # 제외한다(사후 블랙리스트로 볼트당 60초 낭비하던 것을 없앤다).
    REACH_Y_MAX = 0.063              # |y − 통중심| 이 넘으면 도달 불가로 스킵(좌우)
    REACH_X_FAR = 0.45               # 이보다 앞쪽(x)이면 하강 깊이 부족으로 스킵
    # 기울임 허용 최소 볼트중심 z. 바닥 볼트(중심 0.010)를 기울이면 손끝이 TCP보다
    # 9.5mm 아래라 바닥을 1.6~2.9mm 파고든다(θ=15~30°). '다른 볼트 위에 확실히
    # 얹힌' 볼트(중심 ≥ 0.020)만 기울여야 손끝이 바닥 위에 남는다.
    TILT_MIN_CENTER_Z = 0.020
    # 데이터/모델 영속 경로(런타임 홈 기준). __init__ 에서 expanduser 확정.
    ATTEMPTS_REL = '~/pick_place_logs/attempts.jsonl'
    MODEL_REL = '~/pick_place_logs/selector_model.pkl'
    # 집는 통(bolt_bin)을 planning-scene 에 등록할지 + '바닥 박스'를 포함할지.
    # [확정된 사실] 통을 없앤 맨바닥에선 볼트가 집혔다 → 통 '바닥 충돌 박스'가
    # 그리퍼 하강을 막던 범인이다(사용자 확인). 그래서:
    #   USE_PICK_BIN=True   → 벽은 등록(운반 중 벽 회피 유지)
    #   PICK_BIN_FLOOR=False → 바닥 박스는 빼서 하강을 막지 않는다
    # 물리 통(Gazebo)은 그대로라 볼트는 통 안 바닥(z≈0.010)의 집기 좋은 높이에
    # 앉고, 실제 바닥 접촉은 GRASP_FLOOR_Z(0.009 하한)가 막는다.
    USE_PICK_BIN = True
    PICK_BIN_FLOOR = False
    # 센싱 없이는 파지 금지. 센싱이 죽으면 '스폰 시점의 공중 좌표'(폴백)로
    # 내려가 허공만 쥔다(20260721 로그의 연속 빈손). '현재' 볼트 위치를 모르는
    # 채 파지를 시작하는 일을 원천 차단한다. 폴백만으로 돌리려면 False.
    REQUIRE_SENSING = True
    # 접근/운반 높이. 0.45 → 0.25 로 낮췄다: 통 벽은 25mm 뿐이라 0.25 로도
    # 여유가 10배이고, 하강 직선이 0.44m → 0.24m 로 절반이 되어 IK 가 관절
    # 한계/점프에 걸릴 구간 자체가 줄어든다(길수록 실패 확률만 커진다).
    APPROACH_HEIGHT = 0.25
    DESCENT_STEP = 0.05               # Cartesian 하강 waypoint 간격 (5cm)
    CART_MAX_STEP = 0.01              # Cartesian 보간 간격 (1cm)
    MIN_FRACTION = 0.9                # ex05 fraction 게이트

    # ex10: 어려운 구간에서 순차 시도할 OMPL 플래너 후보.
    # 앞쪽(RRTConnect)이 대부분 성공하지만, 좁은 공간에서 실패하면
    # 좁은 공간에 강한 EST/KPIECE로 넘어가며 재시도한다.
    # ⚠ planner_id 는 ompl_planning.yaml 의 <group>: planner_configs 에 있는
    #   '설정 이름'이어야 한다('RRTConnect' 같은 알고리즘 이름이 아님).
    #   이름이 안 맞으면 MoveIt 이 조용히 기본 플래너로 폴백해 폴백이 no-op 이 된다.
    PLANNER_FALLBACK = ['RRTConnectkConfigDefault', 'RRTkConfigDefault',
                        'ESTkConfigDefault', 'KPIECEkConfigDefault',
                        'PRMkConfigDefault']

    # ---------- 센싱 프레임 이름 진단 ----------
    # /model/<n>/pose 를 TFMessage 로 브리지하면 child_frame_id 가 'bolt_0' 일
    # 수도, 'bolt_0::bolt'(링크 스코프) 일 수도 있다. 어떤 이름이 실제로 오는지
    # 모르면 필터가 조용히 전부 버려도 알 길이 없으므로, 처음 몇 콜백의 프레임
    # 이름을 딱 한 번 찍어 준다.
    # (과거 SceneBroadcaster 의 /world/<w>/pose/info 를 쓰던 시절엔 이름이 전부
    #  빈 채로 도착했다 — 이 진단이 그 사실을 밝혀냈으므로 그대로 유지한다.)
    FRAME_DIAG_CALLBACKS = 5     # 이만큼 콜백을 모은 뒤 출력하고 종료
    FRAME_DIAG_MAX = 20          # 출력할 최대 고유 이름 수
    # 'bolt_<숫자>' 를 :: 또는 / 로 구분된 어느 세그먼트에서든 뽑아낸다.
    # 매칭: 'bolt_3', '/bolt_3', 'bolt_3::bolt', 'world/bolt_3/bolt'
    # 비매칭: 'bolt_bin', 'drop_bin', 'bolt'(숫자 없음)
    BOLT_ID_RE = re.compile(r'(?:^|::|/)(bolt_\d+)(?=::|/|$)')

    # ---------- 마커 색상 ----------
    COLOR_GENERAL = ColorRGBA(r=1.0, g=0.5, b=0.0, a=0.95)  # 주황: 일반 계획
    COLOR_CART = ColorRGBA(r=0.2, g=0.8, b=1.0, a=0.95)     # 시안: Cartesian
    COLOR_TEXT = ColorRGBA(r=1.0, g=1.0, b=1.0, a=1.0)

    # ---------- FR3 관절 위치 한계 (rad) — 실패 진단용 ----------
    JOINT_LIMITS = {
        'fr3_joint1': (-2.7437, 2.7437),
        'fr3_joint2': (-1.7837, 1.7837),
        'fr3_joint3': (-2.9007, 2.9007),
        'fr3_joint4': (-3.0421, -0.1518),
        'fr3_joint5': (-2.8065, 2.8065),
        'fr3_joint6': (0.5445, 4.5169),
        'fr3_joint7': (-3.0159, 3.0159),
    }
    LIMIT_MARGIN = 0.10   # 한계로부터 이 이내(rad, ≈5.7°)면 '근접' 경고

    # ---------- 통신 타임아웃 (무한 대기 방지) ----------
    ACCEPT_TIMEOUT = 15.0    # 액션 goal 수락 대기
    RESULT_TIMEOUT = 120.0   # 계획/실행 결과 대기 (데모 동작엔 매우 넉넉)
    SERVICE_TIMEOUT = 30.0   # FK / Cartesian / Scene / 파라미터 서비스

    # 기본(수직) 접근방향. 기울기 탐색의 θ=0 후보이기도 하다.
    APPROACH_DOWN = (0.0, 0.0, -1.0)

    # ---------- 같은 접근 자세 반복 방지 ----------
    # 입력(볼트 위치)이 그대로면 계획도 결정적이라, 같은 자세로 다시 시도해 봐야
    # 결과도 똑같다. 실패한 (위치, 기울기) 조합을 기억해 두고, 재시도에서는
    # 남은 다른 기울기부터 쓴다. 남은 자세가 없으면 3회를 채우지 않고 즉시
    # 포기한다. 볼트가 실제로 움직였거나(위치 변화 > TRIED_POS_TOL) 무더기가
    # 바뀌면(epoch 증가) 상황이 달라진 것이므로 기억을 리셋한다.
    TRIED_POS_TOL = 0.005

    # 롤아웃에서 접근 자세를 여러 IK 분기로 탐색할 때 쓰는 시드들.
    # 7축 로봇은 같은 손끝 pose 라도 팔꿈치 방향(J1/J3/J4/J7)에 따라 도달
    # 가능/불가가 갈린다. ready 하나만으로 IK 를 풀면 늘 같은 분기만 나와,
    # '그 분기로는 못 내려가는' 볼트를 통째로 놓친다. 관절값을 흔든 여러 시드를
    # 주면 compute_ik 가 서로 다른 분기해를 내놓아, 깊이 도달하는 자세를 찾는다.
    # [사용자 지시: 팔+그리퍼 공동 탐색] 롤아웃이 (그리퍼 접근각) × (팔 IK 분기)를
    # 함께 돈다. 3 = ready + 흔든 시드 3개. 비용은 tilt 게이트(바닥볼트는 수직
    # 후보만 → 후보 급감) + line_ok 조기종료 + line_ok 시 grasp IK 생략으로 제어.
    # 3 → 1: 낱개분리(전부 수직·도달권 내)에선 ready 시드로 거의 항상 하강이
    # 완주해 seed0 에서 break 된다. 팔 분기 탐색은 이제 저비용 폴백 1개로 충분.
    # (무더기·기울임으로 돌아가면 다시 3~5 로 올릴 것.)
    IK_SEED_JITTER = 1               # ready 외 추가 시드 수(팔 IK 분기 폴백)
    IK_SEED_SPREAD = 1.2             # 흔드는 폭(rad) — 관절 한계 안에서 클램프
