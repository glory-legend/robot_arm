# -*- coding: utf-8 -*-
"""로봇 모델 프로파일 — 회귀 동일성 + 스키마/검증기 테스트.

ROS 무의존(`protocol.py` 테스트와 같은 원칙): Gazebo/rclpy 없이 이 파일 하나로
등록·검증 로직 전체를 돌린다.

이 파일의 가장 중요한 책임은 첫 번째 클래스다 — **FR3 프로파일이 리팩토링 전
`config.py` 상수와 한 값도 다르지 않음을 기계적으로 증명**하는 것. "모델을
바꿔도 기능은 완전히 동일해야 한다"는 요구는 곧 "기준 모델의 값이 하나도 안
변해야 한다"는 뜻이고, 그건 사람 눈이 아니라 테스트가 지켜야 한다.
"""
import copy
import os

import pytest

from bin_picking.robot_profiles import registry, schema
from bin_picking.robot_profiles import validator as V
from bin_picking.robot_profiles.schema import ProfileError, RobotProfile


# =====================================================================
# 1. 회귀 동일성 — 리팩토링 전 config.py 리터럴과 대조
# =====================================================================
# ⚠ 아래 값들은 커밋 392572b 시점 `config.py` 에서 **손으로 옮겨 적은 리터럴**이다.
#    프로파일에서 유도하면 안 된다 — 그러면 "프로파일이 프로파일과 같다"는
#    동어반복이 되어 아무것도 증명하지 못한다.
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
    'TCP_TO_FINGERTIP': 0.0095,
    'FINGER_HALF_W': 0.0044,
    'FINGER_TIP_HALF_X': 0.011,
    'GRASP_MIN_OPEN': 0.009,
    'GRASP_PREGRASP_OPEN': 0.010,
    'APERTURE_STEP': 0.004,
    'REACH_Y_MAX': 0.063,
    'REACH_X_FAR': 0.45,
    'APPROACH_HEIGHT': 0.25,
    'TILT_MIN_CENTER_Z': 0.020,
    'TILT_CANDIDATES_DEG': (15.0, 30.0),
    'LIMIT_MARGIN': 0.10,
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


@pytest.fixture(scope='module')
def fr3():
    return registry.get('fr3')


class TestFr3RegressionIdentity:
    """내장 fr3 프로파일 == 리팩토링 전 상수."""

    def test_arm_identifiers(self, fr3):
        assert fr3.arm.planning_group == _LEGACY['PLANNING_GROUP']
        assert fr3.arm.base_frame == _LEGACY['REFERENCE_FRAME']
        assert fr3.arm.tcp_frame == _LEGACY['END_EFFECTOR_LINK']
        assert list(fr3.arm.joints) == _LEGACY['ARM_JOINTS']
        assert fr3.arm.limit_margin == _LEGACY['LIMIT_MARGIN']

    def test_joint_limits(self, fr3):
        assert fr3.arm.joint_limits == _LEGACY['JOINT_LIMITS']

    def test_gripper(self, fr3):
        g = fr3.gripper
        assert g.command_joint == _LEGACY['GRIPPER_JOINT']
        assert g.action_name == _LEGACY['GRIPPER_ACTION']
        assert g.open_cmd == _LEGACY['GRIPPER_OPEN']
        assert g.closed_cmd == _LEGACY['GRIPPER_CLOSED']
        assert g.tcp_to_fingertip == _LEGACY['TCP_TO_FINGERTIP']
        assert g.finger_half_w == _LEGACY['FINGER_HALF_W']
        assert g.finger_tip_half_x == _LEGACY['FINGER_TIP_HALF_X']
        assert g.min_open == _LEGACY['GRASP_MIN_OPEN']
        assert g.pregrasp_open == _LEGACY['GRASP_PREGRASP_OPEN']
        assert g.aperture_step == _LEGACY['APERTURE_STEP']

    def test_workspace(self, fr3):
        w = fr3.workspace
        assert w.reach_y_max == _LEGACY['REACH_Y_MAX']
        assert w.reach_x_far == _LEGACY['REACH_X_FAR']
        assert w.approach_height == _LEGACY['APPROACH_HEIGHT']
        assert w.tilt_min_center_z == _LEGACY['TILT_MIN_CENTER_Z']
        assert w.tilt_candidates_deg == _LEGACY['TILT_CANDIDATES_DEG']
        assert list(w.planner_fallback) == _LEGACY['PLANNER_FALLBACK']

    def test_franka_hand_is_identity_transform(self, fr3):
        """프랑카 핸드는 관절값이 곧 반개구 — 변환이 값을 바꾸면 안 된다.

        이게 깨지면 파지 판정 경계(GRASP_DETECT_MIN/MAX)가 통째로 어긋난다.
        """
        for v in (0.0, 0.0015, 0.003, 0.0035, 0.04):
            assert fr3.gripper.halfwidth_of(v) == v
            assert fr3.gripper.full_width_of(v) == 2.0 * v

    def test_status_is_verified(self, fr3):
        """기준 모델은 검증됨이어야 전환이 허용된다."""
        assert fr3.is_verified


