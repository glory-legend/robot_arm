# -*- coding: utf-8 -*-
"""bin_picking.protocol 단위 테스트 (ROS/rclpy 무의존 — Gazebo 없이 돈다).

`docs/desktop_protocol.md` 의 데이터 계약을 실제로 지키는지 검증하는 게
목적이라, 여기서 검증하는 값들은 전부 그 문서의 표(부록D/F)에서 그대로
가져온다 — 이 테스트가 곧 "문서와 코드가 일치한다"는 증거다.
"""
import math

import pytest

from bin_picking import protocol


# 부록D 매핑표 그대로 — pick_place_node.py 가 실제로 만들어내는 11개 실패
# reason 문자열 전부를 커버한다(성공은 reason 문자열이 아니라 별도 불리언이라
# 이 표에 안 들어온다).
FAIL_REASON_CASES = [
    ('axis_unreachable', 'UNREACHABLE', False),
    ('no_aperture_exhausted', 'APERTURE_BLOCKED', False),
    ('no_aperture', 'APERTURE_BLOCKED', True),
    ('orientation_fail', 'PLAN_FAIL', False),
    ('approach_fail', 'APPROACH_FAIL', True),
    ('descend_fail', 'PLAN_FAIL', True),
    ('lift_fail', 'PLAN_FAIL', True),
    ('descend_short', 'DESCEND_SHORT', True),
    ('attach_fail', 'ATTACH_FAIL', False),
    ('empty_after_lift', 'GRASP_MISS', True),
    ('abort', 'ABORTED', True),
]


@pytest.mark.parametrize('reason,expected_code,expected_retry', FAIL_REASON_CASES)
def test_map_fail_reason_known(reason, expected_code, expected_retry):
    code, retry_suggested = protocol.map_fail_reason(reason)
    assert code == expected_code
    assert retry_suggested == expected_retry


def test_map_fail_reason_unknown_is_explicit_not_silent():
    # 매핑에 없는 문자열은 조용히 아무거나로 뭉개면 안 되고, 명시적
    # 확장 코드(UNKNOWN)로 드러나야 한다(§4 "침묵은 버그다").
    code, retry_suggested = protocol.map_fail_reason('totally_made_up_reason')
    assert code == 'UNKNOWN'
    assert retry_suggested is False


def test_validate_pick_bolt_all_required_fields_missing():
    errors = protocol.validate_pick_bolt({})
    # 부록F 필수 필드: bolt_id, rank, stamp, frame, pose.position, pose.orientation
    assert any('bolt_id' in e for e in errors)
    assert any('rank' in e for e in errors)
    assert any('stamp' in e for e in errors)
    assert any('frame' in e for e in errors)
    assert any('pose' in e for e in errors)


def test_validate_pick_bolt_valid_args_pass():
    args = {
        'bolt_id': 'b_1', 'rank': 1, 'stamp': 123456789, 'frame': 'fr3_link0',
        'pose': {'position': [0.4, 0.0, 0.2], 'orientation': [0.0, 0.707, 0.0, 0.707]},
    }
    assert protocol.validate_pick_bolt(args) == []


def test_validate_pick_bolt_wrong_shape_position():
    args = {
        'bolt_id': 'b_1', 'rank': 1, 'stamp': 1, 'frame': 'fr3_link0',
        'pose': {'position': [0.4, 0.0], 'orientation': [0.0, 0.707, 0.0, 0.707]},
    }
    errors = protocol.validate_pick_bolt(args)
    assert any('pose.position' in e for e in errors)


def test_validate_pick_bolt_nan_position_rejected():
    # json.loads 는 `NaN` 리터럴을 받아 주지만 PoseStamped 로 흘러가면 하위
    # 계획 단이 조용히 망가진다 — 여기서 걸러야 한다.
    args = {
        'bolt_id': 'b_1', 'rank': 1, 'stamp': 1, 'frame': 'fr3_link0',
        'pose': {'position': [float('nan'), 0.0, 0.2],
                 'orientation': [0.0, 0.707, 0.0, 0.707]},
    }
    errors = protocol.validate_pick_bolt(args)
    assert any('pose.position' in e for e in errors)


def test_validate_pick_bolt_infinite_orientation_rejected():
    args = {
        'bolt_id': 'b_1', 'rank': 1, 'stamp': 1, 'frame': 'fr3_link0',
        'pose': {'position': [0.4, 0.0, 0.2],
                 'orientation': [float('inf'), 0.0, 0.0, 1.0]},
    }
    errors = protocol.validate_pick_bolt(args)
    assert any('pose.orientation' in e for e in errors)


def test_validate_pick_bolt_bool_is_not_a_number():
    # bool 은 int 의 서브클래스라 isinstance(v, (int, float)) 로는 통과해 버린다.
    args = {
        'bolt_id': 'b_1', 'rank': 1, 'stamp': 1, 'frame': 'fr3_link0',
        'pose': {'position': [True, 0.0, 0.2],
                 'orientation': [0.0, 0.707, 0.0, 0.707]},
    }
    errors = protocol.validate_pick_bolt(args)
    assert any('pose.position' in e for e in errors)


def test_validate_pick_bolt_non_unit_quaternion_rejected():
    args = {
        'bolt_id': 'b_1', 'rank': 1, 'stamp': 1, 'frame': 'fr3_link0',
        'pose': {'position': [0.4, 0.0, 0.2], 'orientation': [1.0, 1.0, 0.0, 0.0]},
    }
    errors = protocol.validate_pick_bolt(args)
    assert any('unit quaternion' in e for e in errors)


