# -*- coding: utf-8 -*-
"""데스크톱 통신 프로토콜 변환 (순수, ROS 무의존).

`docs/desktop_protocol.md` 의 데이터 계약을 실제 코드가 정확히 따르게 만드는
변환/검증 로직만 모아 둔다. ROS 를 몰라야(import 없이 단독 테스트 가능) 하는
이유는 desktop_bridge.py 뿐 아니라 pytest 에서도 Gazebo/rclpy 없이 이 파일
하나만으로 전체 fail_reason 매핑·검증 로직을 검증할 수 있어야 하기 때문이다.
"""
import math

# v2->v3(2026-08-04): 전송 계층을 단일 WebSocket 봉투에서 REST(명령)+WebSocket(텔레메
# 트리 전용) 하이브리드로 전환 + Bearer 토큰 인증 도입. v1->v2 전례와 동일하게 아직
# 데스크톱 앱 본체가 없어(mock_desktop_client.py만 유일한 소비자) 호환 shim 없이 클린
# 브레이크한다. §2 데이터 카탈로그(필드 스펙) 자체는 안 바뀌었다 — 어느 채널로 오가는지만
# 바뀌었다(desktop_protocol.md §4).
PROTOCOL_VERSION = 3

ROBOT_PHASES = (
    'IDLE', 'HOMING', 'WAITING_TARGET', 'PLANNING', 'APPROACHING',
    'DESCENDING', 'GRASPING', 'LIFTING', 'PLACING', 'RECOVERING',
    'SAFE_STOP', 'ERROR',
)
_ROBOT_PHASES_SET = frozenset(ROBOT_PHASES)


def is_valid_phase(phase):
    return phase in _ROBOT_PHASES_SET

# ⚠ 이 표의 왼쪽 문자열 일부는 커밋 bf7aff0 에서 이름이 바뀌었다 — attempts.jsonl
# 의 과거/현재 레코드가 같은 사건에 다른 reason 을 쓴다(PROGRESS.md "reason 문자열
# 개명" 항목 참고). reason 으로 그룹핑해 분석할 때 반드시 확인할 것.
# 내부 reason 문자열 -> (부록D 코드, retry_suggested)
# 로봇 파이프라인(pick_place_node.py `_pick()`)이 실제로 발행하는 문자열만 왼쪽에
# 둔다. 오른쪽 부록D 코드 중 REACH_FILTERED/COLLISION_ABORT/JOINT_LIMIT/TIMEOUT
# 은 이 표에 등장하지 않는다 — 이 파이프라인은 아직 그 실패를 구분해 내지 않는다
# (비전/필터 단이 나중에 이 코드들을 채울 수 있어 부록D 에서는 "예약"으로 유지).
FAIL_REASON_MAP = {
    # bolt axis 가 거의 수직 — 옆에서 감쌀 수 없어 영구 포기(블랙리스트)
    'axis_unreachable': ('UNREACHABLE', False),
    # 시도할 새 접근 자세가 안 남아 즉시 포기(블랙리스트)
    'no_aperture_exhausted': ('APERTURE_BLOCKED', False),
    # 개구 확보 실패, 이번 무더기에서만 보류(deferred) — 이웃이 빠지면 재시도 가능
    'no_aperture': ('APERTURE_BLOCKED', True),
    # 파지 자세(그리퍼 회전행렬) 생성 실패 — 방어적 분기
    'orientation_fail': ('PLAN_FAIL', False),
    'approach_fail': ('APPROACH_FAIL', True),
    'descend_fail': ('PLAN_FAIL', True),
    'lift_fail': ('PLAN_FAIL', True),
    'descend_short': ('DESCEND_SHORT', True),
    'attach_fail': ('ATTACH_FAIL', False),
    'empty_after_lift': ('GRASP_MISS', True),
    # 하강 직전 볼트가 허용치 이상 움직여 시도를 취소 — 재시도하면 새 자세로 잡힘
    'abort': ('ABORTED', True),
}