# =====================================================================
# 1b. UR5e + Robotiq Hand-E — 신규 기본 모델
# =====================================================================
# FR3 쪽처럼 '옛 상수와 같은가'를 볼 대상이 없다(새 모델이라 비교 원본이 없다).
# 그래서 여기서는 **값이 그렇게 나온 이유**를 지킨다:
#   - 손끝 기하는 벤더 콜리전 메시에서 유도했으므로, 메시와 다시 대조한다.
#   - 팔 섹션은 그리퍼와 무관하므로 ur5e_robotiq85 와 한 글자도 달라선 안 된다.
#   - 적응형 하강이 살아 있는가는 이 저장소가 두 번 데인 지점이라 수식으로 고정한다.
_HANDE = 'ur5e_robotiq_hande'

# 이 저장소 소스트리 기준 경로들(설치본이 아니라 소스에서 돈다).
_REPO_SRC = os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__))))                      # …/src
_HANDE_MESH = os.path.join(_REPO_SRC, 'robotiq_hande_description',
                           'meshes', 'finger_collision.dae')
_HANDE_URDF = os.path.join(_REPO_SRC, 'bin_picking', 'urdf',
                           'ur5e_robotiq_hande_gazebo.urdf.xacro')

# config.py 에서 손으로 옮겨 적은 작업(task) 상수 — 프로파일에서 유도하지 말 것.
_TASK = {
    'BIN_FLOOR_TOP': 0.005,        # 통 바닥 충돌박스 상면
    'BOLT_SHAFT_RADIUS': 0.004,    # M8 샤프트 반경
    'BOLT_REST_CENTER_Z': 0.009,   # = BIN_FLOOR_TOP + BOLT_SHAFT_RADIUS
    'GRASP_DETECT_MAX': 0.009,
}


def _finger_pad_box():
    """벤더 콜리전 메시에서 '파지 패드' 박스의 (x, y, z) 범위를 뽑는다.

    finger_collision.dae 는 정점 16개 = 박스 두 개(파지 패드 + 캐리지)이고,
    asset 이 unit meter=1.0 / Z_UP 이며 visual_scene 에 노드 변환이 없다 →
    <float_array> 정점이 곧 손가락 링크 좌표(m)다. 패드는 손끝(z 최대) 쪽 박스.
    """
    import xml.etree.ElementTree as ET

    ns = {'c': 'http://www.collada.org/2005/11/COLLADASchema'}
    root = ET.parse(_HANDE_MESH).getroot()
    asset = root.find('c:asset', ns)
    assert float(asset.find('c:unit', ns).get('meter')) == 1.0
    assert asset.find('c:up_axis', ns).text.strip() == 'Z_UP'

    boxes = []
    for geom in root.iter('{%s}geometry' % ns['c']):
        mesh = geom.find('c:mesh', ns)
        src_id = next(i.get('source').lstrip('#')
                      for i in mesh.find('c:vertices', ns).findall('c:input', ns)
                      if i.get('semantic') == 'POSITION')
        vals = [float(v) for v in mesh.find(
            "c:source[@id='%s']" % src_id, ns).find('c:float_array', ns).text.split()]
        pts = list(zip(vals[0::3], vals[1::3], vals[2::3]))
        boxes.append(((min(p[0] for p in pts), max(p[0] for p in pts)),
                      (min(p[1] for p in pts), max(p[1] for p in pts)),
                      (min(p[2] for p in pts), max(p[2] for p in pts))))
    return max(boxes, key=lambda b: b[2][1])


@pytest.fixture(scope='module')
def hande():
    return registry.get(_HANDE)


