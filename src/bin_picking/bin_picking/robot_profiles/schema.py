# -*- coding: utf-8 -*-
"""로봇 모델 프로파일 스키마 (순수, ROS 무의존).

이 파일이 답하는 질문은 하나다 — **"팔을 갈아끼울 때 사람이 무엇을 채워 넣어야
하는가?"**

빈피킹 파이프라인은 원래 FR3 하나에 맞춰 쓰여 있었고, 업체마다 다른 값들이
`config.py` 의 클래스 상수로 굳어 있었다. 그 값들을 성격별로 갈라 여기 필드로
세운다. 규칙은 하나다:

    **로봇/그리퍼를 바꿀 때 달라지는 값만 프로파일로 옮긴다.**

그래서 볼트 치수·통 배치·블랙리스트 정책·학습기 설정처럼 '작업(task)'에 속한
상수는 여전히 `config.py` 에 남는다. 반대로 관절 이름, 관절 한계, 그리퍼 명령
인터페이스, 손끝 기하, 도달성 한계처럼 '기체(machine)'에 속한 값은 전부 이리로
온다.

⚠ 이 파일은 rclpy 를 임포트하지 않는다. `protocol.py` 와 같은 이유다 — ROS 나
  Gazebo 없이 pytest 만으로 스키마·검증 로직 전체를 돌릴 수 있어야 한다.
"""
import math


class ProfileError(ValueError):
    """프로파일이 스키마를 만족하지 않는다. 메시지에 '어느 필드가' 를 담는다."""


# 그리퍼 명령 단위. 등록자가 반드시 의식적으로 골라야 하는 값이라 기본값을 두지
# 않는다(잘못 고르면 파지 판정이 통째로 무의미해진다).
#   linear  : 명령/실측 관절값이 '손가락 하나의 중심 이격'(m). 프랑카 핸드가 이것.
#             총 개구폭 = 2 × 관절값.
#   angular : 명령/실측 관절값이 '구동 관절 각도'(rad). Robotiq 2F 계열이 이것.
#             각도 → 개구폭 변환이 비선형이라 등록자가 실측 대응표를 넣어야 한다.
GRIPPER_KINDS = ('linear', 'angular')

# MoveIt / ros2_control 이 그리퍼에 쓰는 액션 인터페이스.
# (MoveIt 문서 "Low Level Controllers" 의 두 갈래와 같다)
GRIPPER_ACTION_TYPES = ('FollowJointTrajectory', 'GripperCommand')

# 등록 상태 — **안전 게이트**다. 작업 성능과 섞지 않는다.
#   draft    : 아직 `binpick_model verify` 를 통과하지 못함 → 전환 거부
#   verified : verify 통과. 즉 프로파일에 적힌 값이 **실제 모델/런타임과 대조**됐다
#              — 관절 이름·한계가 URDF 와 맞고, planning group 이 SRDF 에 있고,
#                그리퍼 지령이 관절 한계 안이고, 컨트롤러·액션이 실제로 뜬다.
#              → 전환 허용
#
# [왜 '파지 성공'을 기준으로 삼지 않는가]
#   전환을 막는 이유는 **틀린 값으로 로봇을 움직이면 실물에서 충돌·과주행**이기
#   때문이다. 그건 위 대조 항목들이 지키는 것이고, verify 가 검사한다.
#   반면 "이 그리퍼로 이 물체를 잘 집느냐"는 작업 적합성 문제다 — 안전과 무관하고,
#   대상이 바뀌면 답도 바뀐다. 둘을 한 축에 묶으면 '안전하게 로드는 되지만 이
#   작업엔 안 맞는 팔'을 표현할 수 없다. 그래서 아래 `task_validated` 로 분리한다.
STATUSES = ('verified', 'draft')


def _req(d, key, where):
    """필수 키를 꺼낸다. 없으면 '어디의 어느 키'인지 밝히고 실패한다."""
    if key not in d:
        raise ProfileError(f'{where}: 필수 항목 누락 — {key!r}')
    return d[key]


def _as_float(v, where):
    try:
        return float(v)
    except (TypeError, ValueError):
        raise ProfileError(f'{where}: 숫자여야 하는데 {v!r} 이 들어왔다')


def _as_str(v, where):
    if not isinstance(v, str) or not v.strip():
        raise ProfileError(f'{where}: 비어 있지 않은 문자열이어야 하는데 {v!r}')
    return v


def _as_str_tuple(v, where, min_len=1):
    if not isinstance(v, (list, tuple)) or len(v) < min_len:
        raise ProfileError(
            f'{where}: 항목 {min_len}개 이상의 목록이어야 하는데 {v!r}')
    return tuple(_as_str(x, f'{where}[{i}]') for i, x in enumerate(v))


