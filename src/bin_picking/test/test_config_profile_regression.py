# -*- coding: utf-8 -*-
"""`config.py` 프로파일 주입 회귀 — "모델을 바꿔도 기능은 완전히 동일"의 최종 증명.

`test_robot_profiles.py` 는 **프로파일 파일**이 옛 상수와 같음을 본다. 이 파일은 그
다음 단계 — 프로파일이 `PickPlaceConfig` 에 꽂힌 **결과**가 리팩토링 전과 같은지를
본다. 둘은 다른 실패를 잡는다:

  - 프로파일에는 값이 맞게 적혀 있는데 `apply_profile()` 이 엉뚱한 칸에 꽂는 경우
  - 유도 상수(GRASP_DETECT_MIN, GRASP_FLOOR_Z) 재계산을 빼먹어 이름만 새 로봇이고
    물리는 옛 로봇인 경우 ← 가장 찾기 힘든 종류

⚠ 이 파일만 ROS 를 필요로 한다(`config.py` 가 rclpy/moveit_msgs 를 임포트한다).
  ROS 가 없으면 **건너뛴다** — 건너뛴 사실이 pytest 출력에 남으므로, 통과가
  '검사를 건너뛴 통과'인지 구분할 수 있다.
"""
import pytest

pytest.importorskip('rclpy', reason='config.py 는 ROS 환경이 필요하다')
pytest.importorskip('moveit_msgs', reason='config.py 는 ROS 환경이 필요하다')

from bin_picking import config as _config              # noqa: E402
from bin_picking import robot_profiles as _profiles     # noqa: E402
from bin_picking.config import PickPlaceConfig as C     # noqa: E402
from bin_picking.geometry import GeometryMixin          # noqa: E402


@pytest.fixture(autouse=True)
def _pin_fr3():
    """이 파일의 모든 검사는 FR3 주입 결과를 본다 → 활성 모델과 무관하게 고정.

    `config.py` 는 import 시점에 '활성 모델'을 꽂는다(머신의
    ~/.config/bin_picking/active_model 나 BIN_PICKING_ROBOT_MODEL 에 좌우됨).
    누군가 `binpick_model use <다른모델>` 을 했거나 같은 프로세스의 다른 테스트가
    프로파일을 갈아끼우면 여기 FR3 리터럴 대조가 엉뚱한 모델을 보고 깨진다.
    회귀의 대상은 'FR3 프로파일 주입'이므로 매 검사 직전에 FR3 를 되꽂아
    결정론적으로 만든다.
    """
    _config.apply_profile(_profiles.get('fr3'))
    yield


class _Geom(C, GeometryMixin):
    """상수(PickPlaceConfig) + 순수 기하(GeometryMixin) 합성.

    `_grasp_z_for` 같은 계산은 GeometryMixin 에 있고 `cls.GRASP_FLOOR_Z` 를 읽는다.
    실제 노드(`IntegratedPickPlace`)가 두 클래스를 상속해 얻는 것과 같은 조합을
    여기서 최소한으로 재현한다 — rclpy 노드를 띄우지 않고 순수 계산만 검증하려고.
    """


# 커밋 392572b 시점 `config.py` 에서 손으로 옮겨 적은 리터럴.
# 프로파일에서 유도하지 말 것 — 그러면 아무것도 증명하지 못한다.
_LEGACY = {
    'PLANNING_GROUP': 'fr3_arm',
    'REFERENCE_FRAME': 'fr3_link0',
    'END_EFFECTOR_LINK': 'fr3_hand_tcp',
    'ARM_JOINTS': ['fr3_joint1', 'fr3_joint2', 'fr3_joint3',
                   'fr3_joint4', 'fr3_joint5', 'fr3_joint6', 'fr3_joint7'],
    'GRIPPER_JOINT': 'fr3_finger_joint1',
    'GRIPPER_ACTION': '/fr3_gripper_controller/follow_joint_trajectory',
    'GRIPPER_OPEN': 0.04,
    'GRIPPER_CLOSED': 0.0015,
    'BOLT_SHAFT_RADIUS': 0.004,
    'GRASP_DETECT_MAX': 0.009,
    'GRASP_FLOOR_CLEAR': 0.0005,
    'TCP_TO_FINGERTIP': 0.0095,
    'GRASP_MIN_FRACTION': 0.995,
    'GRASP_Z_TOL': 0.003,
    'GRASP_RAISE_STEP': 0.002,
    'GRASP_MAX_ABOVE': 0.006,
    'GRASP_FLOOR_RAISE': 0.0,
    'PICK_CLEAR_R': 0.075,
    'IK_SEED_JITTER': 1,
    'IK_SEED_SPREAD': 1.2,
    'POSE_REFRESH_TOL': 0.004,
    'FINGER_HALF_W': 0.0044,
    'FINGER_TIP_HALF_X': 0.011,
    'GRASP_SAFETY': 0.003,
    'SWEEP_SAFETY': 0.0015,
    'GRASP_MIN_OPEN': 0.009,
    'GRASP_PREGRASP_OPEN': 0.010,
    'APERTURE_STEP': 0.004,
    'APERTURE_SCAN_R': 0.090,
    'REACH_Y_MAX': 0.063,
    'REACH_X_FAR': 0.45,
    'APPROACH_HEIGHT': 0.25,
    'TILT_MIN_CENTER_Z': 0.020,
    'TILT_CANDIDATES_DEG': (15.0, 30.0),
    'TILT_PRIOR_PENALTY': 0.02,
    'LIMIT_MARGIN': 0.10,
    'DESCENT_STEP': 0.05,
    'CART_MAX_STEP': 0.01,
    'MIN_FRACTION': 0.9,
    'DROP_Z': 0.040,
    'MAX_PICK_RETRY': 3,
    'MAX_NO_PROGRESS': 3,
    'PLANNER_FALLBACK': ['RRTConnectkConfigDefault', 'RRTkConfigDefault',
                         'ESTkConfigDefault', 'KPIECEkConfigDefault',
                         'PRMkConfigDefault'],
    'JOINT_LIMITS': {
        'fr3_joint1': (-2.7437, 2.7437),
        'fr3_joint2': (-1.7837, 1.7837),
        'fr3_joint3': (-2.9007, 2.9007),
        'fr3_joint4': (-3.0421, -0.1518),
        'fr3_joint5': (-2.8065, 2.8065),
        'fr3_joint6': (0.5445, 4.5169),
        'fr3_joint7': (-3.0159, 3.0159),
    },
}