class TestUr5eHandeProfile:
    """신규 기본 모델 — 등록되어 있고, 값의 유도 근거가 살아 있는가."""

    def test_is_the_default_model(self, hande):
        assert registry.DEFAULT_MODEL == _HANDE
        assert hande.name == _HANDE

    def test_status_is_draft_until_gazebo_verified(self, hande):
        """실물/실측 전이므로 draft 다 — 명시 전환은 계속 거부돼야 한다."""
        assert not hande.is_verified
        assert hande.task_validated is False

    def test_arm_section_is_identical_to_2f85(self, hande):
        """팔은 그리퍼와 무관하다 — 두 UR5e 프로파일이 어긋나면 둘 중 하나가 틀렸다."""
        assert hande.arm.to_dict() == registry.get('ur5e_robotiq85').arm.to_dict()

    def test_gripper_identifiers(self, hande):
        g = hande.gripper
        assert g.kind == 'linear'          # 평행 슬라이더 — 2F-85 의 angular 와 다르다
        assert g.command_joint == 'robotiq_hande_left_finger_joint'
        assert g.action_type == 'GripperCommand'
        assert g.action_name == '/robotiq_hande_controller/gripper_cmd'
        assert g.controller == 'robotiq_hande_controller'
        # 종동 관절은 gz 가 처리하므로 발행되지 않는다 → 넣지 않는다.
        assert list(g.state_joints) == ['robotiq_hande_left_finger_joint']

    def test_joint_value_is_the_halfwidth(self, hande):
        """관절값 = 반개구. 패드 안쪽면이 손가락 링크 x=0 에 있어서 성립한다.

        이게 깨지면 파지 판정 경계(GRASP_DETECT_MIN/MAX)가 통째로 어긋난다.
        """
        for v in (0.0, 0.001, 0.004, 0.010, 0.025):
            assert hande.gripper.halfwidth_of(v) == v
            assert hande.gripper.full_width_of(v) == 2.0 * v
        # 만개 총 개구 = 50mm (Robotiq Hand-E 카탈로그)
        assert hande.gripper.full_width_of(hande.gripper.open_cmd) == pytest.approx(0.050)

    def test_open_closed_direction(self, hande):
        """FR3 규약(값이 커질수록 열림). 2F-85 는 정반대라 여기서 갈린다."""
        g = hande.gripper
        assert g.halfwidth_of(g.open_cmd) > g.halfwidth_of(g.closed_cmd)
        assert g.command_range() == (g.closed_cmd, g.open_cmd)

    def test_closing_axis_needs_quarter_turn(self, hande):
        """grasp_tcp 는 닫힘축이 x 다 → y_tool 로 보내려면 z 둘레 +90°."""
        import math
        roll, pitch, yaw = hande.gripper.tool_frame_rpy
        assert (roll, pitch) == (0.0, 0.0)
        assert yaw == pytest.approx(math.pi / 2, abs=1e-4)

    def test_grasp_detection_separates_empty_close_from_bolt(self, hande):
        """허공 닫힘과 M8 파지가 판정 경계의 서로 다른 쪽에 있는가.

        경계 = (허공 닫힘 개구 + 샤프트 반경)/2 — config.apply_profile 과 같은 식.
        """
        g = hande.gripper
        empty = g.halfwidth_of(g.closed_cmd)
        bolt = _TASK['BOLT_SHAFT_RADIUS']
        boundary = (empty + bolt) / 2.0
        assert empty < boundary < bolt <= _TASK['GRASP_DETECT_MAX']

    def test_adaptive_descent_loop_actually_runs(self, hande):
        """바닥 볼트에서 적응형 하강이 0회 돌지 않는가.

        이 저장소가 두 번 데인 지점이다(2F-85 는 손끝 28.5mm 때문에 루프가 통째로
        죽었다). Hand-E 는 FR3 보다 손끝이 1mm 길 뿐인데 그 1mm 로 grasp_z 가
        z_cap 을 넘어선다 → floor_raise 가 반드시 0 보다 커야 한다.
        수식은 pick_place_node 의 z_cap 계산을 그대로 옮긴 것이다.
        """
        gr, gg = hande.grasp, hande.gripper
        grasp_z = (_TASK['BIN_FLOOR_TOP'] + gg.tcp_to_fingertip + gr.floor_clear)
        z_cap = _TASK['BOLT_REST_CENTER_Z'] + gr.max_above
        if gr.floor_raise > 0.0:
            z_cap = max(z_cap, grasp_z + gr.floor_raise)
        assert grasp_z <= z_cap + 1e-9, '적응형 하강 루프가 0회 돈다'

        # 상향 재시도의 상한에서도 손끝이 샤프트 몸통 안에 남아야 한다
        # (2F-85 라이브 실측 기준: 손끝 0.0115 까지는 물고, 샤프트 상단에서는 헛잡음).
        shaft_top = _TASK['BOLT_REST_CENTER_Z'] + _TASK['BOLT_SHAFT_RADIUS']
        assert z_cap - gg.tcp_to_fingertip < shaft_top

    def test_drop_z_clears_the_bin_wall(self, hande):
        """놓는 순간 손끝이 통 벽 상단(0.025)을 넘는가.

        안 넘으면 놓은 직후 자세가 start-in-collision 이 되어 이후 계획이 전부
        거부되고 episode 가 멈춘다(2F-85 에서 실측 확인된 실패 모드).
        """
        fingertip = hande.workspace.drop_z - hande.gripper.tcp_to_fingertip
        assert fingertip > 0.025

    def test_geometry_matches_vendor_collision_mesh(self, hande):
        """손끝 기하 3값이 벤더 메시와 여전히 일치하는가.

        yaml 주석의 유도를 기계로 다시 밟는다 — 메시가 바뀌거나 누가 값을 '보기
        좋게' 반올림하면 여기서 걸린다.
        """
        if not os.path.exists(_HANDE_MESH):
            pytest.skip(f'벤더 메시가 없다: {_HANDE_MESH}')
        (x_lo, x_hi), (y_lo, y_hi), (z_lo, z_hi) = _finger_pad_box()
        g = hande.gripper

        # 패드 안쪽면이 x=0 이어야 '관절값 = 반개구'가 성립한다.
        assert x_lo == pytest.approx(0.0, abs=1e-6)
        # TCP(패드 중앙) → 손끝(패드 끝)
        assert g.tcp_to_fingertip == pytest.approx(z_hi - (z_lo + z_hi) / 2.0,
                                                   abs=5e-5)
        # 닫힘축 반폭 = 패드 두께의 절반
        assert g.finger_half_w == pytest.approx((x_hi - x_lo) / 2.0, abs=5e-5)
        # 볼트축 반폭 = 원점에서 먼 쪽 y (보수적)
        assert g.finger_tip_half_x == pytest.approx(max(abs(y_lo), abs(y_hi)),
                                                    abs=5e-5)

    def test_grasp_tcp_offset_in_urdf_matches_the_profile(self, hande):
        """결합 xacro 의 grasp_tcp_z 가 메시에서 유도한 패드 중앙과 같은가.

        yaml(손끝 오프셋)과 urdf(TCP 위치)는 같은 메시에서 나왔지만 서로 다른
        파일에 산다 — 한쪽만 고치면 파지 깊이가 통째로 어긋난 채 조용히 돈다.
        """
        import re

        if not (os.path.exists(_HANDE_MESH) and os.path.exists(_HANDE_URDF)):
            pytest.skip('소스트리에서만 도는 검사다')
        text = open(_HANDE_URDF, encoding='utf-8').read()
        m = re.search(r'name="grasp_tcp_z"\s+default="([0-9.]+)"', text)
        assert m, 'grasp_tcp_z 인자를 결합 xacro 에서 찾지 못했다'
        grasp_tcp_z = float(m.group(1))

        # 손가락 관절 원점(robotiq_hande_link 기준 z=0.099, 벤더 xacro hande_height)
        _, _, (z_lo, z_hi) = _finger_pad_box()
        assert grasp_tcp_z == pytest.approx(0.099 + (z_lo + z_hi) / 2.0, abs=5e-5)
        # 그리고 손끝은 TCP 보다 정확히 tcp_to_fingertip 만큼 아래다.
        assert (0.099 + z_hi) - grasp_tcp_z == pytest.approx(
            hande.gripper.tcp_to_fingertip, abs=5e-5)