@pytest.mark.parametrize('value,expected', [
    (0.5, True),
    (3, True),
    (True, False),
    (False, False),
    (float('nan'), False),
    (float('inf'), False),
    (float('-inf'), False),
    ('0.5', False),
    (None, False),
])
def test_is_finite_number(value, expected):
    assert protocol._is_finite_number(value) is expected


def _valid_pick_bolt_args(**overrides):
    args = {
        'bolt_id': 'b_1', 'rank': 1, 'stamp': 1_000, 'frame': 'fr3_link0',
        'pose': {'position': [0.4, 0.0, 0.2], 'orientation': [0.0, 0.707, 0.0, 0.707]},
    }
    args.update(overrides)
    return args


def test_build_pick_bolt_pose_valid_args():
    errors, pos, quat = protocol.build_pick_bolt_pose(
        _valid_pick_bolt_args(), 'fr3_link0', now_ns=2_000)
    assert errors == []
    assert pos == [0.4, 0.0, 0.2]
    assert quat == [0.0, 0.707, 0.0, 0.707]


def test_build_pick_bolt_pose_missing_field_returns_no_pose():
    args = _valid_pick_bolt_args()
    del args['bolt_id']
    errors, pos, quat = protocol.build_pick_bolt_pose(args, 'fr3_link0', now_ns=2_000)
    assert any('bolt_id' in e for e in errors)
    assert pos is None and quat is None


def test_build_pick_bolt_pose_frame_mismatch():
    errors, pos, _ = protocol.build_pick_bolt_pose(
        _valid_pick_bolt_args(frame='world'), 'fr3_link0', now_ns=2_000)
    assert any('frame' in e for e in errors)
    assert pos is None


def test_build_pick_bolt_pose_stale_deadline():
    errors, pos, _ = protocol.build_pick_bolt_pose(
        _valid_pick_bolt_args(deadline=1_500), 'fr3_link0', now_ns=2_000)
    assert any('stale' in e for e in errors)
    assert pos is None


def test_build_pick_bolt_pose_coerces_int_position_to_float():
    # 회귀 테스트: rclpy 생성 바인딩은 float64 필드에 int 가 들어오면 잡을 수 없는
    # C 단 assert 로 프로세스를 통째로 abort 시킨다(실측). JSON 은 0/1 을 int 로
    # 파싱하므로 여기서 반드시 float 으로 바뀌어 나와야 한다.
    args = _valid_pick_bolt_args()
    args['pose'] = {'position': [0, 0, 0], 'orientation': [0, 0, 0, 1]}
    errors, pos, quat = protocol.build_pick_bolt_pose(args, 'fr3_link0', now_ns=2_000)
    assert errors == []
    assert all(isinstance(v, float) for v in pos)
    assert all(isinstance(v, float) for v in quat)


def test_is_stale_no_deadline_never_stale():
    assert protocol.is_stale(stamp_ns=100, deadline_ns=None, now_ns=10**18) is False


def test_is_stale_past_deadline():
    assert protocol.is_stale(stamp_ns=100, deadline_ns=200, now_ns=300) is True
    assert protocol.is_stale(stamp_ns=100, deadline_ns=200, now_ns=150) is False


def test_joint_margin_scalar_matches_min_across_joints():
    limits = {'j1': (-1.0, 1.0), 'j2': (-2.0, 2.0)}
    q = {'j1': 0.9, 'j2': 0.0}       # j1 여유 0.1, j2 여유 2.0 -> 최솟값 0.1
    assert math.isclose(protocol.joint_margin(q, limits), 0.1)


def test_joint_margin_empty_input_returns_zero():
    assert protocol.joint_margin({}, {'j1': (-1.0, 1.0)}) == 0.0


def test_joint_margins_list_shape_matches_joint_order():
    limits = {'j1': (-1.0, 1.0), 'j2': (-2.0, 2.0)}
    q = {'j1': 0.9, 'j2': -1.5}
    out = protocol.joint_margins(q, limits, ['j1', 'j2', 'j3'])
    assert len(out) == 3                     # arm_state.joint_margin 은 f32[7] 고정길이
    assert math.isclose(out[0], 0.1)
    assert math.isclose(out[1], 0.5)
    assert out[2] is None                    # j3 는 q/limits 어디에도 없음


def test_joint_margins_joint_present_in_q_but_missing_limits():
    # q_dict 에는 있는데 limits 에만 없는 경우도 None 이다(q_dict 에 아예 없는
    # 경우와 구분되는 별개 분기) — 현재 동작을 못 박아 둔다. desktop_bridge 는
    # 이 None 을 보고 프레임을 통째로 거르고 JOINT_LIMITS_INCOMPLETE 로 알린다.
    limits = {'j1': (-1.0, 1.0)}
    q = {'j1': 0.9, 'j2': 0.0}
    out = protocol.joint_margins(q, limits, ['j1', 'j2'])
    assert math.isclose(out[0], 0.1)
    assert out[1] is None


def test_joint_margins_and_joint_margin_agree_on_minimum():
    # 두 함수는 같은 로직의 스칼라/리스트 버전이어야 한다(구현 중복 없이
    # protocol.py 가 유일한 소스) — 리스트의 최솟값이 스칼라와 같아야 함.
    limits = {'j1': (-2.7437, 2.7437), 'j2': (-1.7837, 1.7837),
              'j3': (-2.9007, 2.9007)}
    q = {'j1': 1.0, 'j2': -1.7, 'j3': 0.0}
    order = ['j1', 'j2', 'j3']
    scalar = protocol.joint_margin(q, limits)
    per_joint = protocol.joint_margins(q, limits, order)
    assert math.isclose(scalar, min(v for v in per_joint if v is not None))
