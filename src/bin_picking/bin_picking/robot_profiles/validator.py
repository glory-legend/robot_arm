# -*- coding: utf-8 -*-
"""프로파일 검증 — 사람이 손으로 채운 값이 실제 로봇과 맞는지 대조한다.

**이 파일이 등록 기능의 진짜 값어치다.** 스키마(`schema.py`)는 "빠진 칸이 없는가"만
본다. 하지만 등록은 사람이 데이터시트와 URDF 를 뒤져 수기로 옮겨 적는 작업이라,
빠짐없이 채워도 **틀리게** 채우는 일이 반드시 생긴다. 그리고 그 오류는 대부분
조용하다:

  - 관절 이름 오타 → `/joint_states` 매칭 실패 → 파지 판정이 영영 `None` → 전패
  - 관절 한계를 URDF 보다 넓게 적음 → '한계 근접 경고'가 안 뜬 채 컨트롤러가 거부
  - `planner_fallback` 이름이 ompl 설정에 없음 → MoveIt 이 조용히 기본 플래너로
    폴백 → 폴백 로직 전체가 no-op
  - 그리퍼 지령 단위 혼동(rad↔m) → 명령은 수락되는데 손가락이 안 움직임

이 저장소의 원칙은 "침묵은 버그다"(docs/desktop_protocol.md §4). 그래서 위 오류를
**등록/기동 시점에** 잡아 시끄럽게 실패시킨다.

검증은 두 층이다:
  - **정적(static)** — 파일만 보고 판단. 패키지·파일 존재, 값의 자기모순.
  - **모델 대조(model)** — 렌더된 URDF/SRDF 와 대조. 링크·관절·그룹의 실재 확인.

⚠ 이 모듈은 rclpy 를 임포트하지 않는다. 문자열/목록을 받는 순수 함수라 Gazebo 나
  실행 중인 로봇 없이 pytest 로 전부 검증할 수 있다. 실행 중 시스템에서 값을
  긁어 오는 부분(`/joint_states`, 액션 서버 존재)은 `model_cli.py` 가 담당한다.
"""
import xml.etree.ElementTree as ET

# 심각도. error 가 하나라도 있으면 그 프로파일로는 전환하지 않는다.
ERROR = 'error'
WARN = 'warn'
INFO = 'info'

_ORDER = {ERROR: 0, WARN: 1, INFO: 2}


class Finding:
    """검증 결과 한 줄. `where` 는 프로파일 안의 위치(고쳐야 할 칸)를 가리킨다."""

    __slots__ = ('level', 'where', 'message')

    def __init__(self, level, where, message):
        self.level = level
        self.where = where
        self.message = message

    def __repr__(self):
        return f'<{self.level} {self.where}: {self.message}>'

    def format(self):
        mark = {ERROR: '⛔', WARN: '⚠', INFO: 'ℹ'}[self.level]
        return f'{mark} [{self.where}] {self.message}'


class Report:
    """한 프로파일에 대한 검증 결과 묶음."""

    def __init__(self, profile_name, findings=None, checked=None):
        self.profile_name = profile_name
        self.findings = list(findings or [])
        # 실제로 수행한 검사 이름들 — "무엇을 확인했는가"가 보고에 남아야
        # 통과가 '검사를 건너뛴 통과'인지 구분할 수 있다.
        self.checked = list(checked or [])

    def add(self, level, where, message):
        self.findings.append(Finding(level, where, message))
        return self

    def extend(self, other):
        self.findings.extend(other.findings)
        self.checked.extend(other.checked)
        return self

    @property
    def errors(self):
        return [f for f in self.findings if f.level == ERROR]

    @property
    def warnings(self):
        return [f for f in self.findings if f.level == WARN]

    @property
    def ok(self):
        """전환을 허용해도 되는가. 경고는 허용, 오류는 불가."""
        return not self.errors

    def sorted_findings(self):
        return sorted(self.findings, key=lambda f: (_ORDER[f.level], f.where))

    def format(self):
        lines = [f'프로파일 검증: {self.profile_name}']
        if self.checked:
            lines.append('  수행한 검사: ' + ', '.join(self.checked))
        if not self.findings:
            lines.append('  ✅ 지적사항 없음')
        else:
            lines.extend('  ' + f.format() for f in self.sorted_findings())
        lines.append(
            f'  → 오류 {len(self.errors)}건 / 경고 {len(self.warnings)}건 — '
            + ('통과' if self.ok else '실패(전환 불가)'))
        return '\n'.join(lines)