# =====================================================================
# 2. 스키마 — 빠지거나 모순된 입력을 등록 시점에 막는가
# =====================================================================
def _minimal_dict():
    """스키마를 만족하는 최소 프로파일(테스트용 합성 모델).

    실제 등록 가능한 모델이 아니라, 스키마 검사를 흔들어 보기 위한 골격이다.
    """
    return {
        'name': 'testarm',
        'status': 'draft',
        'arm': {
            'planning_group': 'test_arm',
            'base_frame': 'base_link',
            'tcp_frame': 'tool_tcp',
            'controller': 'arm_ctrl',
            'joints': ['j1', 'j2'],
            'joint_limits': {'j1': [-1.0, 1.0], 'j2': [-2.0, 2.0]},
            'limit_margin': 0.1,
        },
        'gripper': {
            'kind': 'linear',
            'command_joint': 'g1',
            'state_joints': ['g1', 'g2'],
            'action_type': 'FollowJointTrajectory',
            'action_name': '/grip/follow_joint_trajectory',
            'controller': 'grip_ctrl',
            'open_cmd': 0.04,
            'closed_cmd': 0.001,
            'halfwidth_scale': 1.0,
            'halfwidth_offset': 0.0,
            'touch_links': ['hand'],
            'geometry': {'tcp_to_fingertip': 0.01,
                         'finger_half_w': 0.004,
                         'finger_tip_half_x': 0.01},
            'aperture': {'min_open': 0.008, 'pregrasp_open': 0.01,
                         'step': 0.004},
        },
        'workspace': {
            'reach_y_max': 0.06, 'reach_x_far': 0.4,
            'approach_height': 0.25, 'tilt_min_center_z': 0.02,
            'tilt_candidates_deg': [15.0],
            'planner_fallback': ['RRTConnectkConfigDefault'],
        },
        'description': {
            'urdf': {'package': 'p', 'path': 'urdf/a.xacro'},
            'srdf': {'package': 'p', 'path': 'srdf/a.xacro'},
            'moveit': {'package': 'p', 'files': {
                'kinematics': 'c/k.yaml', 'joint_limits': 'c/jl.yaml',
                'ompl': 'c/o.yaml', 'controllers': 'c/ctl.yaml',
                'rviz': 'r/m.rviz'}},
            'gazebo': {'entity': 'testarm'},
        },
    }


def test_minimal_profile_parses():
    p = RobotProfile.from_dict(_minimal_dict())
    assert p.name == 'testarm'
    assert not p.is_verified          # status: draft