class ArmSpec:
    """팔(매니퓰레이터) 쪽 기체 사양.

    MoveIt 이 이해하는 이름들(planning group, 프레임, 관절)과, 실패 진단에 쓰는
    관절 한계표가 여기 있다. 관절 한계는 **URDF 에서 자동으로 읽지 않고** 등록자가
    직접 적는다 — URDF 한계는 제조사 안전여유가 이미 들어간 값이라 로그 진단용
    '이 자세가 한계에 몇 rad 남았나' 판정에는 그대로 못 쓰는 경우가 많고, 무엇보다
    값이 틀리면 조용히 오진단으로 이어지기 때문이다(검증기가 URDF 와 대조한다).
    """

    __slots__ = ('planning_group', 'base_frame', 'tcp_frame', 'joints',
                 'joint_limits', 'limit_margin', 'controller', 'home_state')

    def __init__(self, planning_group, base_frame, tcp_frame, joints,
                 joint_limits, limit_margin, controller, home_state):
        self.planning_group = planning_group
        self.base_frame = base_frame
        self.tcp_frame = tcp_frame
        self.joints = joints
        self.joint_limits = joint_limits
        self.limit_margin = limit_margin
        self.controller = controller
        self.home_state = home_state

    @classmethod
    def from_dict(cls, d, where='arm'):
        if not isinstance(d, dict):
            raise ProfileError(f'{where}: 매핑이어야 한다')
        joints = _as_str_tuple(_req(d, 'joints', where), f'{where}.joints')

        raw_limits = _req(d, 'joint_limits', where)
        if not isinstance(raw_limits, dict):
            raise ProfileError(f'{where}.joint_limits: 매핑이어야 한다')
        limits = {}
        for name, pair in raw_limits.items():
            spot = f'{where}.joint_limits[{name!r}]'
            if not isinstance(pair, (list, tuple)) or len(pair) != 2:
                raise ProfileError(f'{spot}: [하한, 상한] 두 값이어야 한다')
            lo = _as_float(pair[0], f'{spot}[0]')
            hi = _as_float(pair[1], f'{spot}[1]')
            if not lo < hi:
                raise ProfileError(f'{spot}: 하한({lo}) < 상한({hi}) 이어야 한다')
            limits[name] = (lo, hi)

        # 한계표와 관절 목록이 어긋나면 '한계 근접 경고'가 조용히 사라진다.
        # 그 침묵이 실패 진단을 통째로 무력화하므로 등록 시점에 막는다.
        missing = [j for j in joints if j not in limits]
        if missing:
            raise ProfileError(
                f'{where}.joint_limits: 관절 한계가 빠진 관절 {missing} — '
                f'joints 에 적은 관절은 전부 한계를 적어야 한다')
        extra = [j for j in limits if j not in joints]
        if extra:
            raise ProfileError(
                f'{where}.joint_limits: joints 에 없는 관절의 한계 {extra} — '
                f'오타이거나 관절 목록이 불완전하다')

        return cls(
            planning_group=_as_str(_req(d, 'planning_group', where),
                                   f'{where}.planning_group'),
            base_frame=_as_str(_req(d, 'base_frame', where),
                               f'{where}.base_frame'),
            tcp_frame=_as_str(_req(d, 'tcp_frame', where), f'{where}.tcp_frame'),
            joints=joints,
            joint_limits=limits,
            limit_margin=_as_float(_req(d, 'limit_margin', where),
                                   f'{where}.limit_margin'),
            controller=_as_str(_req(d, 'controller', where),
                               f'{where}.controller'),
            home_state=_as_str(d.get('home_state', 'ready'),
                               f'{where}.home_state'),
        )

    def to_dict(self):
        return {
            'planning_group': self.planning_group,
            'base_frame': self.base_frame,
            'tcp_frame': self.tcp_frame,
            'joints': list(self.joints),
            'joint_limits': {k: list(v) for k, v in self.joint_limits.items()},
            'limit_margin': self.limit_margin,
            'controller': self.controller,
            'home_state': self.home_state,
        }