# =====================================================================
# 정적 검증 — 파일만 보고 판단
# =====================================================================
def validate_static(profile, package_share=None, path_exists=None):
    """스키마를 통과한 프로파일의 '값이 말이 되는가'를 본다.

    `package_share(name) -> 경로` 와 `path_exists(경로) -> bool` 을 주면 참조하는
    패키지·파일이 실제로 있는지까지 확인한다. 안 주면 그 검사만 건너뛰고
    (건너뛴 사실은 `checked` 에 남지 않는다) 나머지는 그대로 수행한다 — ROS 가
    소스되지 않은 환경(순수 pytest)에서도 돌아야 하기 때문이다.
    """
    rep = Report(profile.name, checked=['static'])
    arm, grip, ws = profile.arm, profile.gripper, profile.workspace

    # ---- 그리퍼 지령이 스스로 모순되지 않는가 ----
    # ⚠ 비교는 반드시 **물리 개구(m)** 공간에서 한다. aperture.* 는 물리 개구인데
    #   open_cmd/closed_cmd 는 관절 단위(선형 그리퍼는 m, 각도 그리퍼는 rad)라,
    #   그대로 대소를 비교하면 각도 그리퍼에서 rad 와 m 를 견주게 된다.
    hw_closed = grip.halfwidth_of(grip.closed_cmd)
    hw_open = grip.halfwidth_of(grip.open_cmd)

    # 닫힘 지령이 개구 하한보다 넓으면 '닫아도 물체를 못 문다'.
    if hw_closed >= grip.min_open:
        rep.add(ERROR, 'gripper.aperture.min_open',
                f'닫힘 지령의 개구({hw_closed:.4f}m)가 min_open({grip.min_open}m) '
                f'이상이다 — 끝까지 닫아도 파지 하한보다 넓어 물체를 물 수 없다')
    if grip.pregrasp_open > hw_open:
        rep.add(ERROR, 'gripper.aperture.pregrasp_open',
                f'pregrasp_open({grip.pregrasp_open}m)이 만개 개구'
                f'({hw_open:.4f}m)보다 넓다 — 그리퍼가 벌릴 수 있는 한계를 넘는다')
    if grip.aperture_step <= 0.0:
        rep.add(ERROR, 'gripper.aperture.step',
                f'step({grip.aperture_step})은 0 보다 커야 한다 — '
                f'0 이면 이웃 회피 개구 탐색이 무한 루프가 된다')

    # ---- 각도 그리퍼인데 변환을 안 넣었는가 ----
    # rad 단위 관절값을 m 로 착각하면 파지 판정이 통째로 무의미해진다.
    # 항등 변환(scale=1, offset=0)은 '선형(m)' 그리퍼에서만 맞다.
    if (grip.kind == 'angular' and grip.halfwidth_curve is None
            and grip.halfwidth_scale == 1.0 and grip.halfwidth_offset == 0.0):
        rep.add(ERROR, 'gripper.halfwidth_scale',
                'kind: angular 인데 관절값→개구 변환이 항등(scale=1, offset=0)이다 — '
                '각도(rad)를 그대로 개구(m)로 쓰고 있다. 실측 대응표를 '
                'halfwidth_curve 에 넣거나 선형근사로 scale/offset 을 채우세요')

    # 각도 그리퍼를 선형 1차식으로 근사하면 대개 중간 구간에서 어긋난다.
    # 링크 기하 때문에 각도↔개구가 비선형이기 때문이다. 막지는 않되 알린다.
    if grip.kind == 'angular' and grip.halfwidth_curve is None:
        rep.add(WARN, 'gripper.halfwidth_curve',
                '각도 구동 그리퍼를 선형 1차식으로 근사하고 있다 — 각도↔개구는 '
                '링크 기하상 대개 비선형이라 중간 개구에서 오차가 커진다. '
                '몇 지점을 실측해 halfwidth_curve 로 주는 편이 안전하다')

    # ---- 손끝 기하가 개구와 모순되지 않는가 ----
    # 손가락 반폭의 2배보다 좁은 개구는 손가락끼리 겹친다는 뜻이다.
    if grip.min_open < grip.finger_half_w:
        rep.add(WARN, 'gripper.aperture.min_open',
                f'min_open({grip.min_open})이 손가락 팁 반폭'
                f'({grip.finger_half_w})보다 좁다 — 기하가 서로 어긋난 것 같다')

    # ---- 워크스페이스 값이 채워졌는가 ----
    if ws.approach_height <= 0.0:
        rep.add(ERROR, 'workspace.approach_height',
                f'approach_height({ws.approach_height})는 0 보다 커야 한다')
    if ws.reach_y_max <= 0.0:
        rep.add(ERROR, 'workspace.reach_y_max',
                f'reach_y_max({ws.reach_y_max})는 0 보다 커야 한다 — '
                f'0 이면 모든 볼트가 도달 불가로 걸러져 아무것도 못 집는다')

    # ---- 참조하는 패키지/파일이 실제로 있는가 ----
    if package_share is not None and path_exists is not None:
        rep.checked.append('files')
        desc = profile.description
        refs = [('description.urdf', desc.urdf_package, desc.urdf_path),
                ('description.srdf', desc.srdf_package, desc.srdf_path)]
        for key, rel in sorted(desc.moveit_files.items()):
            refs.append((f'description.moveit.files.{key}',
                         desc.moveit_package, rel))
        seen_missing_pkg = set()
        for where, pkg, rel in refs:
            try:
                share = package_share(pkg)
            except Exception as exc:              # noqa: BLE001
                if pkg not in seen_missing_pkg:
                    seen_missing_pkg.add(pkg)
                    rep.add(ERROR, where,
                            f'패키지 {pkg!r} 를 찾을 수 없다 — 워크스페이스에 없거나 '
                            f'빌드/소스가 안 됐다 ({exc.__class__.__name__})')
                continue
            if not path_exists(share + '/' + rel):
                rep.add(ERROR, where,
                        f'{pkg}/{rel} 가 없다 — 경로 오타이거나 그 파일이 설치되지 '
                        f'않았다(setup.py data_files 확인)')
    return rep