@pytest.mark.parametrize('mutate,expect', [
    # 관절 한계가 빠지면 실패 진단이 조용히 죽는다
    (lambda d: d['arm']['joint_limits'].pop('j2'), 'joint_limits'),
    # joints 에 없는 관절의 한계 = 오타 신호
    (lambda d: d['arm']['joint_limits'].update({'j9': [-1.0, 1.0]}),
     'joint_limits'),
    # 명령 관절이 상태 관절에 없으면 파지 판정이 값을 못 읽는다
    (lambda d: d['gripper'].update({'state_joints': ['g2']}), 'state_joints'),
    # 하한 >= 상한
    (lambda d: d['arm']['joint_limits'].update({'j1': [1.0, -1.0]}), 'joint_limits'),
    # 닫힘 >= 열림
    (lambda d: d['gripper'].update({'closed_cmd': 0.05}), 'closed_cmd'),
    # 알 수 없는 액션 타입
    (lambda d: d['gripper'].update({'action_type': 'MagicGrip'}), 'action_type'),
    # 알 수 없는 그리퍼 종류
    (lambda d: d['gripper'].update({'kind': 'vacuum'}), 'kind'),
    # MoveIt 필수 설정 누락
    (lambda d: d['description']['moveit']['files'].pop('ompl'), 'moveit.files'),
    # 알 수 없는 상태값
    (lambda d: d.update({'status': 'maybe'}), 'status'),
    # pre-grasp 이 하한보다 좁음
    (lambda d: d['gripper']['aperture'].update({'pregrasp_open': 0.001}),
     'pregrasp_open'),
])
def test_schema_rejects(mutate, expect):
    d = _minimal_dict()
    mutate(d)
    with pytest.raises(ProfileError) as exc:
        RobotProfile.from_dict(d)
    assert expect in str(exc.value), f'오류 메시지가 어느 칸인지 안 알려준다: {exc.value}'


def test_schema_error_names_the_field():
    """오류 메시지는 반드시 '고쳐야 할 칸'을 담아야 한다 — 수기 등록의 생명줄."""
    d = _minimal_dict()
    del d['gripper']['geometry']['tcp_to_fingertip']
    with pytest.raises(ProfileError) as exc:
        RobotProfile.from_dict(d)
    msg = str(exc.value)
    assert 'gripper.geometry' in msg and 'tcp_to_fingertip' in msg


def test_roundtrip_to_dict():
    """to_dict → from_dict 가 값을 보존한다(CLI 의 scaffold/show 가 의존)."""
    p = RobotProfile.from_dict(_minimal_dict())
    again = RobotProfile.from_dict(p.to_dict())
    assert again.to_dict() == p.to_dict()


# =====================================================================
# 3. 검증기 — 실제로 '틀린 값'을 잡아내는가 (음성 테스트)
# =====================================================================
_URDF = """<?xml version="1.0"?>
<robot name="t">
  <link name="base_link"/>
  <link name="l1"/>
  <link name="tool_tcp"/>
  <link name="hand"/>
  <joint name="j1" type="revolute">
    <limit lower="-1.0" upper="1.0"/>
  </joint>
  <joint name="j2" type="revolute">
    <limit lower="-2.0" upper="2.0"/>
  </joint>
  <joint name="g1" type="prismatic">
    <limit lower="0.0" upper="0.04"/>
  </joint>
  <joint name="g2" type="prismatic">
    <limit lower="0.0" upper="0.04"/>
  </joint>
</robot>
"""

_SRDF = """<?xml version="1.0"?>
<robot name="t">
  <group name="test_arm">
    <chain base_link="base_link" tip_link="tool_tcp"/>
  </group>
  <group_state name="ready" group="test_arm">
    <joint name="j1" value="0"/>
  </group_state>
</robot>
"""


def _profile(**mutations):
    d = _minimal_dict()
    for path, value in mutations.items():
        node = d
        keys = path.split('.')
        for k in keys[:-1]:
            node = node[k]
        node[keys[-1]] = value
    return RobotProfile.from_dict(d)


def test_model_validation_passes_on_matching_model():
    rep = V.validate_against_model(_profile(), urdf_xml=_URDF, srdf_xml=_SRDF)
    assert rep.ok, rep.format()
    assert rep.checked == ['urdf', 'srdf']


def test_catches_joint_name_typo():
    """가장 흔하고 가장 조용한 오류 — 관절 이름 오타."""
    p = _profile(**{'arm.joints': ['j1', 'jTWO'],
                    'arm.joint_limits': {'j1': [-1.0, 1.0],
                                         'jTWO': [-2.0, 2.0]}})
    rep = V.validate_against_model(p, urdf_xml=_URDF)
    assert not rep.ok
    assert any('jTWO' in f.message for f in rep.errors)


def test_catches_limits_wider_than_urdf():
    """프로파일 한계가 URDF 보다 넓으면 '한계 근접 경고'가 침묵한다."""
    p = _profile(**{'arm.joint_limits': {'j1': [-3.0, 3.0], 'j2': [-2.0, 2.0]}})
    rep = V.validate_against_model(p, urdf_xml=_URDF)
    assert rep.ok           # 경고지 오류는 아니다 (계획은 여전히 돈다)
    assert any('arm.joint_limits' == f.where for f in rep.warnings)


def test_catches_missing_planning_group():
    p = _profile(**{'arm.planning_group': 'no_such_group'})
    rep = V.validate_against_model(p, srdf_xml=_SRDF)
    assert not rep.ok
    assert any('planning group' in f.message for f in rep.errors)


def test_catches_missing_home_state():
    p = _profile(**{'arm.home_state': 'nap'})
    rep = V.validate_against_model(p, srdf_xml=_SRDF)
    assert not rep.ok
    assert any('nap' in f.message for f in rep.errors)