def map_fail_reason(reason):
    """내부 reason 문자열을 (부록D 고정 코드, retry_suggested) 로 변환.

    매핑에 없는 문자열은 조용히 삼키지 않는다 — `UNKNOWN` 확장 코드로 명시
    표기하고 호출자가 원하면 로그를 남길 수 있도록 매핑 실패 여부를 함께
    반환하지 않는 대신, 이 모듈을 쓰는 쪽(desktop_bridge.py)이 `UNKNOWN` 을
    보면 경고를 남기는 책임을 진다(§4 "침묵은 버그다").
    """
    return FAIL_REASON_MAP.get(reason, ('UNKNOWN', False))


# PICK_BOLT.args 필수 필드 (부록F)
_REQUIRED_PICK_BOLT_FIELDS = ('bolt_id', 'rank', 'stamp', 'frame')


def _is_finite_number(v):
    """JSON 숫자로서 실제로 쓸 수 있는 유한 실수인가.

    `isinstance(v, (int, float))` 만으로는 두 구멍이 남는다:
    ① `bool` 은 `int` 의 서브클래스라 `True` 가 숫자로 통과한다.
    ② `float('nan')`/`inf` 는 JSON 에는 없지만 `json.loads` 가 `NaN`/`Infinity`
       리터럴을 받아 준다 — 그대로 PoseStamped 로 흘러가면 하위 계획 단이 조용히
       망가진다.
    """
    if isinstance(v, bool):
        return False
    if not isinstance(v, (int, float)):
        return False
    return math.isfinite(v)


def validate_pick_bolt(args):
    """PICK_BOLT.args 가 부록F 필수 필드를 갖췄는지 검사.

    반환: 에러 메시지 리스트(비어 있으면 유효). 데스크톱 팀이 스키마를 잘못
    맞췄을 때 어떤 필드가 문제인지 바로 알 수 있도록 필드명을 명시한다.
    """
    errors = []
    for field in _REQUIRED_PICK_BOLT_FIELDS:
        if args.get(field) is None:
            errors.append(f'missing required field: {field}')

    pose = args.get('pose')
    if not isinstance(pose, dict):
        errors.append('missing required field: pose')
        return errors

    pos = pose.get('position')
    if not (isinstance(pos, list) and len(pos) == 3
            and all(_is_finite_number(v) for v in pos)):
        errors.append('missing/invalid required field: pose.position (f64[3])')

    quat = pose.get('orientation')
    if not (isinstance(quat, list) and len(quat) == 4
            and all(_is_finite_number(v) for v in quat)):
        errors.append('missing/invalid required field: pose.orientation (f64[4])')
    elif abs(sum(v * v for v in quat) - 1.0) >= 1e-3:
        # 비단위 쿼터니언은 PoseStamped 에 그대로 실려 나가 하위 계획 단에서
        # 조용히 회전을 왜곡시킨다 — 여기서 거부해 원인을 드러낸다.
        errors.append('pose.orientation not a unit quaternion')

    return errors


# 명령별 인자 검증 규칙(ROS 무의존, 순수). 여기 없는 명령은 추가 검증이 없다.
# 부록A 명령 표에서 인자에 제약이 있는 것만 둔다. `desktop_bridge._http_command`
# 가 이 결과를 그대로 ACK{accepted:false, errors} 로 돌려준다.
def validate_command(mtype, args):
    """ACK-only 제어 명령(`type`, `args`)의 인자 유효성 검사.

    반환: 에러 메시지 리스트(비어 있으면 유효).

    - RESET: fault/세이프스톱을 해제하는 위험 명령이라 반드시 `confirm=true` 를
      요구한다(부록A). 이게 없으면 오조작/유실 클릭으로 안전 정지가 풀린다 —
      BP-C04a. `confirm` 은 엄격히 불리언 True 만 인정한다(문자열 "true"·1 은
      거부해 데스크톱 팀이 타입을 정확히 맞추게 한다).
    """
    args = args or {}
    errors = []
    if mtype == 'RESET':
        if args.get('confirm') is not True:
            errors.append('RESET requires confirm=true')
    return errors


