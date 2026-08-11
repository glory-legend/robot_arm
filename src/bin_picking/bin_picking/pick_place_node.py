# -*- coding: utf-8 -*-
"""
통합 예제: 충돌 회피 + Cartesian 접근 Pick & Place
=================================================================
ex05 + ex07 + ex09 + ex10 예제의 핵심을 하나의 파이프라인으로 합친 통합 데모.

각 예제에서 가져온 부품:
- ex07: plan_only → FK 미리보기 → execute 3단 워크플로 (plan_viz_execute),
        Approach/Lift/Retreat 시퀀스, 그리퍼 제어(FollowJointTrajectory),
        SRDF에서 ready 자세 파싱, FK 다운샘플링(max_points)
- ex05: 물체 근처의 하강/상승/후퇴 구간을 Cartesian 직선 보간으로 교체,
        fraction(달성률) 게이트로 실행 전 검증
- ex09: PlanningScene에 충돌 객체 등록(볼트 통 + 볼트들),
        운반 경로의 장애물 회피, latched QoS 마커, /next_step 단계 트리거
- ex10: 어려운 구간에서 여러 OMPL 플래너를 순차 시도하는 폴백

대상: 집는 통(bolt_bin) 안에 '무더기(pile)'로 쌓인 M8 볼트를 하나씩 집어,
같은 모양의 놓는 통(drop_bin) 안 빈 자리에 툭 떨어뜨린다.

무더기 bin-picking 구조 (로봇은 무더기를 해석하지 않는다):
  외부 비전/판단 시스템이 '가장 위에 있고 가려지지 않은 최적 볼트'의 6D 자세를
  /next_bolt_pose (PoseStamped) 로 던져주면, 로봇은 그 자세에 맞춰 그리퍼 각도를
  돌려 집는다. 외부 입력이 없으면(단독 실행) 센싱된 볼트 중 가장 위에 있는 것을
  자체 선택한다 → get_next_optimal_bolt_pose() 가 그 연동 지점.

실시간 루프:
  Step A  Ready 자세 복귀 (그리퍼 열고 씬을 실제 볼트 위치로 갱신)
  Step B  최적 볼트 6D 자세 수신 (외부 우선 / 없으면 자체 선택)
  Step C  볼트 축에 맞춰 그리퍼 각도를 돌려 파지 → 부착 → 리프트
  Step D  놓는 통에서 '빈 자리'를 찾아 그 위에서 툭 놓기 → 다시 Step A

그리퍼 각도: 볼트 축 a 와 접근방향 z_tool 에 대해 y_tool=z_tool×a(손가락 닫힘),
  x_tool=y_tool×z_tool 로 회전행렬을 세운다(_grasp_frame/grasp_quat_for_axis).
  손가락이 항상 볼트 축과 수직이 되고, 수직 접근 + 눕힌 볼트에선
  euler(π,0,yaw)와 동일하다.

비수직(6D) 접근: 접근방향은 (0,0,-1) 고정이 아니라 '볼트 축 a 를 회전축으로'
  0° → ±15° → ±30° 로 기울여 가며, 개구가 확보되는 첫 방향을 채택한다
  (_approach_candidates/_plan_grasp_approach). 통 벽은 20mm 밖에 안 되므로
  벽 반대쪽으로 기울이면 벽쪽 손가락이 벽 위로 넘어가 자리가 생긴다.
  ⚠ '접근방향을 볼트 축과 정렬'하는 게 아니다 — 그건 원기둥 끝면을 들이받는
    꼴이라 절대 못 집는다. 손가락은 계속 볼트 축과 수직을 유지한다.
  a 둘레 회전은 a·z_tool 을 보존하므로 '볼트축 = hand X'(attach_bolt 의 전제)가
  기울여도 깨지지 않는다.

파지 하강의 완주 검증: 하강은 '끝점 도달'이 목적이라 이동용 fraction 게이트
  (MIN_FRACTION=0.9)로 재면 안 된다. 90%는 볼트보다 수십 mm 위에서 멈춘다는
  뜻이고, 거기서 손가락을 닫으면 반드시 빈손이다. 하강 전용 게이트
  (GRASP_MIN_FRACTION=0.995) + 실행 후 FK 실측 z 재확인
  (verify_descent_reached)을 모두 통과해야만 그리퍼를 닫는다.

볼트 재시도 정책: _picked(옮김) / _blacklist(영구 포기) / _deferred(이번 무더기
  상태에서만 보류) 세 집합으로 관리하고, '마지막 파지 성공 이후'의 실패만
  세는 진전(epoch) 기반 카운터로 블랙리스트를 결정한다 → 이웃이 빠져 풀린
  볼트는 버려지지 않고, 아무 진전이 없으면 루프가 유한 시간에 끝난다.

놓을 자리: 놓는 통 안 격자 슬롯마다 '센싱된 볼트까지 최소 거리'를 재서
  SLOT_CLEAR_R 이상이면 빈 자리로 판정(_free_drop_slot). 전부 차 있으면 가장
  여유로운 자리를 쓴다. 바닥까지 안 내려가고 통 벽 위(DROP_Z)에서 놓는다.

실행 방법 (colcon build 후 각 터미널에서 install/setup.bash source):
  ※ 전제: franka_description 의 finger_joint2 mimic 등록 패치가 적용된 상태여야
     한다(없으면 한쪽 손가락만 닫혀 편측 파지). 최초 1회 colcon build 필요.

  터미널1: ros2 launch bin_picking franka_gazebo_moveit.launch.py   # 로봇+카메라
  터미널2: ros2 launch bin_picking spawn_bolts.launch.py            # 통+볼트 스폰
  터미널3: ros2 launch bin_picking vision_pipeline.launch.py        # (선택) 카메라 브릿지
  터미널4: ros2 run bin_picking bolt_vision                         # (선택) 비전 인식
  터미널5: ros2 run bin_picking integrated_pick_place --auto        # 데모 (연속 자동)
           (--auto 없이 실행하면 STEP_BY_STEP=True → 사이클마다 /next_step 대기:
            ros2 topic pub --once /next_step std_msgs/msg/Empty '{}')

RViz 설정:
  - MarkerArray Display 추가 → Topic: /pick_place_markers
  - Planning Scene Display 추가 (충돌 객체 확인용)
  - Fixed Frame: fr3_link0

경로 색상 규칙:
  - 주황 LINE_STRIP: 일반 계획(RRT류) 경로 — 곡선일 수 있음
  - 시안 LINE_STRIP: Cartesian 직선 경로 — fraction 게이트 통과분
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
from std_msgs.msg import ColorRGBA, Empty, String
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




from bin_picking.config import PickPlaceConfig
from bin_picking.gripper_adapters import make_gripper_adapter
from bin_picking.geometry import GeometryMixin
from bin_picking.grasp_planning import GraspPlanningMixin
from bin_picking.robot_state import RobotStateMixin
from bin_picking.moveit_io import MoveItIOMixin
from bin_picking.gripper import GripperMixin
from bin_picking.scene import SceneMixin
from bin_picking.markers import MarkersMixin
from bin_picking.sensing import SensingMixin
from bin_picking.selection import SelectionMixin


class IntegratedPickPlace(Node, PickPlaceConfig, GeometryMixin, GraspPlanningMixin, RobotStateMixin, MoveItIOMixin, GripperMixin, SceneMixin, MarkersMixin, SensingMixin, SelectionMixin):

    def __init__(self, auto=False):
        super().__init__(
            'franka_integrated_pick_place',
            parameter_overrides=[Parameter('use_sim_time', value=True)],
        )
        self.get_logger().info('=== 통합 Pick & Place 데모 ===')
        # [R5] --auto(또는 생성자 auto=True) 면 STEP_BY_STEP 을 인스턴스 레벨에서
        # False 로 덮어써(클래스 기본 True 를 가림) 트리거 없이 연속 자동 운전한다.
        self._auto = bool(auto)
        if self._auto:
            self.STEP_BY_STEP = False
            self.get_logger().info('[R5] 자동 모드 — 트리거 없이 전 사이클 연속 실행')
        # [고속 학습 모드] 자동(학습) 운전에서는 이동 속도를 올리고 불필요한
        # 대기를 줄여 판당 소요 시간을 단축한다. 단, 파지 품질(학습 라벨의
        # 신뢰성)에 직결되는 것들 — 손가락 정착 대기(GRASP_SETTLE_SEC), 달성률/
        # FK/실측 하드 게이트 — 는 그대로 둔다. 라벨이 깨지면 빨리 모아도 무의미.
        # [속도 최적화] 자유공간 이동은 공격적으로(0.7→0.9), 정밀 하강/리프트는
        # 보수적으로(0.5→0.7) 올린다. 하강은 FK 실측 검증(±3mm)이 지키므로 조금
        # 빨라져도 파지창을 놓치지 않는다(성공률 100% 유지 확인 대상).
        self._vel = 0.9 if self._auto else 0.3        # 이동(Ready/접근/운반) 속도
        # 0.7 → 0.6: 0.7 에서 하강이 간헐적으로 목표보다 6mm 위에서 멈춰(컨트롤러
        # 추종 한계) '하강 미달' 재시도 낭비가 났다(로그 143629 실측 0.0211).
        # 0.6 은 하강 2초→~2.3초로 미미하게 늘 뿐 그 낭비를 없앤다. 자유공간(0.9)
        # 은 정밀도와 무관해 그대로 둔다.
        self._vel_fine = 0.6 if self._auto else 0.3   # 하강/리프트(정밀 구간) 속도
        # 외부 비전이 없는 학습 판에서 매 사이클 3초 대기는 순수 낭비 → 0.5초
        self._ext_pose_wait = 0.5 if self._auto else self.EXT_POSE_WAIT
        self._grip_dur = 0.5 if self._auto else 1.0   # 그리퍼 개폐 명령 시간

        # --- 액션 / 서비스 클라이언트 ---
        self._move_client = ActionClient(self, MoveGroup, 'move_action')
        self._execute_client = ActionClient(
            self, ExecuteTrajectory, 'execute_trajectory')
        # 그리퍼는 액션 타입이 업체마다 다르다(FollowJointTrajectory / GripperCommand)
        # → 프로파일이 고른 어댑터가 액션 클라이언트를 소유한다.
        self._gripper_adapter = make_gripper_adapter(
            self, self.ROBOT_PROFILE.gripper)
        self._gripper_client = self._gripper_adapter.client
        self._fk_client = self.create_client(GetPositionFK, 'compute_fk')
        self._ik_client = self.create_client(GetPositionIK, 'compute_ik')
        self._cart_client = self.create_client(
            GetCartesianPath, 'compute_cartesian_path')
        self._scene_client = self.create_client(
            ApplyPlanningScene, 'apply_planning_scene')

        # --- 마커: latched QoS + 주기 재발행 (ex09) ---
        latched_qos = QoSProfile(depth=10)
        latched_qos.durability = DurabilityPolicy.TRANSIENT_LOCAL
        self._marker_pub = self.create_publisher(
            MarkerArray, self.MARKER_TOPIC, latched_qos)
        self._markers = MarkerArray()
        self._marker_id = 0
        self._marker_timer = self.create_timer(2.0, self._republish_markers)

        # --- /joint_states 구독 (Cartesian start_state + 파지 성공 판정 용) ---
        self._joint_state = None
        self._finger_pos = None   # fr3_finger_joint1 실측 위치 (파지 판정)
        self._finger_seq = 0      # 손가락 값이 갱신된 횟수(신선한 샘플 대기용)
        self.create_subscription(
            JointState, 'joint_states', self._joint_state_cb, 10)

        # --- 단계 트리거 (ex09) ---
        self._trigger_received = False
        self.create_subscription(Empty, '/next_step', self._trigger_cb, 10)

        # --- Gazebo 볼트 실제 위치 구독 (spawn_bolts.launch 의 pose 브리지) ---
        #  /model/bolt_i/pose → TFMessage. 볼트마다 토픽이 따로 있다.
        #  없으면(브리지 미설정) 자동으로 BOLT_LAYOUT 폴백.
        self._bolt_sensed = {}   # 'bolt_i' -> ((x,y,z), (qx,qy,qz,qw)) [월드]
        self._sensing_logged = False
        self._frame_diag = []        # 실제로 수신한 'parent -> child' 이름 표본
        self._frame_diag_n = 0
        self._frame_diag_done = False
        # ---------- 볼트 선택 상태 (Issue C — 각 집합의 의미를 명확히) ----------
        # _picked     : 집어서 놓는 통으로 옮긴 볼트. 다시 선택하지 않는다.
        #               (놓기에 실패해 손에서 놓쳤으면 discard 로 되돌린다)
        # _blacklist  : '영구 포기'. 진전 없는 재시도 상한(MAX_NO_PROGRESS) 도달,
        #               또는 놓기 반복 실패. 실물은 통에 남아 있으므로 씬에는
        #               계속 등록하되(충돌 회피 대상), 다시는 선택하지 않는다.
        #               → 이 집합이 커지면서 루프가 반드시 종료된다.
        # _deferred   : '이번 무더기 상태에서는' 불가(이웃/벽이 개구를 막음).
        #               영구 포기가 아니다. 파지에 성공하면(무더기가 실제로
        #               바뀌면) 통째로 비워 재검토한다.
        # _attempts   : 볼트별 (진전 epoch, 그 epoch 안에서의 실패 횟수).
        #               epoch 가 바뀌면(=그 사이 어떤 볼트든 파지 성공) 리셋된다
        #               → '이웃이 빠져 풀린 볼트'는 절대 블랙리스트로 안 간다.
        # _drop_fail  : 볼트별 '놓기' 실패 횟수. 파지는 성공하는데 놓기만 계속
        #               실패하는 라이브락(파지 성공이 epoch 를 계속 올려 _attempts
        #               가 영원히 리셋됨)을 이 카운터가 따로 막는다.
        self._picked = set()
        self._blacklist = set()
        self._deferred = set()
        self._attempts = {}
        self._drop_fail = {}
        # 볼트별 '이미 실패한 접근 자세(기울기)' 기억: key → (epoch, pos, {deg}).
        # 같은 위치·같은 epoch 에서의 재시도는 반드시 다른 자세를 쓰게 강제하고,
        # 새 자세가 안 남았으면 즉시 포기한다(동일 자세 무의미 반복 방지).
        self._tried_grasp = {}
        # 진전(=파지 성공) 카운터. 오를 때마다 무더기가 실제로 바뀐 것으로 본다.
        self._pick_epoch = 0
        # 직전 실패에서 아무것도 안 쥔 채 접근 높이에 남아 있으면 True —
        # 다음 사이클의 Ready 복귀/그리퍼 개방을 생략하고 제자리에서 재선택
        # (실패당 왕복 2회 + 그리퍼 개폐 낭비 제거).
        self._skip_ready = False
        self._grasp_closed = False   # 그리퍼가 물리적으로 닫혀 있는지(씬 부착과 별개)
        self._attached_src_id = None   # 부착 중인 볼트의 '원래' bolt_i id

        # --- 외부 비전 입력: 최적 볼트 6D 자세 (없으면 자체 선택 폴백) ---
        self._ext_pose = None
        self._ext_pose_fresh = False
        self.create_subscription(
            PoseStamped, self.EXT_POSE_TOPIC, self._ext_pose_cb, 10)
        # QoS: ros_gz_bridge 의 parameter_bridge 는 QoS 를 따로 지정하지 않으면
        # rclcpp 기본값(RELIABLE / VOLATILE / KEEP_LAST)으로 발행한다.
        # 구독자가 BEST_EFFORT 를 '요청'하면 RELIABLE 발행자와도, BEST_EFFORT
        # 발행자와도 붙는다(요청 신뢰도 ≤ 제공 신뢰도이면 호환). 즉 BEST_EFFORT 는
        # 양쪽 모두를 커버하는 가장 안전한 선택이라 그대로 둔다.
        # ※ 반대로 RELIABLE 로 바꾸면 브리지가 SENSOR_DATA 프로파일로 설정된
        #   경우 아예 연결되지 않는다 — 그래서 '더 엄격하게' 가면 안 된다.
        # depth 만 1 → 10 으로 키운다. 55Hz 로 들어오는데 노드는 계획/실행 중
        # 오래 스핀하지 않으므로, 큐가 1이면 스핀 재개 시점에 하필 유실된
        # 프레임 하나만 남을 수 있다(누락 자체가 치명적이진 않지만 무료 보험).
        pose_qos = QoSProfile(depth=10)
        pose_qos.reliability = ReliabilityPolicy.BEST_EFFORT
        # 볼트마다 구독을 따로 연다. 콜백에 그 볼트의 id 를 묶어 두므로(기본 인자
        # 바인딩), 프레임 이름 파싱이 실패해도 어느 볼트인지는 토픽으로 확정된다.
        for i in range(len(BOLT_LAYOUT)):
            bid = f'bolt_{i}'
            self.create_subscription(
                TFMessage, self.POSE_TOPIC_FMT.format(bid),
                lambda msg, _bid=bid: self._bolt_pose_cb(msg, _bid), pose_qos)

        # 충돌 객체를 실제로 등록했는지 — 종료 시 불필요한 정리(및 대기) 방지
        self._objects_added = False
        # 볼트를 EE에 부착한 상태인지 + 어떤 볼트인지 — 중단 시 detach 누락 방지
        self._bolt_attached = False
        self._attached_id = None

        # ---------- 학습형 파지 선택기 초기화 (R1/R4) ----------
        # 경로 확정(런타임 홈 기준). 학습 데이터/모델은 로그와 같은 폴더에 둔다.
        self.ATTEMPTS_PATH = os.path.expanduser(self.ATTEMPTS_REL)
        self.MODEL_PATH = os.path.expanduser(self.MODEL_REL)
        self._attempt_count = 0            # 온라인 update 누적 횟수(주기 재적합 트리거)
        # 학습 선택으로 정해진 계획을 _pick 에 넘길 임시 슬롯(재계산 방지).
        self._pending_plan = None
        # [데스크톱 통신] 이번 사이클 대상의 출처. get_next_optimal_bolt_pose()
        # 가 매 _pick() 호출 직전 항상 갱신하므로 여기 초기값은 첫 사이클 전
        # 미바인딩을 막는 용도일 뿐(안전한 기본값 'ROBOT').
        self._pick_origin = 'ROBOT'
        # [데스크톱 통신] cycle_id 발급 카운터 — _log_attempt 가 매 호출마다
        # 1씩 올려 시스템 전체에서 유일하게 이 값을 발급한다(명시 초기화 —
        # 발행 훅이 예외를 통째로 삼키므로 hasattr 지연초기화면 미바인딩 시
        # 진단 없이 조용히 죽는다).
        self._cycle_seq = 0
        # [데스크톱 통신] cycle_result 퍼블리셔도 같은 이유로 여기서 미리 만든다 —
        # 첫 _pick() 종결 직전에야 지연 생성하면, 새 퍼블리셔가 desktop_bridge 의
        # 구독과 디스커버리를 마치기 전에 바로 publish() 가 일어나 RELIABLE/
        # VOLATILE QoS 하에서 첫 사이클의 결과가 그냥 유실된다(구독자가 아직
        # 안 보이는 상태로 publish 하면 조용히 버려짐). __init__ 시점에 만들어
        # 두면 첫 PICK_BOLT 가 실제로 처리될 때까지 디스커버리가 끝날 여유가 생긴다.
        self._cycle_result_pub = self.create_publisher(String, self.CYCLE_RESULT_TOPIC, 10)
        self.selector = None
        if self.USE_LEARNED_SELECTOR and GraspSelector is not None:
            self.selector = GraspSelector()
            if not self.selector.available:
                self.get_logger().warn(
                    f'[학습선택기] sklearn 비활성({self.selector.sklearn_error}) '
                    f'— 휴리스틱으로 동작합니다')
            else:
                # 저장 모델을 먼저 시도하고, 이어서 누적 로그로 warm start 한다.
                loaded = self.selector.load(self.MODEL_PATH)
                n, ready = self.selector.warm_start(
                    self.ATTEMPTS_PATH, epochs=self.WARM_START_EPOCHS)
                self.get_logger().info(
                    f'[학습선택기] 준비: 모델로드 {"성공" if loaded else "없음"}, '
                    f'표본 {n}개, ready={ready} '
                    f'(경로 {self.ATTEMPTS_PATH})')
        elif self.USE_LEARNED_SELECTOR and GraspSelector is None:
            self.get_logger().warn(
                f'[학습선택기] grasp_selector 임포트 실패({_SELECTOR_IMPORT_ERR}) '
                f'— 휴리스틱으로 동작합니다')

    # =========================================================
    # 외부 비전 인터페이스 + 놓을 자리 찾기
    # =========================================================
    def get_next_optimal_bolt_pose(self, timeout_sec=None):
        """[외부 비전 연동 지점] 다음에 집을 '가장 집기 좋은' 볼트의 6D 자세.

        1) 외부 시스템이 EXT_POSE_TOPIC(PoseStamped)으로 보낸 자세가 있으면 소비.
           → 무더기 해석은 외부가 담당하고, 로봇은 '위에 있는 최적 볼트' 하나만 받는다.
        2) 없으면(단독 실행) 센싱된 볼트 중 가장 위 + 덜 붐비는 것을 자체 선택.
        반환: (bolt_id 또는 None, (x,y,z), (qx,qy,qz,qw)) / 더 없으면 None
        """
        wait = self._ext_pose_wait if timeout_sec is None else timeout_sec
        end = time.time() + wait
        # 외부 pose 로 잡히면 학습 계획은 없다 — 이전 사이클 잔재를 비운다.
        self._pending_plan = None
        while time.time() < end and rclpy.ok():
            if self._ext_pose_fresh:
                self._ext_pose_fresh = False
                fid = (self._ext_pose.header.frame_id or '').lstrip('/')
                if fid and fid != self.REFERENCE_FRAME:
                    # TF 변환 미구현 — 다른 프레임이면 조용히 엉뚱한 곳으로 가므로 거부
                    self.get_logger().error(
                        f'외부 pose 프레임 "{fid}" ≠ {self.REFERENCE_FRAME} — 무시. '
                        f'{self.REFERENCE_FRAME} 기준으로 발행하세요.')
                    continue
                pp = self._ext_pose.pose
                pos = (pp.position.x, pp.position.y, pp.position.z)
                quat = (pp.orientation.x, pp.orientation.y,
                        pp.orientation.z, pp.orientation.w)
                # 외부 자세와 가장 가까운 센싱 볼트를 찾아 id 를 붙인다.
                # id 가 있어야 하강 전 그 볼트를 씬에서 뺄 수 있다(자기 충돌 방지).
                bid = self._match_sensed_bolt(pos)
                self.get_logger().info(
                    f'외부 비전 6D 자세 수신 → 파지 (매칭 {bid or "없음"})')
                # [데스크톱 통신] 이 사이클의 대상이 desktop_bridge 의 PICK_BOLT
                # 재발행(EXT_POSE_TOPIC)에서 왔음을 기록 — _log_attempt 가 결과를
                # RESULT(데스크톱 상관관계 있음) 대 grasp_result(없음) 로 가를 때 쓴다.
                self._pick_origin = 'DESKTOP'
                return (bid, pos, quat)
            rclpy.spin_once(self, timeout_sec=0.05)
        # 외부 자세가 안 오면 자체 선택으로 폴백. 학습 선택기가 준비됐으면 랭킹,
        # 아니면 기존 휴리스틱(_select_topmost_bolt). (R3)
        self._pick_origin = 'ROBOT'
        return self._select_fallback()

    def _spin_sleep(self, duration):
        """콜백을 처리하면서 대기"""
        end_time = time.time() + duration
        while time.time() < end_time:
            rclpy.spin_once(self, timeout_sec=0.05)

    # =========================================================
    # Pick & Place 한 볼트 (반복 단위)
    # =========================================================
    def _pick(self, target, plan=None):
        """Step C — 받은 6D 자세에 맞춰 그리퍼 각도를 돌려 볼트를 집는다.

        [R3] plan(=_select_learned 이 만든 dict)이 주어지면 (tilt/approach/
        aperture/wall_cap/feat)를 그대로 써서 접근각 재탐색을 생략한다. plan 이
        None 이면 기존과 동일하게 _plan_grasp_approach 로 내부 탐색한다.
        하드 게이트(달성률·FK·손가락 실측·리프트 재검증)와 재시도 상태기계는
        어느 경로에서도 그대로다.

        [R4] 모든 종결 지점에서 _log_attempt 로 시도 데이터를 남기고 온라인
        학습을 돌린다(성공 라벨 = 리프트 후 재검증까지 통과).
        """
        t0 = time.time()                    # 시도 소요시간(out.dur) 측정 기준
        feat = None                         # 후보가 정해지면 채워지는 학습 특징
        bolt_id, pos, quat = target
        label = bolt_id if bolt_id else 'ext'
        # 하강 직전 재취득(3b)의 '기준점'. 넘겨받은 pos 와 직접 비교하면, 외부
        # 비전 pose 가 센싱값과 원래 조금 다를 때 매번 취소되어 버린다.
        # → 같은 출처(센싱)끼리 비교해 '접근하는 동안 실제로 움직인 양'만 잰다.
        sensed_at_lock = self._bolt_sensed.get(bolt_id) if bolt_id else None
        axis = self.bolt_axis_from_quat(quat)
        # 실패 집계 키 — 볼트 id 가 없는 외부 pose 경로도 상한을 갖도록 합성한다
        fail_key = bolt_id or f'ext_{round(pos[0], 3)}_{round(pos[1], 3)}'
        # [데스크톱 통신] retries 필드 값 — "이번 시도 이전의" 연속 실패수를
        # _pick() 시작 시점에 딱 한 번만 읽어 이번 호출 내 모든 _log_attempt
        # 지점에 동일한 기준으로 쓴다(호출마다 다른 시점에 self._attempts 를
        # 읽으면 _note_attempt_failed 의 증가/성공 시 pop 순서에 따라 성공·
        # 실패 레코드의 의미가 서로 달라져 버린다). _note_attempt_failed 와
        # 동일하게 epoch 불일치 시 0으로 리셋한다(그 사이 다른 볼트가 성공해
        # 무더기가 바뀌었다는 뜻 — _note_progress 는 _attempts 를 안 비우므로
        # 이 리셋이 없으면 무효화된 낡은 스트릭이 유령처럼 남는다).
        _epoch_at_start, _retries_before = self._attempts.get(
            fail_key, (self._pick_epoch, 0))
        if _epoch_at_start != self._pick_epoch:
            _retries_before = 0
        if self.grasp_quat_for_axis(axis) is None:
            self.get_logger().warn(
                f'[{label}] 볼트가 거의 수직으로 서 있어 옆에서 감쌀 수 없음 — 건너뜀')
            # ⚠ 예전엔 _picked 에 넣었다 — '옮겼다'는 뜻이라 통계·씬 판단을
            #   오염시킨다. 실제로는 영구 포기이므로 블랙리스트가 맞다.
            #   (축이 접근방향과 이루는 각은 기울기 후보로도 바뀌지 않는다 —
            #    _grasp_frame 주석의 불변식 참고 → 기울여봐도 소용없다)
            self._blacklist.add(fail_key)
            # [데스크톱 통신] 이 분기는 _note_attempt_failed 를 거치지 않으므로
            # (영구 포기라 스트릭 집계 자체가 무의미) retries 는 미조정 값 그대로.
            self._log_attempt(fail_key, None, 0, 'axis_unreachable',
                              dur=round(time.time() - t0, 2),
                              retries=_retries_before)
            return False

        tx, ty = pos[0], pos[1]
        grasp_z = self._grasp_z_for(pos[2])
        yaw_deg = math.degrees(math.atan2(float(axis[1]), float(axis[0])))
        self.get_logger().info(
            f'[{label}] 파지 ({tx:.3f}, {ty:.3f}, z={grasp_z:.3f}) '
            f'[볼트중심 z={pos[2]:.3f}, 바닥안착기준 {self.BOLT_REST_CENTER_Z:.3f}, '
            f'바닥 한계 {self.GRASP_FLOOR_Z:.3f}] '
            f'볼트축 {yaw_deg:+.0f}° → 그리퍼 각도 자동 정렬')

        # --- 동적 개구 최적화 + 접근방향(기울기) 탐색 ---
        # 만개(40mm)로 수직으로만 내려가면 벽 근처/이웃이 가까운 볼트에서 손가락이
        # 먼저 닿는다. 개구를 좁히고, 그래도 안 되면 접근방향을 볼트 축 둘레로
        # 기울여 벽 위로 손가락을 넘긴다(Issue D).
        # 같은 상황에서 이미 실패한 기울기는 후보에서 뺀다 — 재시도는 반드시
        # '다른 자세'로만 한다. 뺄 게 없으면 예전과 동일.
        sel_pos = tuple(pos)               # 실패 기록의 기준 위치(재취득 전)
        if plan is not None:
            # [R3] 학습 선택 단계에서 이미 (기울기·접근·개구)를 정했다 —
            # 재탐색 없이 그대로 사용(특징도 그때 계산된 것을 재사용).
            tilt_deg = plan['tilt_deg']
            approach = plan['approach']
            aperture = plan['aperture']
            wall_cap = plan['wall_cap']
            feat = plan.get('feat')
            # 롤아웃이 '하강이 닿은' 접근 팔자세를 실었으면 그걸로 접근한다 —
            # 시뮬과 같은 IK 분기여야 하강이 실제로 성립한다.
            plan_app_joints = plan.get('approach_joints')
            self.get_logger().info(
                f'[{label}] 학습 선택 계획 사용 — 접근각 재탐색 생략 '
                f'(기울기 {tilt_deg:+.0f}°, 개구 {aperture * 1000:.1f}mm'
                f'{", 롤아웃 접근자세 고정" if plan_app_joints else ""})')
        else:
            # --- 동적 개구 최적화 + 접근방향(기울기) 탐색 ---
            # 같은 상황에서 이미 실패한 기울기는 후보에서 뺀다 — 재시도는 반드시
            # '다른 자세'로만 한다. 뺄 게 없으면 예전과 동일.
            tried = self._tried_approaches(fail_key, sel_pos)
            if tried:
                self.get_logger().info(
                    f'[{label}] 이미 실패한 접근 자세 {sorted(tried)}° 제외 — '
                    f'다른 자세로만 재시도')
            sel = self._plan_grasp_approach(
                pos, axis, bolt_id, exclude_degs=tried)
            if sel is None and tried:
                # 새로 시도할 자세가 없다 — 같은 자세를 반복해 봐야 결과도 같으므로
                # 3회를 채우지 않고 즉시 포기하고 다음 볼트로 넘어간다.
                self._blacklist.add(fail_key)
                self.get_logger().warn(
                    f'[{label}] 남은 새 접근 자세 없음(실패한 자세 {sorted(tried)}°) '
                    f'— 동일 자세 반복 대신 즉시 포기, 다음 볼트로')
                # [데스크톱 통신] 여기도 _note_attempt_failed 를 안 거치는
                # 블랙리스트 분기 — retries 미조정.
                self._log_attempt(fail_key, None, 0, 'no_aperture_exhausted',
                                  dur=round(time.time() - t0, 2),
                                  retries=_retries_before)
                return False
            if sel is None:
                self.get_logger().warn(
                    f'[{label}] 수직·기울임({self.TILT_CANDIDATES_DEG}°) 어느 접근으로도 '
                    f'그리퍼가 들어갈 공간이 없음 — 보류 (이웃이 빠지면 재시도)')
                # ⚠ 영구 포기가 아니라 '이번 무더기 상태에서는 보류'다. 막고 있는 건
                #   '이웃'이므로, 다른 볼트를 하나라도 집어내면 다시 가능해진다.
                #   단, 진전이 없는 채로 반복되면 _note_attempt_failed 가 결국
                #   블랙리스트로 보내 루프를 끝낸다.
                self._deferred.add(fail_key)
                self._note_attempt_failed(fail_key, '개구 확보 실패')
                # [데스크톱 통신] 위에서 _note_attempt_failed 가 이미 스트릭을
                # 증가시켰으므로 +1 — 문서가 정의하는 "이번 실패까지 포함한
                # 연속 실패수"와 로봇의 MAX_NO_PROGRESS 블랙리스트 트리거가
                # 보는 카운트를 일치시킨다.
                self._log_attempt(fail_key, None, 0, 'no_aperture',
                                  dur=round(time.time() - t0, 2),
                                  retries=_retries_before + 1)
                return False
            tilt_deg, approach, aperture, wall_cap = sel
            plan_app_joints = None       # 롤아웃 경로가 아니면 접근자세 고정 없음
            # 학습 로깅/랭킹과 동일한 특징을 이 시점(선택 시)에 계산해 둔다.
            feat = self._grasp_features(
                pos, axis, tilt_deg, aperture, wall_cap, approach)
        # 개구는 _grasp_aperture 가 이미 '목표 개구(GRASP_PREGRASP_OPEN)와 벽/이웃
        # 제약'을 함께 반영해 타이트하게 돌려준다(하한 GRASP_MIN_OPEN). 여기서
        # 추가로 깎지 않는다 — 예전 임시 클램프(0.01=10mm)는 하한 12mm 보다도 좁아
        # 볼트를 채 감싸지 못했고, 벽/이웃 검증 결과까지 통째로 버렸다.

        ori = self.grasp_quat_for_axis(axis, approach)
        if ori is None:                     # 방어: 위 검사를 통과했으면 안 나온다
            self._note_attempt_failed(fail_key, '파지 자세 생성 실패')
            self._log_attempt(fail_key, feat, 0, 'orientation_fail',
                              dur=round(time.time() - t0, 2),
                              retries=_retries_before + 1)
            return False
        self.get_logger().info(
            f'[{label}] 개구 {self.GRIPPER_OPEN_HALFWIDTH * 1000:.1f}mm → '
            f'{aperture * 1000:.1f}mm (벽 제약 {wall_cap * 1000:.0f}mm) / '
            f'접근 기울기 {tilt_deg:+.0f}° '
            f'{"(수직)" if abs(tilt_deg) < 1e-9 else "(볼트축 둘레로 기울임 — 벽 회피)"}')
        # 접근/하강 '전에' 미리 좁혀 둔다(pre-grasp aperture).
        self.move_gripper(aperture)

        def fail(msg, reason='abort', metrics=None):
            self.get_logger().error(f'[{label}] {msg}')
            # 이 (위치, 접근 자세) 조합은 실패 — 재시도 시 같은 자세를 다시 쓰지
            # 않도록 기억한다(볼트가 움직이거나 무더기가 바뀌면 자동 리셋).
            self._record_tried(fail_key, sel_pos, tilt_deg)
            # 씬 부착(_bolt_attached)이 아니라 '물리적으로 닫혀 있는지'로 판단해야
            # 부착 실패 상태에서도 반드시 손을 편다.
            held = self._grasp_closed or self._bolt_attached
            if held:
                self.gripper_open()
                self._grasp_closed = False
                if self._attached_id:
                    dropped = self._attached_id
                    self.detach_bolt(dropped)
                    self.remove_collision_objects([dropped])
                # 뭔가를 쥐었다 놓은 경우에만 Home 으로 빠진다(놓은 볼트 위에서
                # 얼쩡거리면 유령 충돌/재센싱 간섭). 아무것도 안 쥔 실패는 팔이
                # 접근 높이(0.25)에 그대로 있으므로 Home 왕복이 순수 낭비다 —
                # 제자리에서 다음 후보로 바로 간다(다음 접근도 IK 관절목표라
                # 시작 자세가 ready 가 아니어도 무방). Step A 의 Ready 복귀도
                # _skip_ready 로 같이 건너뛴다 → 실패당 이동 2회 절약.
                self.plan_viz_execute_joint(
                    self._ready_target, vel=self._vel, label='Home')
            else:
                # [J7 오염 방지 — 서브에이전트 확인] 기울임 실패 등으로 팔이 관절
                # 한계 근처(예: J7 +3.017)에 남으면, 그 상태에서 다음 사이클 계획을
                # 시작해 연쇄 실패한다. 한계 근처면 Ready 로 리셋해 오염을 끊고,
                # 아니면 제자리 재선택(왕복 절약)을 유지한다.
                cur = self._arm_joint_positions()
                if cur is not None and self._joint_margin(cur) < self.LIMIT_MARGIN:
                    self.get_logger().warn(
                        f'[{label}] 실패 후 관절 한계 근접(여유 '
                        f'{self._joint_margin(cur):.3f}rad) — Ready 로 리셋(오염 차단)')
                    self.plan_viz_execute_joint(
                        self._ready_target, vel=self._vel, label='Home')
                else:
                    self._skip_ready = True
            # 못 든 채 실패면 볼트는 통에 그대로 → 다음 사이클 refresh 가 복원한다
            # 볼트 id 유무와 무관하게 같은 상태기계로 집계한다(Issue C).
            self._note_attempt_failed(fail_key, msg)
            self._attached_src_id = None
            # [R4] 실패 라벨(0)로 학습 데이터 기록 + 온라인 갱신.
            # [데스크톱 통신] 위에서 _note_attempt_failed 가 이미 증가시켰으므로 +1.
            self._log_attempt(fail_key, feat, 0, reason,
                              dur=round(time.time() - t0, 2),
                              metrics=metrics, retries=_retries_before + 1)
            return False

        def abort(msg):
            """'이번 시도 취소' — 아직 아무것도 물지 않은 상태에서만 부르므로
            detach 는 필요 없다. 다음 사이클에 자세를 다시 잡고 재계획한다.

            ⚠ 예전엔 여기서 아무 집계도 하지 않았다 → 볼트가 계속 조금씩 흔들리면
              '취소 → 재선택 → 취소'가 영원히 반복되는 라이브락이 났다.
              취소도 '진전 없는 사이클'이므로 반드시 집계한다.
            """
            self.get_logger().warn(f'[{label}] {msg} — 시도 취소, 다음 사이클 재계획')
            self.gripper_open()
            # 아무것도 안 쥔 취소 — 접근 높이 제자리에서 다음 후보로 바로 간다
            # (Home 왕복 생략, Step A Ready 복귀도 _skip_ready 로 생략)
            self._skip_ready = True
            self._note_attempt_failed(fail_key, '시도 취소')
            # [R4] 취소도 '실패한 시도'로 기록(라벨 0, reason=abort).
            # [데스크톱 통신] 위에서 _note_attempt_failed 가 이미 증가시켰으므로 +1.
            self._log_attempt(fail_key, feat, 0, 'abort',
                              dur=round(time.time() - t0, 2),
                              retries=_retries_before + 1)
            return False

        approach_pose = Pose()
        approach_pose.position = Point(x=tx, y=ty, z=self.APPROACH_HEIGHT)
        approach_pose.orientation = ori
        # [롤아웃 접근자세 고정] 시뮬에서 '하강이 닿은' 바로 그 팔자세로 접근한다.
        # 관절목표(joint goal)로 가야 그 IK 분기에 정확히 안착해 하강이 성립한다.
        # (직선 접근은 어느 분기로 도착할지 보장 못 해 하강이 다시 어긋난다.)
        if plan_app_joints is not None:
            ok_ap = self.plan_viz_execute_joint(
                plan_app_joints, vel=self._vel, label=f'Approach-{label}')
            if not ok_ap:
                return fail('접근 실패(롤아웃 자세)', 'approach_fail')
            # 하강 단계로 진행 (아래 공통 경로)
        else:
            ok_ap = False
        # [직선 운송 — 불필요한 비틀림 제거] 관절공간 계획(RRT)은 시작·목표
        # 관절값 사이를 임의의 관절 곡선으로 잇기 때문에, 훤히 뚫린 공중
        # 이동에서도 팔이 크게 비틀며 도는 경로가 나온다(사용자 관찰).
        # 이동은 눈에 보이는 대로 '현재 TCP → 접근 pose 직선'(Cartesian,
        # 자세는 구면보간)으로 먼저 계획하고, 직선이 안 나올 때만(장애물·
        # 특이점·관절 점프) 기존 IK 관절목표(RRT)로 폴백한다.
        if not ok_ap and plan_app_joints is None:
            ok_ap = self.cartesian_viz_execute(
                [approach_pose], label=f'Approach-{label}', vel=self._vel,
                allow_fallback=False, min_fraction=0.98, log_fail=False)
        ik_goal = None
        if not ok_ap:
            self.get_logger().info(
                f'[{label}] 직선 접근 불가 — IK 관절목표(RRT)로 폴백')
            ik_goal = self._ik_joint_goal(approach_pose)
        if not ok_ap and ik_goal is not None:
            ok_ap = self.plan_viz_execute_joint(
                ik_goal, vel=self._vel, label=f'Approach-{label}')
        elif not ok_ap:
            self.get_logger().warn(
                f'[{label}] 접근 IK(ready 시드) 실패 — pose 목표(RRT)로 폴백. '
                f'하강 시작 자세가 임의가 되어 실패 확률이 높아집니다')
            ok_ap = self.plan_viz_execute(
                approach_pose, label=f'Approach-{label}')
        if not ok_ap:
            return fail('접근 실패', 'approach_fail')

        # --- 하강 직전 자세 재취득 ---
        # Step B 에서 잠근 좌표는 접근(수 초) 동안 이미 낡았을 수 있다. 무더기는
        # 옆 볼트가 굴러오거나 자체 안착으로 계속 움직인다. 씬에서 이웃을 빼기
        # '전에' 최신 센싱값과 대조한다(취소해도 씬이 온전히 남는다).
        fresh = self._bolt_sensed.get(bolt_id) if bolt_id else None
        if fresh is not None and sensed_at_lock is not None:
            old = sensed_at_lock[0]
            new = fresh[0]
            moved = math.dist(old, new)
            if moved > self.POSE_REFRESH_TOL:
                # 접근 자세(ori)·개구는 옛 위치 기준으로 이미 굳었다.
                # 여기서 다시 푸는 것보다 깨끗이 접고 다시 계획하는 게 안전.
                return abort(
                    f'하강 직전 볼트가 {moved * 1000:.1f}mm 이동 '
                    f'(허용 {self.POSE_REFRESH_TOL * 1000:.0f}mm)')
            if moved > 1e-6:
                # 허용 오차 안 — 움직인 만큼만 목표를 평행이동한다(외부 pose 의
                # 고유 오프셋은 보존). 자세/개구는 4mm 이내 변화라 그대로 유효.
                pos = (pos[0] + new[0] - old[0],
                       pos[1] + new[1] - old[1],
                       pos[2] + new[2] - old[2])
                tx, ty = pos[0], pos[1]
                grasp_z = self._grasp_z_for(pos[2])
                self.get_logger().info(
                    f'[{label}] 하강 직전 자세 재취득: {moved * 1000:.1f}mm 이동 '
                    f'→ ({tx:.3f}, {ty:.3f}, z={grasp_z:.3f})')

        # 무더기 속으로 손가락을 넣어야 하므로, 대상 볼트와 '바로 옆 이웃'을
        # 잠시 씬에서 뺀다. 그러지 않으면 이웃과의 충돌로 하강 fraction 이 떨어지고
        # 곡선 폴백이 통 안을 쓸어버린다. (다음 사이클 refresh 가 자동 복원)
        near = self._neighbors_within(pos, self.PICK_CLEAR_R, bolt_id)
        if near:
            self.remove_collision_objects(near)
            self.get_logger().info(
                f'[{label}] 하강 위해 임시 제거: {", ".join(near)}')
        # [적응형 하강 깊이] 바닥 충돌모델은 그대로 둔 채, '계획이 실제로
        # 통과하는 가장 깊은 목표'를 자동으로 찾는다. grasp_z 부터 시작해
        # GRASP_RAISE_STEP(2mm)씩 목표를 올려 가며 재계획하되, 손가락이
        # 샤프트 상반부를 물 수 있는 한계(볼트중심 + GRASP_MAX_ABOVE)까지만.
        # → "바닥에 닿지는 않지만 파지를 위해 최대한 내려간다"를 계획기가
        #   스스로 실현한다. 재계획은 서비스 호출뿐이라(실행 없음) 비용이 없다.
        # [Issue A] 게이트는 GRASP_MIN_FRACTION(0.995) 유지 — 끝점 도달이 생명.
        z_cap = pos[2] + self.GRASP_MAX_ABOVE      # 이보다 높으면 어차피 빈손
        z_try = grasp_z
        descended = False
        while z_try <= z_cap + 1e-9:
            descent = self.make_vertical_waypoints(
                tx, ty, self.APPROACH_HEIGHT, z_try, ori)
            if self.cartesian_viz_execute(descent, label=f'Descend-{label}',
                                          vel=self._vel_fine,
                                          allow_fallback=False,
                                          min_fraction=self.GRASP_MIN_FRACTION):
                descended = True
                break
            z_next = z_try + self.GRASP_RAISE_STEP
            if z_next <= z_cap + 1e-9:
                self.get_logger().info(
                    f'[{label}] 목표 z={z_try:.4f} 하강 불가 → '
                    f'{z_next:.4f} 로 {self.GRASP_RAISE_STEP * 1000:.0f}mm '
                    f'올려 재계획 (한계 {z_cap:.4f})')
            z_try = z_next
        if not descended:
            # [기구학 하강 폴백] Cartesian 직선이 마지막 ~20mm 를 못 내려간 원인은
            # 충돌이 아니라(이웃 제거·바닥 여유 확인됨) 기구학이다: 직선 보간은
            # 1cm 마다의 '모든' 중간점에 관절점프 없는 IK 를 요구하므로, 끝점
            # 자체는 도달 가능해도 중간 한 점의 손목 뒤집힘에서 전체가 잘린다.
            # → 끝점(파지 pose)의 IK 를 '현재 접근 자세를 시드로' 직접 풀어,
            #   그 관절해로 짧게 관절공간 이동한다(벽은 씬에 남아 있어 RRT 가
            #   자동 회피, 이웃은 이미 제거). FK 로 실제 도달 z 를 반드시 재확인.
            self.get_logger().info(
                f'[{label}] 직선 하강 불가 — 파지 pose IK 직접 풀어 관절이동 시도')
            grasp_pose = Pose()
            grasp_pose.position = Point(x=tx, y=ty, z=grasp_z)
            grasp_pose.orientation = ori
            seed = self._arm_joint_positions()   # 현재(접근) 관절을 시드로
            gik = self._ik_joint_goal(grasp_pose, seed=seed)
            if gik is not None and self.plan_viz_execute_joint(
                    gik, vel=self._vel_fine, label=f'DescendJoint-{label}'):
                descended = True
                z_try = grasp_z
        if not descended:
            return fail('하강 실패(파지 가능 깊이까지 도달 불가)', 'descend_fail')
        if z_try > grasp_z:
            self.get_logger().info(
                f'[{label}] 적응 깊이 채택: z={z_try:.4f} '
                f'(원래 목표 {grasp_z:.4f}보다 {(z_try - grasp_z) * 1000:.0f}mm 위)')
        grasp_z = z_try      # 이후 FK 검증/리프트 기준도 실제 채택 깊이로
        # 계획이 100% 여도 컨트롤러가 못 따라갔을 수 있다 → FK 실측으로 재확인.
        # 여기를 통과해야만 손가락을 닫는다.
        if not self.verify_descent_reached(grasp_z, label):
            return fail('하강 미달 — 파지 높이에 도달하지 못함', 'descend_short')

        self.gripper_close()
        self._grasp_closed = True      # 씬 부착과 무관하게 '물리적으로 닫힘'
        # [지상진실 파지 판정] 손가락 폭만으론 sim 에서 손가락이 얇은 볼트를
        # 관통하면(1.5mm) '정확히 잡았는데도 빈손'으로 오판한다(사용자 확인).
        # → 손끝 폭은 참고로만 찍고, 최종 판정은 '리프트 후 볼트가 실제로 그리퍼를
        #   따라 올라왔는가'(센싱 z 상승)로 한다. 이게 sim 지상진실이라 확실하다.
        w0 = self._sample_finger()
        self.get_logger().info(
            f'[{label}] 닫힘 후 손가락 {(w0 or 0.0) * 1000:.2f}mm(참고) — '
            f'실제 파지는 리프트 후 볼트 상승으로 확정')
        # [데스크톱 통신] grasp_result/RESULT 로 나갈 지상진실 지표. 리프트
        # 재검증 분기(아래)에서 값이 채워지고, 그 전에 실패하면 None 그대로
        # 나간다(측정 자체가 안 됐으므로) — 두 분기 모두 항상 바인딩되게
        # 여기서 미리 초기화해 둔다.
        bolt_rise_m = None
        gripper_width_m = None
        # 파지 전 볼트 높이(지상진실 기준점). 볼트는 부착돼도 Gazebo pose 발행이
        # 계속되므로 _bolt_sensed 로 실제 위치를 추적할 수 있다.
        z_before = (self._bolt_sensed[bolt_id][0][2]
                    if bolt_id and bolt_id in self._bolt_sensed else None)
        if not self.attach_bolt(bolt_id if bolt_id else 'picked_bolt'):
            return fail('씬 부착 실패', 'attach_fail')
        self._attached_src_id = bolt_id
        self._spin_sleep(0.2 if self._auto else 0.3)

        lift = self.make_vertical_waypoints(
            tx, ty, grasp_z, self.APPROACH_HEIGHT, ori)
        if not self.cartesian_viz_execute(lift, label=f'Lift-{label}',
                                          vel=self._vel_fine):
            return fail('리프트 실패', 'descend_fail')
        # --- 지상진실 재검증: 볼트가 그리퍼를 따라 올라왔나 ---
        self._spin_sleep(0.25 if self._auto else 0.4)   # 센싱 갱신 여유
        if z_before is not None and bolt_id in self._bolt_sensed:
            z_after = self._bolt_sensed[bolt_id][0][2]
            rose = z_after - z_before
            bolt_rise_m = rose
            gripper_width_m = w0     # 이 분기는 폭 폴백을 안 타므로 닫힘 직후 참고값
            if rose < 0.10:            # 10cm 이상 안 올라왔으면 빈손(볼트 바닥에 남음)
                return fail(
                    f'리프트 후 볼트 미상승({rose * 1000:+.0f}mm, '
                    f'{z_before:.3f}→{z_after:.3f}) — 실제로 못 물었음',
                    'empty_after_lift',
                    metrics={'bolt_rise_m': bolt_rise_m, 'gripper_width_m': gripper_width_m})
            self.get_logger().info(
                f'[{label}] 파지 확정 — 볼트가 그리퍼 따라 상승 '
                f'{z_before:.3f}→{z_after:.3f} (+{rose * 1000:.0f}mm)')
        else:
            # 볼트 id 센싱 불가(외부 pose 등) → 손끝 폭 폴백
            w = self._sample_finger(settle_sec=0.2)
            gripper_width_m = w
            if not self._finger_width_is_grasp(w):
                return fail(
                    f'리프트 후 빈손(손가락 {(w or 0.0) * 1000:.2f}mm, '
                    f'볼트 추적 불가)', 'empty_after_lift',
                    metrics={'bolt_rise_m': bolt_rise_m, 'gripper_width_m': gripper_width_m})
            self.get_logger().info(
                f'[{label}] (볼트 추적 불가) 손끝 폭 폴백 통과 {w * 1000:.2f}mm')
        if bolt_id:
            self._picked.add(bolt_id)
        self._attempts.pop(fail_key, None)
        # 무더기가 실제로 바뀌었다 → 진전 epoch 를 올려 모든 볼트의 실패 스트릭을
        # 무효화하고, 이웃에 막혀 보류했던 볼트를 전부 재검토 대상으로 되돌린다.
        self._note_progress()
        # [R4] 성공 라벨(1) — 리프트 후 재검증까지 통과한 '진짜 파지'만 여기 온다.
        # [데스크톱 통신] 여기는 _note_attempt_failed 를 안 거치므로(방금 성공)
        # retries 는 미조정 값 — "이번 성공 직전까지의" 연속 실패수라는 뜻.
        self._log_attempt(fail_key, feat, 1, 'success',
                          dur=round(time.time() - t0, 2),
                          metrics={'bolt_rise_m': bolt_rise_m, 'gripper_width_m': gripper_width_m},
                          retries=_retries_before)
        return True

    def _drop(self):
        """Step D — 놓는 통의 '빈 자리' 위로 가서 툭 떨어뜨린다."""
        slot, clear, is_free = self._free_drop_slot()
        qx, qy = slot if slot else (None, None)
        self.get_logger().info(
            f'놓을 자리 ({qx:+.3f}, {qy:.3f}) — '
            f'{"빈 자리" if is_free else "전부 참, 가장 여유로운 곳"} '
            f'(최근접 볼트 {clear * 1000:.0f}mm)')

        held = self._attached_id
        # drop_bin 이 +Y 에 있어 손목 한계를 피하려 yaw 90° 고정(파지와 달리
        # 놓기는 볼트 자세를 맞출 필요가 없으므로 하드코딩해도 무방)
        ori_drop = self.euler_to_quaternion(math.pi, 0.0, math.pi / 2)

        def fail(msg):
            self.get_logger().error(f'[놓기] {msg}')
            src = self._attached_src_id
            released = False
            # 씬 부착 여부가 아니라 '물리적으로 닫혀 있는지'로 판단해 반드시 편다
            if self._grasp_closed or self._bolt_attached:
                self.gripper_open()
                self._grasp_closed = False
                if self._attached_id:
                    dropped = self._attached_id
                    ok_d = self.detach_bolt(dropped)
                    self.remove_collision_objects([dropped])
                    released = ok_d
                else:
                    released = True
            self._attached_src_id = None
            # 릴리즈가 실제로 끝난 경우에만 재선택 후보로 되돌린다.
            # (부착이 안 풀린 채 되돌리면 refresh 가 그리퍼 위치에 볼트를 재등록해
            #  시작 자세가 충돌로 판정되는 그 버그가 재현된다)
            if src and released:
                d = self._drop_fail.get(src, 0) + 1
                self._drop_fail[src] = d
                if d >= self.MAX_PICK_RETRY:
                    self.get_logger().warn(
                        f'[놓기] {src} {d}회 실패 — 이 볼트는 포기합니다')
                    self._blacklist.add(src)
                else:
                    self._picked.discard(src)   # 다시 시도할 수 있게 복귀
            self.plan_viz_execute_joint(
                self._ready_target, vel=self._vel, label='Home')
            return False

        if slot is None:
            return fail('놓을 슬롯을 못 찾음')
        above = Pose()
        above.position = Point(x=qx, y=qy, z=self.APPROACH_HEIGHT)
        above.orientation = ori_drop
        # 운반도 직선 우선(비틀림 제거) — 안 되면 기존 RRT 폴백
        ok_to = self.cartesian_viz_execute(
            [above], label='ToDropBin', vel=self._vel,
            allow_fallback=False, min_fraction=0.98, log_fail=False)
        if not ok_to:
            self.get_logger().info('[놓기] 직선 운반 불가 — RRT 로 폴백')
            ok_to = self.plan_viz_execute(
                above, vel=self._vel, label='ToDropBin')
        if not ok_to:
            return fail('놓는 통 위 이동 실패')

        # 통 벽(0.025) 위에서 멈춘다 — 바닥까지 안 내려가므로 계획이 쉽고 안전
        down = self.make_vertical_waypoints(
            qx, qy, self.APPROACH_HEIGHT, self.DROP_Z, ori_drop)
        if not self.cartesian_viz_execute(down, label='DropDescend',
                                          vel=self._vel_fine):
            return fail('놓기 하강 실패')

        if not self.gripper_open():
            self.get_logger().warn('[놓기] 그리퍼 열기 실패 — 물체 미분리 가능')
        self._grasp_closed = False
        if self._attached_src_id:
            self._drop_fail.pop(self._attached_src_id, None)
        if held:
            self.detach_bolt(held)
            # 놓은 볼트는 임무 완료 → 씬에서 제거(그리퍼 아래 유령 충돌 방지)
            self.remove_collision_objects([held])
        self._attached_src_id = None
        self._spin_sleep(0.4 if self._auto else 0.8)   # 볼트 안착 여유
        self.get_logger().info(f'툭 놓기 완료 (TCP z={self.DROP_Z:.3f})')
        return True

    # =========================================================
    # 메인 시나리오
    # =========================================================
    def run(self):
        self.get_logger().info(
            '[RViz2 안내] MarkerArray Display → /pick_place_markers, '
            'Planning Scene Display 추가. Fixed Frame: fr3_link0')
        self.get_logger().info(
            f'[외부 비전] 최적 볼트 6D 자세를 {self.EXT_POSE_TOPIC} '
            '(geometry_msgs/PoseStamped) 로 보내면 그걸로 집습니다.\n'
            '  없으면 센싱된 볼트 중 가장 위에 있는 것을 자체 선택합니다.')

        self.wait_for_ready()
        # 초기/폴백 배치가 어디서 왔는지 로그에 남긴다 — '랜덤 배치 파일' 이
        # 아니라 '고정 배치'가 찍히면 spawn_bolts.launch.py 를 새로 실행하지
        # 않았다는 뜻이다(랜덤 스폰 미적용).
        self.get_logger().info(f'[배치] {LAYOUT_SOURCE}')
        self._ready_target = self.load_named_pose('ready')
        self.get_logger().info(f'ready: {self._ready_target}')

        # ---- 장면 구성: 집는 통 + 놓는 통 + 볼트 무더기 ----
        if self.STEP_BY_STEP:
            self._wait_for_trigger(
                '>>> [대기] 장면 구성(집는 통 + 놓는 통 + 볼트 무더기) 신호 대기 중...')
        self.get_logger().info('=== 충돌 객체 등록 ===')
        scene_objs = [drop_bin_collision_object()] + bolt_collision_objects()
        if self.USE_PICK_BIN:
            co = bin_collision_object()
            if not self.PICK_BIN_FLOOR:
                # 통 '바닥' 박스(boxes[0])를 계획용 충돌에서 뺀다 — 이게 그리퍼
                # 하강을 막던 범인. 벽 4개는 남겨 운반 중 벽 회피는 유지한다.
                co.primitives = co.primitives[1:]
                co.primitive_poses = co.primitive_poses[1:]
                self.get_logger().info(
                    '[씬] 집는 통: 벽만 등록(바닥 박스 제외 — 하강 방해 제거)')
            scene_objs = [co] + scene_objs
        if not self.add_collision_objects(scene_objs):
            self.get_logger().error('충돌 객체 등록 실패 — 중단')
            return
        self._objects_added = True
        self.add_label_marker((BIN_XYZ[0], BIN_XYZ[1], 0.06), 'Pick Bin')
        self.add_label_marker(
            (DROP_BIN_XYZ[0], DROP_BIN_XYZ[1], 0.06), 'Drop Bin')
        self._spin_sleep(1.0)

        # =====================================================
        # 실시간 루프:  Ready → 자세 수신 → 파지 → 툭 놓기 → Ready
        # =====================================================
        cycle = 0
        n_done = 0
        # 한 번의 /next_step 신호 = '볼트 하나를 통에 넣을 때까지' 자동 진행.
        # 파지·놓기에 실패해도 새 신호를 기다리지 않고(재입력 불필요) 곧바로 다시
        # 최적 볼트를 골라 재시도한다. 볼트 하나를 실제로 옮겨야 다음 신호를
        # 기다린다. (연속 무인 운전을 원하면 STEP_BY_STEP=False → 신호 없이 통을
        # 다 비운다.) 첫 사이클은 True → 볼트 스폰/센싱을 기다리는 초기 게이트 유지.
        need_trigger = True
        while rclpy.ok():
            cycle += 1

            # --- Step A: Ready 자세에서 대기 ---
            # 직전 시도가 '아무것도 안 쥔 실패'면 팔이 접근 높이에 그대로 있다.
            # Ready 왕복 + 그리퍼 재개방은 순수 낭비 → 생략하고 제자리 재선택.
            if self._skip_ready:
                self._skip_ready = False
                self.get_logger().info(
                    f'--- [{cycle}] Step A: 생략(제자리 재선택 — 왕복 제거) ---')
            else:
                self.get_logger().info(f'--- [{cycle}] Step A: Ready 복귀 ---')
                if not self.plan_viz_execute_joint(
                        self._ready_target, vel=self._vel,
                        label=f'Ready{cycle}'):
                    self.get_logger().error('ready 이동 실패 — 중단')
                    break
                self.gripper_open()
                self._spin_sleep(0.2 if self._auto else 0.5)
            self._refresh_bolt_scene()      # 씬을 실제 볼트 위치로 갱신

            if self.STEP_BY_STEP and need_trigger:
                self._wait_for_trigger(
                    f'>>> [대기] [{cycle}] 다음 볼트 집기 신호 대기 중...')

            # --- 센싱 게이트: '현재' 볼트 위치를 모르면 파지를 시작하지 않는다 ---
            # Ready 복귀 때마다 씬은 갱신하지만, 그 갱신의 원천(pose 센싱)이
            # 죽어 있으면 스폰 좌표를 재확인하는 무의미한 동작이 된다. 그런
            # 상태로 내려가면 볼트 없는 곳을 쥐므로, 센싱이 살아날 때까지
            # 3초 간격으로 재확인만 하고 파지는 하지 않는다.
            if self.REQUIRE_SENSING and not self._bolt_sensed:
                self.get_logger().error(
                    f'[{cycle}] 볼트 pose 센싱 0건 — 현재 볼트 위치를 알 수 '
                    f'없어 파지를 진행하지 않습니다(허공 파지 방지). '
                    f'센싱 수신까지 3초 간격 재확인.\n'
                    f'  ① ros2 topic hz /model/bolt_0/pose 로 발행 확인\n'
                    f'  ② 안 나오면 Gazebo(터미널1)를 완전히 재시작한 뒤 '
                    f'spawn_bolts.launch.py(터미널2)를 새로 실행하세요.\n'
                    f'  ③ 스폰 전부터 볼트가 이미 보였다면 이전 세션 잔재입니다 '
                    f'— 그 볼트들은 pose 를 발행하지 않을 수 있습니다')
                self._spin_sleep(3.0)
                need_trigger = False    # 신호 재요구 없이 자동 재확인
                continue

            # --- Step B: 최적 볼트 6D 자세 수신(외부 우선, 없으면 자체 선택) ---
            self.get_logger().info(
                f'--- [{cycle}] Step B: 최적 볼트 자세 수신 대기 '
                f'({self.EXT_POSE_TOPIC}, 최대 {self._ext_pose_wait:.1f}s) ---')
            # get_next_optimal_bolt_pose 는 외부 pose 우선, 없으면 _select_fallback
            # (학습 랭킹 또는 휴리스틱)로 고른다. 학습 경로가 고른 계획은
            # self._pending_plan 에 실려 오므로 _pick 에 그대로 넘긴다(R3).
            target = self.get_next_optimal_bolt_pose()
            if target is None:
                self.get_logger().info('집을 볼트 없음 — 루프 종료')
                break
            plan = self._pending_plan       # 학습 선택 계획(없으면 None)

            # --- Step C: 그리퍼 각도를 볼트 축에 맞춰 동적 파지 ---
            self.get_logger().info(f'--- [{cycle}] Step C: 파지 ---')
            if not self._pick(target, plan=plan):
                need_trigger = False         # 실패 → 신호 없이 곧바로 자동 재시도
                continue                     # Ready 로 돌아가 다음 볼트 재선택

            # --- Step D: 놓는 통의 빈 자리에 툭 놓기 ---
            self.get_logger().info(f'--- [{cycle}] Step D: 놓는 통에 놓기 ---')
            if self._drop():
                n_done += 1
                need_trigger = True          # 하나 완수 → 다음 볼트는 신호 대기
            else:
                need_trigger = False         # 놓기 실패도 신호 없이 자동 재시도
            self.get_logger().info(f'--- [{cycle}] 완료 (누적 {n_done}개) ---')

        # ---- 마무리 ----
        self.get_logger().info(f'=== 종료: 총 {n_done}개 옮김 ===')
        # [R4] 에피소드 종료 시 전체 재적합 + 저장 — "시뮬 1회 끝날 때마다 자동으로
        # 더 똑똑해짐". 이번 실행에서 append 된 시도까지 모두 반영해 모델을 굳힌다.
        self._finalize_selector()
        # Ctrl-C 로 빠져나온 경우 context 가 죽어 있어 서비스/액션 호출이 예외를
        # 던진다. 정리는 main() 의 finally 에 맡기고 여기서는 건너뛴다.
        if rclpy.ok():
            self.plan_viz_execute_joint(
                self._ready_target, vel=0.3, label='Ready')
            self._spin_sleep(0.5)
        self.get_logger().info('=== 통합 Pick & Place 완료! ===')

    def run_auto_picking(self):
        """[R5] 단일 호출 자동 실행 편의 래퍼.

        STEP_BY_STEP 을 인스턴스 레벨에서 False 로 강제한 뒤 run() 을 호출한다.
        이러면 /next_step 트리거를 전혀 기다리지 않고 센싱→선택→파지→드롭→Ready
        전 사이클을 통이 빌 때까지 연속으로 자동 수행한다. CLI 의 --auto 인자나
        생성자 auto=True 와 동일한 효과이며, 코드에서 직접 자동 운전을 시작하고
        싶을 때 쓴다.
        """
        self.STEP_BY_STEP = False
        self.get_logger().info('[R5] run_auto_picking — 트리거 없이 연속 자동 운전')
        self.run()





def _install_run_logging():
    """이 프로세스가 stdout/stderr 에 남기는 모든 것(= ROS/rclpy 로그 포함)을
    고정 경로 파일에도 그대로 복사한다. 콘솔 출력은 유지된다.

    ⚠ rclpy 로그는 파이썬 sys.stderr '객체'가 아니라 C 레벨에서 파일서술자 2
      (fd 2)로 바로 나간다. 그래서 sys.stdout/sys.stderr 를 바꾸는 것으로는 못
      잡고, fd 자체를 파이프로 돌린 뒤(os.dup2) 읽기 스레드가 콘솔과 파일에
      동시에 기록하는 'fd 레벨 tee' 를 쓴다.

    파일:
      ~/pick_place_logs/latest.log    ← 항상 같은 이름(가장 최근 실행). 바로 열람용
      ~/pick_place_logs/run_<시각>.log ← 실행별 보존본(과거 로그 유실 방지)

    반환: latest.log 경로. 설정 실패 시 None(그래도 노드는 정상 실행).
    """
    try:
        log_dir = os.path.expanduser('~/pick_place_logs')
        os.makedirs(log_dir, exist_ok=True)
        stamp = time.strftime('%Y%m%d_%H%M%S')
        latest = os.path.join(log_dir, 'latest.log')
        history = os.path.join(log_dir, f'run_{stamp}.log')

        saved = os.dup(1)                       # 원래 콘솔 fd 보존(계속 콘솔에 출력)
        r, w = os.pipe()
        fds = [saved]
        for p in (latest, history):
            fds.append(os.open(p, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o644))

        header = (f'===== 실행 시작 {stamp} '
                  f'(latest.log / run_{stamp}.log) =====\n').encode()
        for fd in fds[1:]:
            os.write(fd, header)

        def _pump():
            # 파이프에서 읽어 콘솔 + 파일들에 동시 기록. 모든 write 끝(fd 1/2)이
            # 닫히면 EOF → 종료(daemon 스레드라 프로세스 종료도 막지 않는다).
            while True:
                try:
                    data = os.read(r, 65536)
                except OSError:
                    break
                if not data:
                    break
                for fd in fds:
                    try:
                        os.write(fd, data)
                    except OSError:
                        pass
        threading.Thread(target=_pump, daemon=True).start()

        os.dup2(w, 1)     # stdout → 파이프
        os.dup2(w, 2)     # stderr(rclpy 로그) → 파이프
        os.close(w)       # fd 1/2 가 write 끝을 잡고 있으므로 원본 w 는 닫아도 됨
        return latest
    except Exception:
        return None       # 로깅 설정 실패해도 데모는 굴러가야 한다


def main(args=None):
    log_path = _install_run_logging()
    rclpy.init(args=args)
    # [R5] --auto 면 트리거 없이 전 사이클 연속 자동 운전. (sys 는 상단에서 임포트)
    auto = '--auto' in sys.argv
    node = IntegratedPickPlace(auto=auto)
    if log_path:
        node.get_logger().info(
            f'[로그] 이 실행의 모든 로그를 파일에도 기록합니다 → {log_path}')
    try:
        node.run()
    except KeyboardInterrupt:
        node.get_logger().info('사용자에 의해 종료됨')
    finally:
        # 충돌 객체를 실제로 등록한 경우에만 정리(서비스 미기동 상태의 이른
        # 종료에서 불필요한 타임아웃 대기를 피함)
        if getattr(node, '_objects_added', False):
            try:
                node._cleanup_scene()
            except Exception:
                pass
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