class GripperSpec:
    """그리퍼 쪽 기체 사양 — 업체 차이가 가장 크게 벌어지는 지점.

    파이프라인은 그리퍼에 대해 딱 두 가지를 요구한다:

      1. **개구를 지령할 수 있을 것** (`open_cmd` / `closed_cmd` 사이의 값)
      2. **현재 개구를 실측으로 되읽을 수 있을 것** — 파지 성공/빈손 판정이
         액션 error_code 가 아니라 실측 개구에 근거하기 때문이다
         (`FollowJointTrajectory` 의 GOAL_TOLERANCE_VIOLATED 는 '물어서 멈춤'과
         '허공에서 끝까지 닫힘' 양쪽에서 모두 나 구분에 못 쓴다).

    그래서 관절값 → 물리 개구폭 변환(`halfwidth_*`)이 필수 입력이다. 프랑카 핸드는
    관절값이 곧 반개구(m)라 scale=1·offset=0 이지만, 각도 구동 그리퍼는 등록자가
    실측 선형근사를 넣어야 한다.
    """

    __slots__ = ('kind', 'command_joint', 'state_joints', 'action_type',
                 'action_name', 'controller', 'open_cmd', 'closed_cmd',
                 'halfwidth_scale', 'halfwidth_offset', 'halfwidth_curve',
                 'touch_links', 'tool_frame_rpy',
                 'tcp_to_fingertip', 'finger_half_w', 'finger_tip_half_x',
                 'min_open', 'pregrasp_open', 'aperture_step')

    def __init__(self, **kw):
        for slot in self.__slots__:
            setattr(self, slot, kw[slot])

    @classmethod
    def from_dict(cls, d, where='gripper'):
        if not isinstance(d, dict):
            raise ProfileError(f'{where}: 매핑이어야 한다')

        kind = _as_str(_req(d, 'kind', where), f'{where}.kind')
        if kind not in GRIPPER_KINDS:
            raise ProfileError(
                f'{where}.kind: {kind!r} 은 알 수 없다 — {list(GRIPPER_KINDS)} 중 하나')

        action_type = _as_str(_req(d, 'action_type', where),
                              f'{where}.action_type')
        if action_type not in GRIPPER_ACTION_TYPES:
            raise ProfileError(
                f'{where}.action_type: {action_type!r} 은 지원하지 않는다 — '
                f'{list(GRIPPER_ACTION_TYPES)} 중 하나')

        command_joint = _as_str(_req(d, 'command_joint', where),
                                f'{where}.command_joint')
        state_joints = _as_str_tuple(_req(d, 'state_joints', where),
                                     f'{where}.state_joints')
        # 명령 관절이 상태 관절에 없으면 파지 판정이 영영 값을 못 읽는다.
        if command_joint not in state_joints:
            raise ProfileError(
                f'{where}.state_joints: command_joint({command_joint!r})가 빠졌다 — '
                f'파지 판정이 이 관절의 /joint_states 실측을 읽어야 한다')

        open_cmd = _as_float(_req(d, 'open_cmd', where), f'{where}.open_cmd')
        closed_cmd = _as_float(_req(d, 'closed_cmd', where),
                               f'{where}.closed_cmd')
        # ⚠ 여기서 closed_cmd < open_cmd 를 강제하지 **않는다.**
        #   그건 '관절값이 커질수록 벌어진다'는 프랑카 핸드의 관습일 뿐이다.
        #   Robotiq 2F-85 는 정반대다(0 rad = 만개, 0.79 rad = 닫힘).
        #   진짜 불변식은 관절값이 아니라 **물리 개구** 공간에 있다:
        #       halfwidth_of(open_cmd) > halfwidth_of(closed_cmd)
        #   이건 변환 계수가 다 파싱된 뒤에야 확인할 수 있으므로 아래에서 검사한다.

        geom = _req(d, 'geometry', where)
        if not isinstance(geom, dict):
            raise ProfileError(f'{where}.geometry: 매핑이어야 한다')
        gwhere = f'{where}.geometry'

        ap = _req(d, 'aperture', where)
        if not isinstance(ap, dict):
            raise ProfileError(f'{where}.aperture: 매핑이어야 한다')
        awhere = f'{where}.aperture'

        # ---- 관절값 → 반개구 변환: 선형(scale/offset) 또는 실측 곡선 ----
        # 각도 구동 그리퍼는 대개 각도↔개구가 **비선형**이라 한 쌍의 계수로는
        # 안 맞는다. 그런 경우 등록자가 실측 대응표를 넣을 수 있게 한다.
        curve = cls._parse_curve(d.get('halfwidth_curve'), where)
        if curve is None:
            scale = _as_float(_req(d, 'halfwidth_scale', where),
                              f'{where}.halfwidth_scale')
            offset = _as_float(_req(d, 'halfwidth_offset', where),
                               f'{where}.halfwidth_offset')
            if scale == 0.0:
                raise ProfileError(
                    f'{where}.halfwidth_scale: 0 이면 관절이 움직여도 개구가 '
                    f'변하지 않는다는 뜻이라 파지 판정이 불가능하다')
        else:
            # 곡선을 준 경우 선형 계수는 쓰이지 않는다(둘 다 있으면 곡선이 이긴다).
            scale = _as_float(d.get('halfwidth_scale', 1.0),
                              f'{where}.halfwidth_scale')
            offset = _as_float(d.get('halfwidth_offset', 0.0),
                               f'{where}.halfwidth_offset')

        # 파지 자세 생성이 기준으로 삼는 TCP 축 규약과 실제 그리퍼 TCP 의 차이.
        # 파이프라인은 z=접근방향 / y=손가락 닫힘축 프레임으로 파지 자세를 만든다.
        # TCP 링크의 축 배치가 그와 다르면 그 차이를 여기 rpy 로 적어 보정한다.
        # (프랑카 핸드는 규약이 일치해 [0,0,0].)
        rpy_raw = d.get('tool_frame_rpy', [0.0, 0.0, 0.0])
        if (not isinstance(rpy_raw, (list, tuple))) or len(rpy_raw) != 3:
            raise ProfileError(
                f'{where}.tool_frame_rpy: [roll, pitch, yaw] 세 값이어야 한다')
        tool_rpy = tuple(_as_float(v, f'{where}.tool_frame_rpy[{i}]')
                         for i, v in enumerate(rpy_raw))

        spec = cls(
            kind=kind,
            command_joint=command_joint,
            state_joints=state_joints,
            action_type=action_type,
            action_name=_as_str(_req(d, 'action_name', where),
                                f'{where}.action_name'),
            controller=_as_str(_req(d, 'controller', where),
                               f'{where}.controller'),
            open_cmd=open_cmd,
            closed_cmd=closed_cmd,
            halfwidth_scale=scale,
            halfwidth_offset=offset,
            halfwidth_curve=curve,
            tool_frame_rpy=tool_rpy,
            touch_links=_as_str_tuple(_req(d, 'touch_links', where),
                                      f'{where}.touch_links'),
            tcp_to_fingertip=_as_float(_req(geom, 'tcp_to_fingertip', gwhere),
                                       f'{gwhere}.tcp_to_fingertip'),
            finger_half_w=_as_float(_req(geom, 'finger_half_w', gwhere),
                                    f'{gwhere}.finger_half_w'),
            finger_tip_half_x=_as_float(_req(geom, 'finger_tip_half_x', gwhere),
                                        f'{gwhere}.finger_tip_half_x'),
            min_open=_as_float(_req(ap, 'min_open', awhere), f'{awhere}.min_open'),
            pregrasp_open=_as_float(_req(ap, 'pregrasp_open', awhere),
                                    f'{awhere}.pregrasp_open'),
            aperture_step=_as_float(_req(ap, 'step', awhere), f'{awhere}.step'),
        )

        # ---- 진짜 불변식: '열림 지령'이 '닫힘 지령'보다 물리적으로 더 벌어진다 ----
        # 관절값의 대소가 아니라 변환을 거친 개구의 대소를 본다. 이래야 관절값이
        # 커질수록 닫히는 그리퍼(Robotiq 2F 계열)도 그대로 등록된다.
        hw_open = spec.halfwidth_of(spec.open_cmd)
        hw_closed = spec.halfwidth_of(spec.closed_cmd)
        if not hw_open > hw_closed:
            raise ProfileError(
                f'{where}: open_cmd({spec.open_cmd})의 개구 {hw_open:.4f}m 가 '
                f'closed_cmd({spec.closed_cmd})의 개구 {hw_closed:.4f}m 보다 '
                f'크지 않다 — 변환(halfwidth_scale/offset 또는 halfwidth_curve)의 '
                f'부호나 두 지령값이 뒤바뀐 것 같다')
        # pre-grasp 개구가 하한보다 좁으면 파지 전에 이미 대상을 밀어낸다.
        if spec.pregrasp_open < spec.min_open:
            raise ProfileError(
                f'{awhere}: pregrasp_open({spec.pregrasp_open}) 이 '
                f'min_open({spec.min_open}) 보다 좁다')
        return spec

    @staticmethod
    def _parse_curve(raw, where):
        """[[관절값, 반개구], ...] 실측 대응표 → 정렬된 튜플. 없으면 None.

        각도 구동 그리퍼의 각도↔개구는 링크 기하 때문에 비선형이다. 등록자가
        몇 지점을 실측해 넣으면 구간선형으로 보간한다.
        """
        if raw is None:
            return None
        if not isinstance(raw, (list, tuple)) or len(raw) < 2:
            raise ProfileError(
                f'{where}.halfwidth_curve: [관절값, 반개구] 쌍이 2개 이상이어야 한다')
        pts = []
        for i, pair in enumerate(raw):
            spot = f'{where}.halfwidth_curve[{i}]'
            if not isinstance(pair, (list, tuple)) or len(pair) != 2:
                raise ProfileError(f'{spot}: [관절값, 반개구] 두 값이어야 한다')
            pts.append((_as_float(pair[0], f'{spot}[0]'),
                        _as_float(pair[1], f'{spot}[1]')))
        pts.sort(key=lambda p: p[0])
        for a, b in zip(pts, pts[1:]):
            if a[0] == b[0]:
                raise ProfileError(
                    f'{where}.halfwidth_curve: 관절값 {a[0]} 이 중복된다 — '
                    f'같은 관절값에 서로 다른 개구를 줄 수 없다')
        return tuple(pts)

    # ---- 관절값 ↔ 물리 개구 ----
    def halfwidth_of(self, joint_value):
        """구동 관절 실측값 → 손가락 하나의 중심 이격(m).

        변환은 두 가지 중 하나다:
          - `halfwidth_curve` 실측 대응표가 있으면 구간선형 보간(범위 밖은 양 끝
            구간의 기울기로 외삽 — 지령 한계를 살짝 넘은 실측값에서 값이 뭉개지지
            않게).
          - 없으면 선형 `joint * scale + offset`.

        기울기 부호는 **자유롭다.** 관절값이 커질수록 닫히는 그리퍼(Robotiq 2F
        계열)는 음수 기울기를 쓴다. 프랑카 핸드는 항등(scale=1, offset=0)이라
        이 함수가 값을 그대로 돌려준다 — 기존 수치가 완전히 보존된다는 뜻이다.
        """
        if joint_value is None:
            return None
        v = float(joint_value)
        if self.halfwidth_curve is None:
            return v * self.halfwidth_scale + self.halfwidth_offset
        return self._interp(self.halfwidth_curve, v)

    @staticmethod
    def _interp(pts, v):
        """정렬된 (x, y) 점들에 대한 구간선형 보간 + 양 끝 외삽."""
        if v <= pts[0][0]:
            (x0, y0), (x1, y1) = pts[0], pts[1]
        elif v >= pts[-1][0]:
            (x0, y0), (x1, y1) = pts[-2], pts[-1]
        else:
            for (x0, y0), (x1, y1) in zip(pts, pts[1:]):
                if x0 <= v <= x1:
                    break
        return y0 + (y1 - y0) * (v - x0) / (x1 - x0)

    def command_range(self):
        """지령값이 머물러야 하는 [최소, 최대] 관절값.

        `move_gripper` 의 클램프가 쓴다. open/closed 중 어느 쪽이 큰지 모르므로
        (그리퍼마다 다르다) 두 값에서 직접 구한다 — 예전엔 `min(GRIPPER_OPEN, x)`
        로 '열림이 더 크다'를 가정해, 방향이 반대인 그리퍼에서 모든 지령이
        닫힘값으로 뭉개졌다.
        """
        return (min(self.open_cmd, self.closed_cmd),
                max(self.open_cmd, self.closed_cmd))

    def full_width_of(self, joint_value):
        """구동 관절 실측값 → 손가락 사이 총 개구폭(m). 텔레메트리 표시용."""
        hw = self.halfwidth_of(joint_value)
        return None if hw is None else 2.0 * hw

    def to_dict(self):
        return {
            'kind': self.kind,
            'command_joint': self.command_joint,
            'state_joints': list(self.state_joints),
            'action_type': self.action_type,
            'action_name': self.action_name,
            'controller': self.controller,
            'open_cmd': self.open_cmd,
            'closed_cmd': self.closed_cmd,
            'halfwidth_scale': self.halfwidth_scale,
            'halfwidth_offset': self.halfwidth_offset,
            'halfwidth_curve': ([list(p) for p in self.halfwidth_curve]
                                if self.halfwidth_curve else None),
            'tool_frame_rpy': list(self.tool_frame_rpy),
            'touch_links': list(self.touch_links),
            'geometry': {
                'tcp_to_fingertip': self.tcp_to_fingertip,
                'finger_half_w': self.finger_half_w,
                'finger_tip_half_x': self.finger_tip_half_x,
            },
            'aperture': {
                'min_open': self.min_open,
                'pregrasp_open': self.pregrasp_open,
                'step': self.aperture_step,
            },
        }