def is_stale(stamp_ns, deadline_ns, now_ns):
    """PICK_BOLT.args.deadline (옵션) 이 지났으면 True.

    deadline 이 없으면(옵션 필드) stale 판정을 하지 않는다 — stamp 만으로는
    "언제까지 유효한지"를 알 수 없어 무기한 유효로 취급한다.
    """
    if deadline_ns is None:
        return False
    return now_ns > deadline_ns


def build_pick_bolt_pose(args, reference_frame, now_ns):
    """PICK_BOLT.args 를 검증하고 발행 가능한 float 좌표로 변환.

    ROS 무의존이라 rclpy.init() 없이 pytest 로 검증할 수 있다 — desktop_bridge 쪽
    `_pick_bolt_core` 는 이 함수 결과를 PoseStamped 에 담아 발행하기만 한다.

    반환: `(errors, pos, quat)`. `errors` 가 비어 있지 않으면 `pos`/`quat` 는 None.
    """
    errors = validate_pick_bolt(args)
    frame = args.get('frame')
    if frame is not None and frame != reference_frame:
        errors.append(f'frame must be {reference_frame!r}, got {frame!r}')
    if errors:
        return errors, None, None

    if is_stale(args.get('stamp'), args.get('deadline'), now_ns):
        return ['stale: deadline exceeded'], None, None

    pose = args['pose']       # validate_pick_bolt 가 이미 모양을 확인함
    # ⚠ float() 로 명시 변환 필수: JSON 은 int/float 을 구분 안 해서 값이 정확히
    # 0 이나 1 같은 정수형이면 json.loads() 가 Python int 로 파싱한다. rclpy 생성
    # 바인딩은 float64 필드에 int 가 들어오면 catch 가능한 예외가 아니라 C 단
    # assert 로 프로세스 전체를 abort 시킨다(실측: 실제로 브릿지를 통째로 죽임) —
    # validate_pick_bolt 는 int 도 유효한 숫자로 통과시키므로(부록F 는 "숫자"만
    # 요구), 이 방어는 여기서 해야 한다.
    return [], [float(v) for v in pose['position']], [float(v) for v in pose['orientation']]


def joint_margin(q_dict, limits):
    """관절해가 한계에서 얼마나 떨어졌나(전체 최솟값, rad). 클수록 안전.

    `GeometryMixin._joint_margin`(geometry.py) 과 동일 로직의 유일한 구현체 —
    그쪽은 이 함수로 위임한다(구현 중복/드리프트 방지). 내부 안전판정용
    스칼라이므로 falsy 입력 시 0.0, 한계가 없는 관절은 건너뛰는 가드를
    그대로 보존한다.
    """
    if not q_dict:
        return 0.0
    ms = []
    for j, v in q_dict.items():
        lo, hi = limits.get(j, (None, None))
        if lo is not None:
            ms.append(min(v - lo, hi - v))
    return min(ms) if ms else 0.0


def joint_margins(q_dict, limits, joint_order):
    """관절별 한계 여유 리스트(`f32[7]`) — `arm_state.joint_margin` 텔레메트리용.

    위 `joint_margin`(스칼라, 내부 안전판정용)과는 다른 함수다:
    `docs/desktop_protocol.md` 부록F 는 이 필드를 관절별 배열로 스펙해 뒀으므로
    (전체 최솟값이 아니라 "각 관절 한계까지 여유"), 텔레메트리는 이 리스트
    함수를 쓴다. 한계가 없는 관절은 `None` 자리를 채운다(그럴 일은 현재
    ARM_JOINTS 전부에 JOINT_LIMITS 항목이 있어 실제로는 발생하지 않는다).
    """
    out = []
    for j in joint_order:
        v = q_dict.get(j)
        lo, hi = limits.get(j, (None, None))
        if v is None or lo is None:
            out.append(None)
            continue
        out.append(min(v - lo, hi - v))
    return out