def test_catches_gripper_command_outside_urdf_limit():
    """열림 지령이 관절 상한을 넘으면 컨트롤러가 지령을 거부한다."""
    p = _profile(**{'gripper.open_cmd': 0.09})
    rep = V.validate_against_model(p, urdf_xml=_URDF)
    assert not rep.ok
    assert any(f.where == 'gripper.open_cmd' for f in rep.errors)


def test_catches_missing_touch_link():
    p = _profile(**{'gripper.touch_links': ['hand', 'ghost_link']})
    rep = V.validate_against_model(p, urdf_xml=_URDF)
    assert not rep.ok
    assert any('ghost_link' in f.message for f in rep.errors)


def test_catches_angular_gripper_with_identity_transform():
    """rad 를 m 로 착각한 등록 — 파지 판정이 통째로 무의미해지는 사고."""
    p = _profile(**{'gripper.kind': 'angular'})
    rep = V.validate_static(p)
    assert not rep.ok
    assert any(f.where == 'gripper.halfwidth_scale' for f in rep.errors)


# Robotiq 2F-85 를 본뜬 각도 구동 그리퍼: 0 rad = 만개(85mm), 0.7929 rad = 닫힘.
# **관절값이 커질수록 닫힌다** — 프랑카와 정반대다.
_ROBOTIQ_LIKE = {
    'gripper.kind': 'angular',
    'gripper.open_cmd': 0.0,
    'gripper.closed_cmd': 0.7929,
    'gripper.halfwidth_scale': -0.0536,   # 기울기가 음수
    'gripper.halfwidth_offset': 0.0425,   # 0 rad 에서 42.5mm (총 85mm)
}


def test_angular_gripper_with_real_transform_passes():
    p = _profile(**_ROBOTIQ_LIKE)
    rep = V.validate_static(p)
    assert rep.ok, rep.format()


def test_inverted_gripper_is_registrable():
    """관절값이 커질수록 닫히는 그리퍼도 등록돼야 한다.

    예전 스키마는 closed_cmd < open_cmd 와 halfwidth_scale > 0 을 강제해서
    Robotiq 2F 계열을 통째로 거부했다 — 프랑카의 관습을 불변식으로 착각한 것.
    """
    p = _profile(**_ROBOTIQ_LIKE)
    g = p.gripper
    # 관절값으로는 '열림'이 '닫힘'보다 작다 — 프랑카와 반대이고, 그래도 등록된다
    assert g.open_cmd < g.closed_cmd
    # 진짜 불변식은 물리 개구 공간에서 성립한다
    assert g.halfwidth_of(g.open_cmd) > g.halfwidth_of(g.closed_cmd)
    assert g.halfwidth_of(0.0) == pytest.approx(0.0425)
    assert g.halfwidth_of(0.7929) == pytest.approx(0.0, abs=1e-4)


def test_command_range_is_direction_agnostic():
    """클램프 범위는 어느 쪽이 큰지와 무관하게 [min, max] 여야 한다."""
    assert _profile(**_ROBOTIQ_LIKE).gripper.command_range() == (0.0, 0.7929)
    assert _profile().gripper.command_range() == (0.001, 0.04)


def test_schema_rejects_flipped_direction():
    """변환 부호를 잘못 넣으면 '열림이 닫힘보다 좁다'가 되어 거부된다."""
    d = _minimal_dict()
    d['gripper'].update({'kind': 'angular', 'open_cmd': 0.0,
                         'closed_cmd': 0.7929,
                         'halfwidth_scale': 0.0536,      # 부호가 반대!
                         'halfwidth_offset': 0.0})
    with pytest.raises(ProfileError) as exc:
        RobotProfile.from_dict(d)
    assert '부호' in str(exc.value)


def test_halfwidth_curve_interpolates():
    """비선형 각도↔개구는 실측 대응표로 준다."""
    d = _minimal_dict()
    d['gripper'].update({
        'kind': 'angular', 'open_cmd': 0.0, 'closed_cmd': 0.8,
        'halfwidth_curve': [[0.0, 0.0425], [0.4, 0.0240], [0.8, 0.0]],
    })
    g = RobotProfile.from_dict(d).gripper
    assert g.halfwidth_of(0.0) == pytest.approx(0.0425)
    assert g.halfwidth_of(0.4) == pytest.approx(0.0240)
    assert g.halfwidth_of(0.8) == pytest.approx(0.0)
    # 구간 안은 선형 보간
    assert g.halfwidth_of(0.2) == pytest.approx((0.0425 + 0.0240) / 2)
    # 범위를 살짝 벗어난 실측값도 뭉개지지 않고 외삽된다
    assert g.halfwidth_of(0.9) < 0.0


def test_curve_beats_linear_and_needs_two_points():
    d = _minimal_dict()
    d['gripper']['halfwidth_curve'] = [[0.0, 0.0425]]
    with pytest.raises(ProfileError) as exc:
        RobotProfile.from_dict(d)
    assert 'halfwidth_curve' in str(exc.value)


