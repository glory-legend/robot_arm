# -*- coding: utf-8 -*-
"""빈피킹 데모의 모든 상수(파지깊이/개구/도달성/학습 등) + 로봇 프로파일 주입.

PickPlaceConfig 를 노드가 상속하므로 self.X/cls.X 참조가 그대로 동작한다.
값과 유도 주석은 원본 그대로 — 이 주석들이 "왜 이 값인지"의 자산이다.

[상수의 두 부류 — 이 파일을 고칠 때 반드시 지킬 경계]
  1. **작업(task) 상수** — 볼트 치수, 통 배치, 놓기 슬롯, 블랙리스트 정책, 학습기
     설정. 로봇을 갈아끼워도 그대로다 → 이 파일에 리터럴로 남는다.
  2. **기체(machine) 상수** — 관절 이름/한계, 그리퍼 지령 단위, 손끝 기하, 도달성
     한계, MoveIt 설정 위치. 업체마다 다르고 자동 추론이 불가능하다 →
     등록된 프로파일(`robot_profiles/data/<모델>.yaml`)에서 `apply_profile()` 이
     꽂는다. 새 값을 추가할 때 어느 쪽인지 먼저 정할 것.

활성 모델은 `BIN_PICKING_ROBOT_MODEL` 환경변수 → `binpick_model use` 로 저장된
선택 → 기본값('fr3') 순으로 결정된다(robot_profiles/registry.py).
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

# 등록된 로봇 모델 프로파일 — 파일 맨 아래 apply_profile() 이 소비한다
from bin_picking import robot_profiles

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
    # =====================================================================
    # ---------- 로봇 / 그리퍼 상수 — 프로파일에서 주입된다 ----------
    # =====================================================================
    # 아래 이름들은 여기에 리터럴로 적혀 있지 않다. 등록된 로봇 모델 프로파일
    # (`robot_profiles/data/<모델>.yaml`)에서 `apply_profile()` 이 이 클래스에
    # 직접 꽂는다 — 값과 그 유도 주석은 전부 그 YAML 로 옮겨 갔다.
    #
    #   PLANNING_GROUP / REFERENCE_FRAME / END_EFFECTOR_LINK / ARM_JOINTS
    #   ARM_CONTROLLER / HOME_STATE / JOINT_LIMITS / LIMIT_MARGIN
    #   GRIPPER_JOINT / GRIPPER_STATE_JOINTS / GRIPPER_ACTION
    #   GRIPPER_ACTION_TYPE / GRIPPER_CONTROLLER / GRIPPER_TOUCH_LINKS
    #   GRIPPER_OPEN / GRIPPER_CLOSED (컨트롤러 '지령값' — 단위는 그리퍼마다 다름)
    #   GRIPPER_OPEN_HALFWIDTH / GRIPPER_CLOSED_HALFWIDTH (그 지령의 물리 개구 m)
    #   TCP_TO_FINGERTIP / FINGER_HALF_W / FINGER_TIP_HALF_X
    #   GRASP_MIN_OPEN / GRASP_PREGRASP_OPEN / APERTURE_STEP
    #   REACH_Y_MAX / REACH_X_FAR / APPROACH_HEIGHT / TILT_MIN_CENTER_Z
    #   TILT_CANDIDATES_DEG / PLANNER_FALLBACK / DROP_Z
    #   GRASP_MAX_ABOVE / GRASP_FLOOR_RAISE (grasp: 섹션 — 손끝 길이 의존)
    #   ROBOT_MODEL / ROBOT_PROFILE
    #
    # [왜 클래스 속성에 꽂는가 — 인스턴스 속성이 아니라]
    #   이 파이프라인에는 `@classmethod` 로 된 순수 계산이 여럿 있고
    #   (`_grasp_z_for`, `_finger_width_is_grasp`, `_grasp_frame` …), 그것들은
    #   `cls.GRASP_FLOOR_Z` / `cls.GRASP_DETECT_MIN` 을 읽는다. 값을 인스턴스에만
    #   넣으면 classmethod 는 그 값을 **못 보고** 클래스에 남은 옛 기본값을 조용히
    #   쓴다 — 모델을 바꿨는데 파지 깊이만 이전 로봇 값으로 도는, 가장 찾기 힘든
    #   종류의 버그다. 한 프로세스에 활성 모델은 하나뿐이므로 클래스에 꽂는 것이
    #   맞고, 그래야 `self.X`/`cls.X` 두 경로가 항상 같은 값을 본다.
    #
    # [왜 기본값을 안 두는가]
    #   여기에 FR3 기본값을 남겨 두면 진실이 두 벌이 되어 반드시 어긋난다.
    #   주입 전에 읽으면 AttributeError 로 시끄럽게 죽는 편이, 옛 값으로 조용히
    #   도는 것보다 낫다.

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
    # ⚠ GRIPPER_CLOSED(프로파일)에서 유도되므로 apply_profile() 이 계산해 꽂는다.
    #   그리퍼를 바꾸면 판정 경계가 자동으로 따라오게 하기 위함이다.
    #   GRASP_DETECT_MIN = (GRIPPER_CLOSED + BOLT_SHAFT_RADIUS) / 2.0
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
    # ★★ [근본원인 수정] TCP 는 손끝이 아니다 ★★
    # TCP_TO_FINGERTIP(= TCP z − 손끝 최저면 z)은 그리퍼마다 다르므로 프로파일이
    # 준다(FR3+프랑카 핸드는 9.5mm, 유도 근거는 fr3.yaml 주석 참조). 예전 코드는
    # 'TCP=손끝'으로 착각해 목표 z 를 바닥 아래로 잡았고(물리 불가), 물리 바닥이
    # 손끝을 막아 TCP 가 늘 목표보다 그만큼 위에서 멈췄다.
    # ⚠ GRASP_FLOOR_CLEAR(손끝이 통 바닥 상면 위로 남길 여유, 0.5mm)는 그리퍼
    #   정밀도/바닥 성격에 물려 있어 프로파일 grasp: 섹션에서 apply_profile() 이
    #   꽂는다(FR3 는 0.0005 로 기존 동작 불변). 유도 근거는 각 모델 yaml 주석 참조.
    # 하드 바닥 TCP: 손끝이 바닥 상면 위 GRASP_FLOOR_CLEAR 를 유지하는 TCP 높이.
    #   = 바닥상면 + 손끝오프셋 + 여유 = 0.005 + 0.0095 + 0.0005 = 0.015 (FR3 기준)
    # ⚠ TCP_TO_FINGERTIP(프로파일)에서 유도되므로 apply_profile() 이 꽂는다.
    #   GRASP_FLOOR_Z = BIN_FLOOR_TOP + TCP_TO_FINGERTIP + GRASP_FLOOR_CLEAR
    # ---------- 하강 완주 검증 (Issue A) ----------
    # MIN_FRACTION(0.9) 은 '이동' 구간에는 맞지만 '파지 하강'에는 치명적이다.
    # 0.45 → 0.009 하강(0.441m)에서 93.3% 는 TCP z ≈ 0.0385 — 볼트보다 29mm
    # 위다. 거기서 손가락을 닫으면 반드시 빈손이다.
    # → 하강 전용으로 훨씬 엄격한 게이트를 쓰고, 실행 뒤 FK 로 실제 도달 z 까지
    #   재확인한다(계획상 100% 라도 컨트롤러가 못 따라갔을 수 있으므로).
    GRASP_MIN_FRACTION = 0.995       # 하강 전용 fraction 게이트
    # ⚠ GRASP_Z_TOL(실행 후 실측 TCP z 허용 초과분, 3mm)는 컨트롤러 추종 정확도
    #   (팔+구동계)에 민감해 프로파일 grasp: 섹션에서 apply_profile() 이 꽂는다
    #   (FR3 는 0.003 으로 기존 동작 불변).
    # ---------- 적응형 하강 깊이 ----------
    # 바닥 충돌모델을 유지한 채 '계획이 통과하는 가장 깊은 z'를 탐색한다.
    # 원래 목표가 계획상 막히면(바닥/기구학 무엇이든) 2mm 씩 올려 재계획하되,
    # 손가락이 샤프트 상반부(중심~+4mm)를 물 수 없는 높이까지는 안 올라간다.
    # ⚠ GRASP_RAISE_STEP(하강 목표 상향 재계획 간격, 2mm)는 그리퍼 기하와
    #   상호작용해 프로파일 grasp: 섹션에서 apply_profile() 이 꽂는다(FR3 는 0.002).
    # ⚠ 적응형 하강 z_cap 을 정하는 두 값 GRASP_MAX_ABOVE(볼트중심+이값 상한)와
    #   GRASP_FLOOR_RAISE(바닥 한계 지배 시 grasp_z 위 상향 여유)는 **손끝 길이에
    #   의존**하므로(손끝이 길면 grasp_z 가 튀어 z_cap 이 무효화된다) 프로파일의
    #   `grasp:` 섹션에서 apply_profile() 이 주입한다. 유도 근거는 각 모델 yaml 의
    #   grasp 주석 참조(FR3 는 max_above=0.006 / floor_raise=0.0 로 기존 동작 불변).
    # 하강 직전 자세 재취득(3b) 허용 오차. 이보다 많이 움직였으면 접근 자세/개구가
    # 더 이상 유효하지 않으므로 이번 시도를 깨끗이 취소하고 다음 사이클에 재계획.
    POSE_REFRESH_TOL = 0.004
    # 놓기: 놓는 통 '안'의 빈 슬롯 위에서 툭 떨어뜨린다(바닥까지 안 내려감).
    # ⚠ DROP_Z(놓는 순간 TCP 높이)는 그리퍼 길이에 따라 달라져 프로파일에서
    #   주입한다(apply_profile). 큰 그리퍼는 이 높이에서 손끝이 통 벽에 닿아
    #   놓기 직후 자세가 start-in-collision 이 되고 이후 계획이 전부 막힌다.
    DROP_SLOT_DX = 0.070             # 놓는 통 안 슬롯 간격 (x)
    DROP_SLOT_DY = 0.060             # 놓는 통 안 슬롯 간격 (y)
    SLOT_CLEAR_R = 0.055             # 볼트 반길이×2(0.050)+여유 — 이 안에 있으면 '자리 참'
    # ⚠ PICK_CLEAR_R(파지 하강 전 임시 제거할 이웃 반경) = 손가락 반경(0.050) +
    #   이웃 볼트 반길이(0.025). 앞 항이 그리퍼 풋프린트 성격이라 큰 그리퍼면
    #   커져야 하므로 프로파일 grasp: 섹션에서 apply_profile() 이 꽂는다(FR3 는
    #   0.075). 중심간 거리로 판정하므로 이보다 작으면 이웃 몸통 끝이 손가락
    #   영역 안으로 들어온다.
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
    # ---------- 사각(평면) 손가락 팁 기하 (R2) ----------
    # 실제 손가락 팁은 중심선(선분)이 아니라 '사각/직사각 평면'이다. 닫힘축
    # (y_tool)뿐 아니라 볼트 축 방향(x_tool)으로도 폭이 있어, 그 모서리가 벽/이웃에
    # 먼저 스치면 하강 Cartesian 달성률이 떨어진다. 그래서 벽 레이캐스트와 이웃
    # 스윕을 x_tool 방향으로 ±FINGER_TIP_HALF_X 만큼 평행이동해 팁 '면'을 근사한다.
    # ⚠ FINGER_HALF_W(닫힘축 반폭)/FINGER_TIP_HALF_X(축방향 반폭)는 그리퍼마다
    #   다르므로 프로파일이 준다. 값은 임의 튜닝이 아니라 URDF 팁 패드 collision
    #   box 치수를 그대로 옮긴 것이어야 한다(fr3.yaml 주석 참조).
    GRASP_SAFETY = 0.003     # 벽/접근에 대한 여유 (3mm)
    # 손가락이 '닫히는 동안' 훑는 구간(스윕)에 대한 여유. 하강 중 충돌은 팔이
    # 통을 들이받는 크래시지만, 닫으면서 이웃을 스치는 건 상대적으로 경미하므로
    # GRASP_SAFETY 보다 완화해 잡는다(너무 엄격하면 빽빽한 무더기에서 집을 수
    # 있는 볼트가 거의 없어진다 — 아래 트레이드오프 주석 참고).
    SWEEP_SAFETY = 0.0015    # 스윕 전용 여유 (1.5mm)
    # ⚠ 개구 하한(GRASP_MIN_OPEN)·pre-grasp 목표 개구(GRASP_PREGRASP_OPEN)·이웃
    #   회피 탐색 간격(APERTURE_STEP)은 손가락 팁 반폭과 대상 반경에서 유도되므로
    #   그리퍼마다 다르다 → 프로파일의 `gripper.aperture` 가 준다.
    #   벽/이웃이 더 좁히라고 강제하지 않는 한 항상 pre-grasp 폭으로 내려간다.
    #   (예전엔 벽/이웃에 '처음 닿는' 폭을 그대로 썼는데, 그러면 빽빽한 무더기에서
    #    손가락이 이웃과 부딪혀 하강 Cartesian 이 중간(≈93%)에서 잘렸다.)
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
    # ⚠ 기울임 후보각(TILT_CANDIDATES_DEG)은 손목 가동범위에 달렸으므로 프로파일이
    #   준다. 크기만 적고, 부호는 '벽 반대쪽'으로 자동 선택된다.
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
    CYCLE_RESULT_TOPIC = '/bin_picking/cycle_result'   # 사이클 결과(selection.py 훅 → desktop_bridge)
    COMMAND_TOPIC = '/bin_picking/command'              # desktop_bridge → pick_place_node 명령 버스
    ROBOT_PHASE_TOPIC = '/bin_picking/robot_phase'      # pick_place_node → desktop_bridge 실시간 단계
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
    # ---------- 도달성 사전 필터 / 기울임 게이트 ----------
    # ⚠ REACH_Y_MAX(좌우 도달 한계) / REACH_X_FAR(전방 한계) / TILT_MIN_CENTER_Z
    #   (기울임 허용 최소 볼트중심 z)는 팔과 설치 상태에 달린 **실측값**이라
    #   프로파일의 `workspace` 가 준다. 카탈로그 도달반경을 베껴 쓰면 안 된다.
    #   이 값으로 '어떤 접근으로도 못 잡는 볼트'를 후보 열거 전에 걸러낸다
    #   (사후 블랙리스트로 볼트당 60초 낭비하던 것을 없앤다).
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
    # ⚠ 접근/운반 높이(APPROACH_HEIGHT)는 프로파일의 `workspace` 가 준다.
    #   높을수록 하강 직선이 길어져 IK 가 관절 한계/점프에 걸릴 구간이 늘어난다
    #   → 통 벽 위 여유를 확보하는 선에서 낮게 잡는 것이 원칙이다.
    DESCENT_STEP = 0.05               # Cartesian 하강 waypoint 간격 (5cm)
    CART_MAX_STEP = 0.01              # Cartesian 보간 간격 (1cm)
    MIN_FRACTION = 0.9                # ex05 fraction 게이트

    # ex10: 어려운 구간에서 순차 시도할 OMPL 플래너 후보(PLANNER_FALLBACK).
    # 앞쪽(RRTConnect)이 대부분 성공하지만, 좁은 공간에서 실패하면
    # 좁은 공간에 강한 EST/KPIECE로 넘어가며 재시도한다.
    # ⚠ planner_id 는 그 모델의 ompl_planning.yaml 에 있는 '설정 이름'이어야 하므로
    #   MoveIt 설정 패키지마다 다르다 → 프로파일의 `workspace.planner_fallback`.
    #   이름이 안 맞으면 MoveIt 이 조용히 기본 플래너로 폴백해 폴백이 no-op 이 된다
    #   (그래서 `binpick_model verify` 가 이 이름들을 ompl 설정과 대조한다).

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

    # ---------- 관절 위치 한계 (rad) — 실패 진단용 ----------
    # ⚠ JOINT_LIMITS / LIMIT_MARGIN 은 프로파일의 `arm` 이 준다. 이 표가 실제
    #   로봇보다 넓으면 '한계 근접' 경고가 뜨지 않은 채 계획이 거부되어 진단이
    #   통째로 침묵한다 → `binpick_model verify` 가 URDF 와 대조해 경고한다.

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
    # ⚠ IK_SEED_JITTER(ready 외 추가 시드 수, 팔 IK 분기 폴백)와 IK_SEED_SPREAD
    #   (흔드는 폭 rad — 관절 한계 안에서 클램프)는 팔의 여유자유도(7축 팔꿈치
    #   분기)에 물려 있어(6축 팔은 여유자유도가 없어 seed jitter 의 의미가 다르다)
    #   프로파일 grasp: 섹션에서 apply_profile() 이 꽂는다(FR3 는 jitter=1 /
    #   spread=1.2 로 기존 동작 불변).


def apply_profile(profile, cls=PickPlaceConfig):
    """등록된 로봇 모델 프로파일을 설정 클래스에 꽂는다.

    이 함수가 "모델을 바꿔도 기능은 완전히 동일하다"의 구현부다. 파이프라인 코드는
    한 줄도 모델을 모른다 — `self.PLANNING_GROUP` 을 읽을 뿐이고, 그 값이 어느
    로봇에서 왔는지는 여기서만 결정된다.

    클래스 속성에 꽂는 이유는 클래스 상단 주석 참조(요약: `@classmethod` 순수
    계산들이 `cls.X` 로 읽기 때문에 인스턴스에만 넣으면 그것들이 옛 값을 본다).

    유도 상수는 여기서 다시 계산한다 — 그래야 그리퍼/손끝 기하가 바뀔 때 파지
    판정 경계와 바닥 한계가 **자동으로** 따라온다. 이 재계산을 빼먹으면 이름만
    새 로봇이고 물리는 옛 로봇인 상태가 되는데, 그게 가장 찾기 힘든 버그다.

    반환: 꽂은 프로파일(호출자가 로그에 쓰기 좋게).
    """
    arm, grip, ws, gr = (profile.arm, profile.gripper,
                         profile.workspace, profile.grasp)

    # --- 신원 (로그/텔레메트리에서 "지금 무슨 로봇인가"를 답할 수 있어야 한다) ---
    cls.ROBOT_MODEL = profile.name
    cls.ROBOT_PROFILE = profile

    # --- 팔 ---
    cls.PLANNING_GROUP = arm.planning_group
    cls.REFERENCE_FRAME = arm.base_frame
    cls.END_EFFECTOR_LINK = arm.tcp_frame
    # 리스트로 넘기는 이유: 기존 코드가 `self.ARM_JOINTS + [...]` 로 이어 붙인다.
    cls.ARM_JOINTS = list(arm.joints)
    cls.ARM_CONTROLLER = arm.controller
    cls.HOME_STATE = arm.home_state
    cls.JOINT_LIMITS = dict(arm.joint_limits)
    cls.LIMIT_MARGIN = arm.limit_margin

    # --- 그리퍼 ---
    cls.GRIPPER_JOINT = grip.command_joint
    cls.GRIPPER_STATE_JOINTS = list(grip.state_joints)
    cls.GRIPPER_ACTION = grip.action_name
    cls.GRIPPER_ACTION_TYPE = grip.action_type
    cls.GRIPPER_CONTROLLER = grip.controller
    cls.GRIPPER_TOUCH_LINKS = list(grip.touch_links)
    cls.GRIPPER_OPEN = grip.open_cmd
    cls.GRIPPER_CLOSED = grip.closed_cmd
    cls.TCP_TO_FINGERTIP = grip.tcp_to_fingertip
    cls.FINGER_HALF_W = grip.finger_half_w
    cls.FINGER_TIP_HALF_X = grip.finger_tip_half_x
    cls.GRASP_MIN_OPEN = grip.min_open
    cls.GRASP_PREGRASP_OPEN = grip.pregrasp_open
    cls.APERTURE_STEP = grip.aperture_step

    # --- 워크스페이스 ---
    cls.REACH_Y_MAX = ws.reach_y_max
    cls.REACH_X_FAR = ws.reach_x_far
    cls.APPROACH_HEIGHT = ws.approach_height
    cls.TILT_MIN_CENTER_Z = ws.tilt_min_center_z
    cls.TILT_CANDIDATES_DEG = tuple(ws.tilt_candidates_deg)
    cls.PLANNER_FALLBACK = list(ws.planner_fallback)
    cls.DROP_Z = ws.drop_z

    # --- 파지 알고리즘(팔/그리퍼 의존) ---
    cls.GRASP_MAX_ABOVE = gr.max_above
    cls.GRASP_FLOOR_RAISE = gr.floor_raise
    cls.GRASP_Z_TOL = gr.z_tol
    cls.GRASP_RAISE_STEP = gr.raise_step
    # ⚠ GRASP_FLOOR_CLEAR 는 아래 GRASP_FLOOR_Z 유도에 쓰이므로 반드시 먼저 꽂는다.
    cls.GRASP_FLOOR_CLEAR = gr.floor_clear
    cls.IK_SEED_JITTER = gr.ik_seed_jitter
    cls.IK_SEED_SPREAD = gr.ik_seed_spread
    cls.PICK_CLEAR_R = gr.pick_clear_r

    # --- 유도 상수 재계산 (순서 중요: 위 값들이 다 꽂힌 뒤라야 한다) ---
    # 파지 판정 하한 = (허공에서 닫히는 폭 + 대상 샤프트 반경) / 2 — 두 모집단의
    # 중점. 그리퍼 닫힘 지령이 바뀌면 경계도 같이 움직여야 한다.
    # ⚠ 물리 개구(m) 단위로 계산한다 — 닫힘 '지령값'을 그대로 쓰면 각도 구동
    #   그리퍼에서 rad 와 m 를 섞게 된다. 프랑카 핸드는 항등 변환이라 값 동일.
    cls.GRASP_DETECT_MIN = (grip.halfwidth_of(cls.GRIPPER_CLOSED)
                            + cls.BOLT_SHAFT_RADIUS) / 2.0
    # 개구 기하 계산(`_grasp_aperture`)이 쓰는 **물리 개구(m)** 판. 위의
    # GRIPPER_OPEN/GRIPPER_CLOSED 는 컨트롤러에 보내는 '지령값'이라 단위가
    # 그리퍼마다 다르다(프랑카=m, Robotiq 2F=rad). 벽까지의 거리·손가락 반폭과
    # 더하고 비교하려면 반드시 이 변환을 거친 값이어야 한다.
    # ⚠ 프랑카 핸드는 항등 변환이라 지령값과 수치가 완전히 같다 → 기존 동작 불변.
    cls.GRIPPER_OPEN_HALFWIDTH = grip.halfwidth_of(cls.GRIPPER_OPEN)
    cls.GRIPPER_CLOSED_HALFWIDTH = grip.halfwidth_of(cls.GRIPPER_CLOSED)
    # 하드 바닥 TCP = 통 바닥 상면 + 손끝 오프셋 + 여유.
    # 손끝 오프셋이 그리퍼마다 다르므로 이 바닥 한계도 모델마다 달라진다.
    cls.GRASP_FLOOR_Z = (cls.BIN_FLOOR_TOP + cls.TCP_TO_FINGERTIP
                         + cls.GRASP_FLOOR_CLEAR)
    return profile


def _load_active_profile():
    """활성 모델 프로파일을 읽어 꽂는다. 실패하면 '왜'를 말하고 죽는다.

    임포트 시점에 하는 이유: `desktop_bridge.py` 처럼 `PickPlaceConfig.X` 를 모듈
    최상단에서 읽는 소비자가 있어서다. 그 시점에 값이 없으면 AttributeError 가
    엉뚱한 곳에서 터져 원인을 못 찾는다.
    """
    try:
        return apply_profile(robot_profiles.active_profile())
    except (robot_profiles.ProfileError,
            robot_profiles.ProfileNotFound) as exc:
        raise RuntimeError(
            f'로봇 모델 프로파일을 불러오지 못했습니다: {exc}\n'
            f'  활성 모델   : {robot_profiles.active_model_name()!r}\n'
            f'  탐색 경로   : {robot_profiles.search_dirs()}\n'
            f'  등록된 모델 : {robot_profiles.names() or "(없음)"}\n'
            f'`binpick_model list` 로 확인하세요.') from exc


ACTIVE_PROFILE = _load_active_profile()