# =====================================================================
# URDF / SRDF 대조 — "적어 넣은 이름이 실제로 존재하는가"
# =====================================================================
def parse_urdf(urdf_xml):
    """렌더된 URDF → (링크이름 집합, {관절이름: (type, lower, upper)}).

    한계가 없는 관절(continuous/fixed)은 (type, None, None) 이 된다.
    """
    root = ET.fromstring(urdf_xml)
    links = {e.get('name') for e in root.findall('link') if e.get('name')}
    joints = {}
    for e in root.findall('joint'):
        name = e.get('name')
        if not name:
            continue
        jtype = e.get('type') or ''
        lim = e.find('limit')
        lo = hi = None
        if lim is not None:
            lo = lim.get('lower')
            hi = lim.get('upper')
            lo = float(lo) if lo is not None else None
            hi = float(hi) if hi is not None else None
        joints[name] = (jtype, lo, hi)
    return links, joints


def parse_srdf(srdf_xml):
    """렌더된 SRDF → ({그룹이름: (base_link, tip_link)}, {그룹: {상태이름}})."""
    root = ET.fromstring(srdf_xml)
    groups = {}
    for g in root.findall('group'):
        name = g.get('name')
        if not name:
            continue
        chain = g.find('chain')
        if chain is not None:
            groups[name] = (chain.get('base_link'), chain.get('tip_link'))
        else:
            groups[name] = (None, None)
    states = {}
    for s in root.findall('group_state'):
        states.setdefault(s.get('group'), set()).add(s.get('name'))
    return groups, states