def test_curve_rejects_duplicate_joint_value():
    d = _minimal_dict()
    d['gripper']['halfwidth_curve'] = [[0.0, 0.04], [0.0, 0.01], [0.8, 0.0]]
    with pytest.raises(ProfileError) as exc:
        RobotProfile.from_dict(d)
    assert '중복' in str(exc.value)


def test_angular_without_curve_warns_but_passes():
    """선형 근사는 막지 않되, 비선형 위험을 알려야 한다."""
    rep = V.validate_static(_profile(**_ROBOTIQ_LIKE))
    assert rep.ok
    assert any(f.where == 'gripper.halfwidth_curve' for f in rep.warnings)


def test_tool_frame_rpy_defaults_to_identity():
    assert _profile().gripper.tool_frame_rpy == (0.0, 0.0, 0.0)


def test_tool_frame_rpy_parsed():
    d = _minimal_dict()
    d['gripper']['tool_frame_rpy'] = [0.0, 0.0, 1.5708]
    assert RobotProfile.from_dict(d).gripper.tool_frame_rpy[2] == pytest.approx(1.5708)


def test_tool_frame_rpy_rejects_wrong_length():
    d = _minimal_dict()
    d['gripper']['tool_frame_rpy'] = [0.0, 0.0]
    with pytest.raises(ProfileError) as exc:
        RobotProfile.from_dict(d)
    assert 'tool_frame_rpy' in str(exc.value)


def test_catches_closed_cmd_wider_than_min_open():
    p = _profile(**{'gripper.closed_cmd': 0.009,
                    'gripper.aperture': {'min_open': 0.008,
                                         'pregrasp_open': 0.01,
                                         'step': 0.004}})
    rep = V.validate_static(p)
    assert not rep.ok
    assert any('min_open' in f.where for f in rep.errors)


def test_catches_zero_reach_filter():
    """reach_y_max=0 이면 모든 볼트가 걸러져 아무것도 못 집는다."""
    p = _profile(**{'workspace.reach_y_max': 0.0})
    rep = V.validate_static(p)
    assert not rep.ok
    assert any(f.where == 'workspace.reach_y_max' for f in rep.errors)


def test_catches_missing_package_file():
    p = _profile()
    rep = V.validate_static(
        p, package_share=lambda pkg: '/nonexistent/' + pkg,
        path_exists=lambda path: False)
    assert not rep.ok
    assert any(f.where.startswith('description.') for f in rep.errors)


def test_runtime_validation_catches_missing_joint_state():
    p = _profile()
    rep = V.validate_against_runtime(p, joint_state_names=['j1', 'j2', 'g2'])
    assert not rep.ok
    assert any(f.where == 'gripper.command_joint' for f in rep.errors)


def test_runtime_validation_catches_missing_action_server():
    p = _profile()
    rep = V.validate_against_runtime(p, action_names=['/other/action'])
    assert not rep.ok
    assert any(f.where == 'gripper.action_name' for f in rep.errors)


def test_runtime_action_name_slash_insensitive():
    """액션 이름 앞의 '/' 유무는 환경마다 다르다 — 그걸로 오탐하면 안 된다."""
    p = _profile()
    rep = V.validate_against_runtime(
        p, action_names=['grip/follow_joint_trajectory'])
    assert rep.ok, rep.format()


def test_runtime_validation_catches_missing_controller():
    p = _profile()
    rep = V.validate_against_runtime(p, controller_names=['joint_state_broadcaster'])
    assert not rep.ok
    assert {f.where for f in rep.errors} == {'arm.controller', 'gripper.controller'}


def test_skipped_checks_are_not_reported_as_passed():
    """인자를 안 주면 그 검사는 'checked' 에 안 들어간다 — 침묵 통과 방지."""
    rep = V.validate_against_runtime(_profile())
    assert rep.checked == []
    assert rep.ok      # 지적사항은 없지만, 아무것도 확인하지 않았다


# =====================================================================
# 4. 레지스트리 — 탐색·우선순위·활성 모델
# =====================================================================
def test_builtin_fr3_is_discovered():
    assert 'fr3' in registry.names()


def test_no_broken_builtin_profiles():
    """내장 프로파일이 깨져 있으면 즉시 드러나야 한다."""
    assert registry.discover_errors() == []


def test_unknown_model_error_lists_available():
    with pytest.raises(registry.ProfileNotFound) as exc:
        registry.get('definitely_not_registered')
    msg = str(exc.value)
    assert 'fr3' in msg and 'binpick_model' in msg


def test_user_dir_overrides_builtin(tmp_path, monkeypatch):
    """사용자가 자기 설치 상태에 맞게 내장값을 덮어쓰는 것이 정상 운용이다."""
    import yaml

    d = _minimal_dict()
    d['name'] = 'fr3'                       # 같은 이름으로 덮어쓰기
    d['workspace']['reach_y_max'] = 0.099   # 내 설치의 실측값
    override = tmp_path / 'fr3.yaml'
    override.write_text(yaml.safe_dump(d), encoding='utf-8')

    monkeypatch.setenv(registry.ENV_PROFILE_PATH, str(tmp_path))
    assert registry.get('fr3').workspace.reach_y_max == 0.099
    assert registry.get('fr3').source_path == str(override)

    monkeypatch.delenv(registry.ENV_PROFILE_PATH)
    assert registry.get('fr3').workspace.reach_y_max == _LEGACY['REACH_Y_MAX']