class WorkspaceSpec:
    """이 팔이 '실제로 닿는' 범위 — 전부 실측에서 나온 값이다.

    ⚠ 여기 값들은 카탈로그 스펙(도달반경 855mm 따위)에서 베껴 오면 안 된다.
      통 위치·설치 높이·그리퍼 길이가 모두 섞인 **이 설치 상태에서의** 한계이고,
      파이프라인은 이 값으로 '어떤 접근으로도 못 잡는 볼트'를 후보 열거 전에
      걸러낸다. 값이 낙관적이면 볼트당 수십 초를 낭비하고, 비관적이면 잡을 수
      있는 볼트를 통째로 버린다.
    """

    __slots__ = ('reach_y_max', 'reach_x_far', 'approach_height',
                 'tilt_min_center_z', 'tilt_candidates_deg', 'planner_fallback',
                 'drop_z')

    def __init__(self, **kw):
        for slot in self.__slots__:
            setattr(self, slot, kw[slot])

    @classmethod
    def from_dict(cls, d, where='workspace'):
        if not isinstance(d, dict):
            raise ProfileError(f'{where}: 매핑이어야 한다')
        tilts = _req(d, 'tilt_candidates_deg', where)
        if not isinstance(tilts, (list, tuple)):
            raise ProfileError(f'{where}.tilt_candidates_deg: 목록이어야 한다')
        return cls(
            reach_y_max=_as_float(_req(d, 'reach_y_max', where),
                                  f'{where}.reach_y_max'),
            reach_x_far=_as_float(_req(d, 'reach_x_far', where),
                                  f'{where}.reach_x_far'),
            approach_height=_as_float(_req(d, 'approach_height', where),
                                      f'{where}.approach_height'),
            tilt_min_center_z=_as_float(_req(d, 'tilt_min_center_z', where),
                                        f'{where}.tilt_min_center_z'),
            tilt_candidates_deg=tuple(
                _as_float(t, f'{where}.tilt_candidates_deg[{i}]')
                for i, t in enumerate(tilts)),
            planner_fallback=_as_str_tuple(_req(d, 'planner_fallback', where),
                                           f'{where}.planner_fallback'),
            # 놓기 순간 TCP 높이(m). 그리퍼가 크면 열었을 때 손끝이 드롭 통 벽에
            # 닿아(놓은 뒤 그 자세가 start-in-collision → 이후 계획 전부 즉시 거부)
            # episode 가 멈춘다. 그리퍼 길이에 따라 달라지므로 모델별로 준다.
            # 생략하면 FR3 기준 0.040(프랑카 핸드가 이 높이에서 벽을 넘음).
            drop_z=_as_float(d.get('drop_z', 0.040), f'{where}.drop_z'),
        )

    def to_dict(self):
        return {
            'reach_y_max': self.reach_y_max,
            'reach_x_far': self.reach_x_far,
            'approach_height': self.approach_height,
            'tilt_min_center_z': self.tilt_min_center_z,
            'tilt_candidates_deg': list(self.tilt_candidates_deg),
            'planner_fallback': list(self.planner_fallback),
            'drop_z': self.drop_z,
        }