def validate_against_model(profile, urdf_xml=None, srdf_xml=None):
    """프로파일에 적은 이름들이 실제 URDF/SRDF 에 있는지 대조한다.

    둘 다 없으면 아무 검사도 하지 않고 빈 보고를 낸다(호출자가 '무엇을 확인했는지'
    를 `checked` 로 알 수 있다).
    """
    rep = Report(profile.name)
    arm, grip = profile.arm, profile.gripper

    if urdf_xml:
        rep.checked.append('urdf')
        try:
            links, joints = parse_urdf(urdf_xml)
        except ET.ParseError as exc:
            rep.add(ERROR, 'description.urdf',
                    f'URDF 를 파싱할 수 없다 — {exc}')
            links, joints = set(), {}

        for where, frame in (('arm.base_frame', arm.base_frame),
                             ('arm.tcp_frame', arm.tcp_frame)):
            if links and frame not in links:
                rep.add(ERROR, where,
                        f'링크 {frame!r} 가 URDF 에 없다 — 이름 오타이거나 '
                        f'xacro 인자(arm_prefix/ee_id)가 프로파일과 다르다')

        for link in grip.touch_links:
            if links and link not in links:
                rep.add(ERROR, 'gripper.touch_links',
                        f'링크 {link!r} 가 URDF 에 없다 — 볼트 부착 시 충돌 허용이 '
                        f'적용되지 않아 파지 직후 계획이 실패한다')

        # 팔 관절: 존재 + 실제로 움직이는 관절 + 한계 정합
        for j in arm.joints:
            if not joints:
                break
            if j not in joints:
                rep.add(ERROR, 'arm.joints',
                        f'관절 {j!r} 가 URDF 에 없다 — /joint_states 매칭이 실패해 '
                        f'팔 자세를 영영 못 읽는다')
                continue
            jtype, lo, hi = joints[j]
            if jtype == 'fixed':
                rep.add(ERROR, 'arm.joints',
                        f'관절 {j!r} 가 fixed 다 — 계획 대상이 될 수 없다')
            p_lo, p_hi = arm.joint_limits[j]
            # 프로파일 한계가 URDF 보다 '넓으면' 진단이 침묵한다: 컨트롤러는
            # 거부하는데 우리 쪽은 "한계 여유 충분"이라고 로그를 남긴다.
            if lo is not None and p_lo < lo - 1e-9:
                rep.add(WARN, 'arm.joint_limits',
                        f'{j}: 하한 {p_lo} 가 URDF 값 {lo} 보다 넓다 — '
                        f'한계 근접 경고가 뜨지 않은 채 계획이 거부될 수 있다')
            if hi is not None and p_hi > hi + 1e-9:
                rep.add(WARN, 'arm.joint_limits',
                        f'{j}: 상한 {p_hi} 가 URDF 값 {hi} 보다 넓다 — '
                        f'한계 근접 경고가 뜨지 않은 채 계획이 거부될 수 있다')

        # 그리퍼 관절: 존재 + 지령값이 URDF 한계 안인가
        for j in grip.state_joints:
            if joints and j not in joints:
                level = ERROR if j == grip.command_joint else WARN
                rep.add(level, 'gripper.state_joints',
                        f'관절 {j!r} 가 URDF 에 없다'
                        + (' — 파지 성공/빈손 판정이 값을 못 읽어 전부 실패로 '
                           '처리된다' if level == ERROR else ''))
        cj = grip.command_joint
        if joints and cj in joints:
            _jtype, lo, hi = joints[cj]
            for where, val in (('gripper.open_cmd', grip.open_cmd),
                               ('gripper.closed_cmd', grip.closed_cmd)):
                if lo is not None and val < lo - 1e-9:
                    rep.add(ERROR, where,
                            f'{val} 가 {cj} 의 URDF 하한 {lo} 미만이다 — '
                            f'컨트롤러가 지령을 거부하거나 관절이 한계를 벗어난다')
                if hi is not None and val > hi + 1e-9:
                    rep.add(ERROR, where,
                            f'{val} 가 {cj} 의 URDF 상한 {hi} 초과다 — '
                            f'컨트롤러가 지령을 거부하거나 관절이 한계를 벗어난다')

    if srdf_xml:
        rep.checked.append('srdf')
        try:
            groups, states = parse_srdf(srdf_xml)
        except ET.ParseError as exc:
            rep.add(ERROR, 'description.srdf',
                    f'SRDF 를 파싱할 수 없다 — {exc}')
            groups, states = {}, {}

        g = arm.planning_group
        if groups and g not in groups:
            rep.add(ERROR, 'arm.planning_group',
                    f'planning group {g!r} 가 SRDF 에 없다 — MoveIt 이 모든 계획 '
                    f'요청을 즉시 거부한다 (SRDF 의 그룹: {sorted(groups)})')
        elif groups:
            base, tip = groups[g]
            if base is not None and base != arm.base_frame:
                rep.add(WARN, 'arm.base_frame',
                        f'SRDF 그룹 {g!r} 의 base_link 는 {base!r} 인데 프로파일은 '
                        f'{arm.base_frame!r} 이다 — 목표 자세의 기준 프레임이 어긋난다')
            if tip is not None and tip != arm.tcp_frame:
                rep.add(WARN, 'arm.tcp_frame',
                        f'SRDF 그룹 {g!r} 의 tip_link 는 {tip!r} 인데 프로파일은 '
                        f'{arm.tcp_frame!r} 이다 — 파지 깊이 계산이 다른 링크를 '
                        f'기준으로 돌아간다')
            if arm.home_state not in states.get(g, set()):
                rep.add(ERROR, 'arm.home_state',
                        f'group_state {arm.home_state!r} 가 그룹 {g!r} 에 없다 — '
                        f'Ready 복귀 동작이 실패한다 '
                        f'(있는 상태: {sorted(states.get(g, set())) or "없음"})')
    return rep