def test_broken_file_does_not_hide_the_rest(tmp_path, monkeypatch):
    (tmp_path / 'broken.yaml').write_text('name: x\narm: 3\n', encoding='utf-8')
    monkeypatch.setenv(registry.ENV_PROFILE_PATH, str(tmp_path))
    assert 'fr3' in registry.names()          # 나머지는 살아 있고
    errors = registry.discover_errors()       # 깨진 파일은 따로 보고된다
    assert any('broken.yaml' in path for path, _ in errors)


def test_env_var_wins_for_active_model(monkeypatch):
    monkeypatch.setenv(registry.ENV_MODEL, 'someothermodel')
    assert registry.active_model_name() == 'someothermodel'
    monkeypatch.delenv(registry.ENV_MODEL)


def test_default_active_model_is_ur5e_robotiq_hande(monkeypatch, tmp_path):
    """저장된 선택도 환경변수도 없으면 UR5e + Hand-E 가 기본이다.

    2026-08-31 에 fr3 → ur5e_robotiq_hande 로 옮겼다. fr3 는 등록된 채로 남는다.
    """
    monkeypatch.delenv(registry.ENV_MODEL, raising=False)
    monkeypatch.setenv('XDG_CONFIG_HOME', str(tmp_path))   # 저장된 선택 없음
    assert registry.active_model_name() == registry.DEFAULT_MODEL
    assert registry.active_profile().name == 'ur5e_robotiq_hande'
    assert 'fr3' in registry.names()


def test_set_active_refuses_unregistered(monkeypatch, tmp_path):
    monkeypatch.setenv('XDG_CONFIG_HOME', str(tmp_path))
    with pytest.raises(registry.ProfileNotFound):
        registry.set_active('nope')


def test_set_active_refuses_draft(monkeypatch, tmp_path):
    """검증 전 모델로 전환하면 실물에서 충돌·과주행로 직결된다 — 막아야 한다."""
    import yaml

    d = _minimal_dict()          # status: draft
    (tmp_path / 'draft.yaml').write_text(yaml.safe_dump(d), encoding='utf-8')
    monkeypatch.setenv(registry.ENV_PROFILE_PATH, str(tmp_path))
    monkeypatch.setenv('XDG_CONFIG_HOME', str(tmp_path / 'cfg'))

    with pytest.raises(ProfileError) as exc:
        registry.set_active('testarm')
    assert 'verify' in str(exc.value)

    # 명시적으로 허용하면 통과한다(검증 작업 자체에 필요)
    registry.set_active('testarm', allow_draft=True)
    assert registry.active_model_name() == 'testarm'


def test_task_validated_defaults_false():
    """작업 성능은 명시하지 않으면 '확인 안 됨'이다 — 낙관적 기본값 금지."""
    assert RobotProfile.from_dict(_minimal_dict()).task_validated is False


def test_task_validated_parsed():
    d = _minimal_dict()
    d['task_validated'] = True
    assert RobotProfile.from_dict(d).task_validated is True


def test_status_gate_ignores_task_validated(monkeypatch, tmp_path):
    """안전검증(status)과 작업성능(task_validated)은 별개 축이다.

    verify 를 통과했다면(=값이 실제 모델과 대조됐다면) 그 팔로 아직 작업을
    성공시켜 보지 못했더라도 전환은 허용돼야 한다. 둘을 한 축으로 묶으면
    '안전하게 로드는 되지만 이 작업엔 안 맞는 팔'을 표현할 수 없다.
    """
    import yaml

    d = _minimal_dict()
    d['status'] = 'verified'
    d['task_validated'] = False          # 작업은 아직 성공 못 시킴
    (tmp_path / 'x.yaml').write_text(yaml.safe_dump(d), encoding='utf-8')
    monkeypatch.setenv(registry.ENV_PROFILE_PATH, str(tmp_path))
    monkeypatch.setenv('XDG_CONFIG_HOME', str(tmp_path / 'cfg'))
    monkeypatch.delenv(registry.ENV_MODEL, raising=False)

    p = registry.set_active('testarm')   # 거부되면 안 된다
    assert p.name == 'testarm'
    assert p.task_validated is False


def test_fr3_is_task_validated():
    """기준 모델은 실제로 파지에 성공한 기록이 있다."""
    assert registry.get('fr3').task_validated is True


def test_set_active_roundtrip(monkeypatch, tmp_path):
    monkeypatch.delenv(registry.ENV_MODEL, raising=False)
    monkeypatch.setenv('XDG_CONFIG_HOME', str(tmp_path))
    registry.set_active('fr3')
    assert registry.active_model_name() == 'fr3'
    assert os.path.exists(registry.active_model_file())