class GraspSpec:
    """파지 알고리즘 중 **팔/그리퍼 기하에 의존하는** 튜닝값들.

    이 값들은 순수 알고리즘 상수처럼 보이지만 실제로는 그리퍼 손끝 길이·팔
    자유도에 물려 있어, 한 로봇 기준으로 하드코딩하면 다른 로봇에서 조용히
    깨진다(예: `max_above` 가 FR3 손끝 9.5mm 기준이라 손끝이 긴 Robotiq 에서
    적응형 하강 루프를 통째로 무효화했다). 그래서 모델별 프로파일로 뺀다.
    전 필드 선택 — 생략하면 FR3 기준 기본값이라 기존 동작이 불변이다.
    (감사 계획: docs/robot_profiles_audit_plan.md)
    """

    __slots__ = ('max_above', 'floor_raise', 'z_tol', 'raise_step',
                 'floor_clear', 'ik_seed_jitter', 'ik_seed_spread',
                 'pick_clear_r')

    def __init__(self, **kw):
        for slot in self.__slots__:
            setattr(self, slot, kw[slot])

    @classmethod
    def from_dict(cls, d, where='grasp'):
        if not isinstance(d, dict):
            raise ProfileError(f'{where}: 매핑이어야 한다')
        return cls(
            # 적응형 하강 z_cap = 볼트중심 + 이 값. '이보다 높으면 어차피 빈손'의
            # 상한. 손끝이 짧은 그리퍼는 작아도 되지만, 이 값이 바닥 한계(grasp_z)
            # 보다 작으면 적응형 하강 루프가 스킵된다. 생략 시 FR3 기준 0.006.
            max_above=_as_float(d.get('max_above', 0.006),
                                f'{where}.max_above'),
            # 바닥 한계 지배 시 적응형 하강이 grasp_z 위로 상향 탐색할 여유(m).
            # 손끝이 긴 그리퍼(Robotiq 등)는 이게 있어야 바닥 볼트에서 적응형
            # 하강 루프가 살아난다. 생략하면 0.0(FR3 동작 불변).
            floor_raise=_as_float(d.get('floor_raise', 0.0),
                                  f'{where}.floor_raise'),
            # 실행 후 실측 TCP z 허용 초과분(m). 컨트롤러 추종 정확도(팔+구동계)에
            # 민감하다. 생략 시 FR3 기준 0.003.
            z_tol=_as_float(d.get('z_tol', 0.003), f'{where}.z_tol'),
            # 적응형 하강 목표 상향 재계획 간격(m). 그리퍼 기하와 상호작용한다.
            # 생략 시 FR3 기준 0.002.
            raise_step=_as_float(d.get('raise_step', 0.002),
                                 f'{where}.raise_step'),
            # 손끝이 통 바닥 상면 위로 남길 여유(m). 하드 바닥 TCP(grasp_z) 유도에
            # 쓰인다. 생략 시 FR3 기준 0.0005.
            floor_clear=_as_float(d.get('floor_clear', 0.0005),
                                  f'{where}.floor_clear'),
            # ready 외 추가 IK 시드 수(팔 IK 분기 폴백). 여유자유도(7축 팔꿈치 분기)
            # 해소용이라 6축 팔에서는 의미가 다르다. 정수. 생략 시 FR3 기준 1.
            ik_seed_jitter=int(d.get('ik_seed_jitter', 1)),
            # IK 시드를 흔드는 폭(rad, 관절 한계 안에서 클램프). 생략 시 FR3 기준 1.2.
            ik_seed_spread=_as_float(d.get('ik_seed_spread', 1.2),
                                     f'{where}.ik_seed_spread'),
            # 파지 하강 전 임시 제거할 이웃 반경(m). 앞 항이 손가락 반경(그리퍼
            # 풋프린트) 성격이라 큰 그리퍼면 커져야 한다. 생략 시 FR3 기준 0.075.
            pick_clear_r=_as_float(d.get('pick_clear_r', 0.075),
                                   f'{where}.pick_clear_r'),
        )

    def to_dict(self):
        return {
            'max_above': self.max_above,
            'floor_raise': self.floor_raise,
            'z_tol': self.z_tol,
            'raise_step': self.raise_step,
            'floor_clear': self.floor_clear,
            'ik_seed_jitter': self.ik_seed_jitter,
            'ik_seed_spread': self.ik_seed_spread,
            'pick_clear_r': self.pick_clear_r,
        }