@pytest.mark.parametrize('name', sorted(_LEGACY))
def test_constant_unchanged(name):
    """리팩토링 전후로 상수 값이 하나도 안 바뀌었다."""
    assert getattr(C, name) == _LEGACY[name], (
        f'{name} 이 리팩토링 전 값과 다르다 — "기능 완전 동일" 약속이 깨졌다')


def test_pinned_model_is_fr3():
    """이 파일이 보는 것은 'FR3 를 꽂은 결과'다.

    ⚠ 이름이 곧 기본 모델이라는 뜻은 아니다 — 기본 모델은 2026-08-31 에
      `ur5e_robotiq_hande` 로 옮겼다(registry.DEFAULT_MODEL). 여기서는 위
      `_pin_fr3` 픽스처가 매 검사 직전에 FR3 를 되꽂아 회귀 대조를 결정론적으로
      만든다. 그게 실제로 먹혔는지 확인하는 검사다.
    """
    assert C.ROBOT_MODEL == 'fr3'
    assert C.ROBOT_PROFILE.name == 'fr3'


# ---- 유도 상수: 프로파일에서 다시 계산된 값이 옛 공식 결과와 같은가 ----
def test_grasp_detect_min_derivation():
    """(허공 닫힘폭 + 샤프트 반경)/2 = (0.0015 + 0.004)/2 = 0.00275."""
    assert C.GRASP_DETECT_MIN == pytest.approx(0.00275, abs=1e-12)


def test_grasp_floor_z_derivation():
    """통 바닥상면(0.005) + 손끝오프셋(0.0095) + 여유(0.0005) = 0.015."""
    assert C.GRASP_FLOOR_Z == pytest.approx(0.015, abs=1e-12)


def test_bin_floor_and_rest_center_unchanged():
    assert C.BIN_FLOOR_TOP == pytest.approx(0.005, abs=1e-12)
    assert C.BIN_WALL_TOP == pytest.approx(0.025, abs=1e-12)
    assert C.BOLT_REST_CENTER_Z == pytest.approx(0.009, abs=1e-12)


# ---- 파지 판정: 단위 정규화 후에도 경계가 그대로인가 ----
@pytest.mark.parametrize('joint_value,expected', [
    (None, False),        # 관측 불가 → 보수적으로 실패
    (0.0015, False),      # 허공에서 끝까지 닫힘
    (0.00274, False),     # 경계 바로 아래
    (0.00275, True),      # 경계
    (0.004, True),        # M8 샤프트 반경에서 정지 = 파지
    (0.0065, True),       # 머리를 물어도 통과
    (0.009, True),        # 상한
    (0.00901, False),     # 아예 닫히지 않음
    (0.010, False),
])
def test_grasp_detection_boundaries(joint_value, expected):
    assert _Geom._finger_width_is_grasp(joint_value) is expected


def test_franka_hand_halfwidth_is_identity():
    """프랑카 핸드는 관절값이 곧 반개구 — 변환이 값을 바꾸면 판정이 어긋난다."""
    for v in (0.0, 0.0015, 0.004, 0.04):
        assert _Geom._finger_halfwidth(v) == v


@pytest.mark.parametrize('bolt_center_z,expected', [
    (0.010, 0.015),   # 바닥 볼트 → 바닥 한계가 지배
    (0.024, 0.024),   # 얹힌 볼트 → 패드 중심 = 볼트 중심
])
def test_grasp_z_for(bolt_center_z, expected):
    assert _Geom._grasp_z_for(bolt_center_z) == pytest.approx(expected, abs=1e-12)


# ---- 프로파일 기반 목록이 옛 하드코딩과 같은가 ----
def test_gripper_state_joints_match_legacy_hardcoding():
    """robot_state.py 가 쓰던 ['fr3_finger_joint1', 'fr3_finger_joint2']."""
    assert C.GRIPPER_STATE_JOINTS == ['fr3_finger_joint1', 'fr3_finger_joint2']


def test_touch_links_match_legacy_hardcoding():
    """scene.py 가 쓰던 ['fr3_hand','fr3_leftfinger','fr3_rightfinger',TCP]."""
    assert C.GRIPPER_TOUCH_LINKS == [
        'fr3_hand', 'fr3_leftfinger', 'fr3_rightfinger', 'fr3_hand_tcp']


def test_controller_names():
    assert C.ARM_CONTROLLER == 'fr3_arm_controller'
    assert C.GRIPPER_CONTROLLER == 'fr3_gripper_controller'


def test_bolt_scene_reference_frame_matches():
    """bolt_scene 의 기본 프레임이 프로파일과 갈리면 씬 객체가 엉뚱한 곳에 선다."""
    from bin_picking import bolt_scene
    assert bolt_scene.REFERENCE_FRAME == C.REFERENCE_FRAME