# =====================================================================
# 실행 중 시스템 대조 — 이름이 아니라 '지금 살아 있는가'
# =====================================================================
def validate_against_runtime(profile, joint_state_names=None,
                             action_names=None, controller_names=None):
    """실행 중인 시스템에서 긁어 온 목록과 대조한다.

    인자를 안 주면 그 검사는 건너뛴다 — Gazebo 가 안 떠 있는 상태에서도
    나머지 검증은 그대로 돌아야 하기 때문이다.

    joint_state_names : `/joint_states` 에 실제로 실려 오는 관절 이름들
    action_names      : 노출된 액션 이름들 (그리퍼 액션 확인용)
    controller_names  : `controller_manager` 에 올라온 컨트롤러 이름들
    """
    rep = Report(profile.name)
    arm, grip = profile.arm, profile.gripper

    if joint_state_names is not None:
        rep.checked.append('joint_states')
        present = set(joint_state_names)
        missing_arm = [j for j in arm.joints if j not in present]
        if missing_arm:
            rep.add(ERROR, 'arm.joints',
                    f'/joint_states 에 없는 관절 {missing_arm} — 이름이 틀렸거나 '
                    f'joint_state_broadcaster 가 이 관절을 발행하지 않는다')
        if grip.command_joint not in present:
            rep.add(ERROR, 'gripper.command_joint',
                    f'/joint_states 에 {grip.command_joint!r} 가 없다 — '
                    f'파지 성공 판정이 실측을 못 읽어 모든 시도가 실패로 기록된다')
        # 종동(mimic) 관절은 시뮬레이터가 발행할 수도, 안 할 수도 있다. 없으면
        # Cartesian 충돌검사의 start_state 에서 조용히 빠져 '미리 좁혀 둔 그리퍼'가
        # 반영되지 않는다 — 하강 달성률이 이유 없이 떨어지는 원인이 되므로 알린다.
        missing_state = [j for j in grip.state_joints
                         if j != grip.command_joint and j not in present]
        if missing_state:
            rep.add(WARN, 'gripper.state_joints',
                    f'/joint_states 에 없는 종동 관절 {missing_state} — 이 시뮬/드라이버는 '
                    f'mimic 관절을 발행하지 않는 것 같다. 목록에서 빼거나, 빠진 채로 '
                    f'충돌검사가 도는 것을 감수할지 판단하세요')

    if action_names is not None:
        rep.checked.append('actions')
        # 액션 이름은 앞의 '/' 유무가 환경마다 달라 정규화해 비교한다.
        norm = {a.lstrip('/') for a in action_names}
        want = grip.action_name.lstrip('/')
        if want not in norm:
            rep.add(ERROR, 'gripper.action_name',
                    f'액션 서버 {grip.action_name!r} 가 없다 — 그리퍼 컨트롤러'
                    f'({grip.controller!r})가 안 떴거나 액션 이름이 다르다')

    if controller_names is not None:
        rep.checked.append('controllers')
        present = set(controller_names)
        for where, ctrl in (('arm.controller', arm.controller),
                            ('gripper.controller', grip.controller)):
            if ctrl not in present:
                rep.add(ERROR, where,
                        f'컨트롤러 {ctrl!r} 가 controller_manager 에 없다 — '
                        f'스포너가 실패했거나 이름이 다르다 '
                        f'(올라온 컨트롤러: {sorted(present) or "없음"})')
    return rep


def validate_all(profile, package_share=None, path_exists=None,
                 urdf_xml=None, srdf_xml=None, joint_state_names=None,
                 action_names=None, controller_names=None):
    """가능한 모든 층의 검증을 한 번에 돌려 하나의 보고로 합친다."""
    rep = validate_static(profile, package_share=package_share,
                          path_exists=path_exists)
    rep.extend(validate_against_model(profile, urdf_xml=urdf_xml,
                                      srdf_xml=srdf_xml))
    rep.extend(validate_against_runtime(
        profile, joint_state_names=joint_state_names,
        action_names=action_names, controller_names=controller_names))
    return rep