class DescriptionSpec:
    """이 모델의 URDF/SRDF/MoveIt 설정이 '어느 패키지 어느 파일'에 있는지.

    런치가 이 정보만으로 스택 전체를 세울 수 있어야 `robot_model:=` 인자 하나로
    전환이 끝난다. 경로는 ament 패키지 share 기준 상대경로다.
    """

    __slots__ = ('urdf_package', 'urdf_path', 'urdf_args',
                 'srdf_package', 'srdf_path', 'srdf_args',
                 'moveit_package', 'moveit_files', 'ompl_overlay',
                 'gazebo_entity', 'gazebo_resource_package')

    # MoveIt 이 뜨려면 반드시 있어야 하는 설정 파일 키.
    REQUIRED_MOVEIT_FILES = ('kinematics', 'joint_limits', 'ompl',
                             'controllers', 'rviz')

    def __init__(self, **kw):
        for slot in self.__slots__:
            setattr(self, slot, kw[slot])

    @staticmethod
    def _args(d, key, where):
        raw = d.get(key, {}) or {}
        if not isinstance(raw, dict):
            raise ProfileError(f'{where}.{key}: 매핑이어야 한다')
        # xacro 인자는 전부 문자열로 넘어간다. bool 을 'True' 로 넘기면 xacro 가
        # 조용히 참으로 읽어 버리는 사고가 잦아, 여기서 소문자로 정규화한다.
        out = {}
        for k, v in raw.items():
            if isinstance(v, bool):
                out[str(k)] = 'true' if v else 'false'
            else:
                out[str(k)] = str(v)
        return out

    @classmethod
    def from_dict(cls, d, where='description'):
        if not isinstance(d, dict):
            raise ProfileError(f'{where}: 매핑이어야 한다')

        urdf = _req(d, 'urdf', where)
        srdf = _req(d, 'srdf', where)
        moveit = _req(d, 'moveit', where)
        gazebo = d.get('gazebo', {}) or {}
        for sub, name in ((urdf, 'urdf'), (srdf, 'srdf'), (moveit, 'moveit')):
            if not isinstance(sub, dict):
                raise ProfileError(f'{where}.{name}: 매핑이어야 한다')

        files = _req(moveit, 'files', f'{where}.moveit')
        if not isinstance(files, dict):
            raise ProfileError(f'{where}.moveit.files: 매핑이어야 한다')
        missing = [k for k in cls.REQUIRED_MOVEIT_FILES if k not in files]
        if missing:
            raise ProfileError(
                f'{where}.moveit.files: 필수 설정 누락 {missing} — '
                f'{list(cls.REQUIRED_MOVEIT_FILES)} 전부 있어야 move_group 이 뜬다')

        # 벤더 ompl_planning.yaml 위에 덮어쓸 내용. 구조는 그 파일과 똑같다.
        # 있는 이유: 어떤 벤더는 `planner_configs` 를 아예 안 준다(UR 이 그렇다).
        # 그러면 우리 `planner_fallback` 이름이 하나도 안 맞아 MoveIt 이 조용히
        # 기본 플래너로 폴백하고, 어려운 구간용 폴백 로직 전체가 no-op 이 된다.
        overlay = moveit.get('ompl_overlay') or {}
        if not isinstance(overlay, dict):
            raise ProfileError(f'{where}.moveit.ompl_overlay: 매핑이어야 한다')

        return cls(
            urdf_package=_as_str(_req(urdf, 'package', f'{where}.urdf'),
                                 f'{where}.urdf.package'),
            urdf_path=_as_str(_req(urdf, 'path', f'{where}.urdf'),
                              f'{where}.urdf.path'),
            urdf_args=cls._args(urdf, 'args', f'{where}.urdf'),
            srdf_package=_as_str(_req(srdf, 'package', f'{where}.srdf'),
                                 f'{where}.srdf.package'),
            srdf_path=_as_str(_req(srdf, 'path', f'{where}.srdf'),
                              f'{where}.srdf.path'),
            srdf_args=cls._args(srdf, 'args', f'{where}.srdf'),
            moveit_package=_as_str(_req(moveit, 'package', f'{where}.moveit'),
                                   f'{where}.moveit.package'),
            moveit_files={k: _as_str(v, f'{where}.moveit.files[{k!r}]')
                          for k, v in files.items()},
            ompl_overlay=overlay,
            gazebo_entity=_as_str(gazebo.get('entity', 'robot'),
                                  f'{where}.gazebo.entity'),
            gazebo_resource_package=_as_str(
                gazebo.get('resource_package',
                           _req(urdf, 'package', f'{where}.urdf')),
                f'{where}.gazebo.resource_package'),
        )

    def to_dict(self):
        return {
            'urdf': {'package': self.urdf_package, 'path': self.urdf_path,
                     'args': dict(self.urdf_args)},
            'srdf': {'package': self.srdf_package, 'path': self.srdf_path,
                     'args': dict(self.srdf_args)},
            'moveit': {'package': self.moveit_package,
                       'files': dict(self.moveit_files),
                       'ompl_overlay': dict(self.ompl_overlay)},
            'gazebo': {'entity': self.gazebo_entity,
                       'resource_package': self.gazebo_resource_package},
        }


class RobotProfile:
    """등록된 로봇 모델 하나. 전환의 단위이자 검증의 단위다."""

    __slots__ = ('name', 'display_name', 'vendor', 'status', 'task_validated',
                 'notes', 'arm', 'gripper', 'workspace', 'grasp', 'description',
                 'source_path')

    def __init__(self, name, display_name, vendor, status, notes,
                 arm, gripper, workspace, description, source_path=None,
                 task_validated=False, grasp=None):
        self.name = name
        self.display_name = display_name
        self.vendor = vendor
        self.status = status
        # 이 팔로 **실제 작업(빈피킹)을 성공시켜 봤는가.** status 와 별개 축이다.
        # false 라도 전환은 허용된다 — 안전 검증(status)은 통과했다는 뜻이므로.
        self.task_validated = bool(task_validated)
        self.notes = notes
        self.arm = arm
        self.gripper = gripper
        self.workspace = workspace
        # 선택 섹션 — 없으면 FR3 기준 기본값의 GraspSpec (기존 동작 불변).
        self.grasp = grasp if grasp is not None else GraspSpec.from_dict({})
        self.description = description
        self.source_path = source_path

    @property
    def is_verified(self):
        """전환을 허용해도 되는 상태인가. draft 는 거부된다."""
        return self.status == 'verified'

    @classmethod
    def from_dict(cls, d, source_path=None):
        if not isinstance(d, dict):
            raise ProfileError('프로파일 최상위는 매핑이어야 한다')
        name = _as_str(_req(d, 'name', '<root>'), 'name')
        status = _as_str(d.get('status', 'draft'), 'status')
        if status not in STATUSES:
            raise ProfileError(
                f'status: {status!r} 은 알 수 없다 — {list(STATUSES)} 중 하나')
        return cls(
            name=name,
            display_name=_as_str(d.get('display_name', name), 'display_name'),
            vendor=_as_str(d.get('vendor', 'unknown'), 'vendor'),
            status=status,
            task_validated=bool(d.get('task_validated', False)),
            notes=str(d.get('notes', '') or ''),
            arm=ArmSpec.from_dict(_req(d, 'arm', '<root>')),
            gripper=GripperSpec.from_dict(_req(d, 'gripper', '<root>')),
            workspace=WorkspaceSpec.from_dict(_req(d, 'workspace', '<root>')),
            # 선택 섹션(팔/그리퍼 의존 파지 튜닝). 없으면 FR3 기준 기본값.
            grasp=GraspSpec.from_dict(d.get('grasp', {}) or {}),
            description=DescriptionSpec.from_dict(_req(d, 'description',
                                                       '<root>')),
            source_path=source_path,
        )

    def to_dict(self):
        return {
            'name': self.name,
            'display_name': self.display_name,
            'vendor': self.vendor,
            'status': self.status,
            'task_validated': self.task_validated,
            'notes': self.notes,
            'arm': self.arm.to_dict(),
            'gripper': self.gripper.to_dict(),
            'workspace': self.workspace.to_dict(),
            'grasp': self.grasp.to_dict(),
            'description': self.description.to_dict(),
        }

    # ---- 파이프라인이 실제로 소비하는 파생값 ----
    def tilt_candidates_rad(self):
        return tuple(math.radians(d) for d in self.workspace.tilt_candidates_deg)

    def __repr__(self):
        return (f'<RobotProfile {self.name!r} ({self.status}) '
                f'group={self.arm.planning_group!r} '
                f'gripper={self.gripper.kind}/{self.gripper.action_type}>')
