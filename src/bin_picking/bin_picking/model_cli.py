# -*- coding: utf-8 -*-
"""`binpick_model` — 로봇 모델 등록·검증·전환 명령.

    binpick_model list                 등록된 모델과 검증 상태
    binpick_model show <이름>           프로파일 전체 내용
    binpick_model new  <이름>           새 모델 등록용 뼈대 생성(채워야 할 칸 안내)
    binpick_model validate <이름>       정적 검증 (파일만 보고 판단)
    binpick_model verify <이름>         실행 중인 시스템/URDF 와 대조 (가장 강한 검증)
    binpick_model use  <이름>           활성 모델 전환  ← 원클릭 전환

설계 의도: **등록이 핵심이고 전환은 그 결과다.** 그래서 `use` 는 아무 이름이나
받지 않는다 — 등록돼 있고 `status: verified` 인 모델만 통과시킨다. 검증되지 않은
값으로 로봇을 움직이면(관절 한계나 그리퍼 지령 단위가 틀린 채로) 실물에서는
충돌·과주행로 직결되기 때문이다.

`verify` 만 ROS 를 쓴다(실행 중인 노드에서 `/joint_states`·액션·컨트롤러 목록을
긁어 온다). 나머지 하위명령은 rclpy 없이 동작하므로 로봇이 안 떠 있어도 쓸 수 있다.
"""
import argparse
import os
import subprocess
import sys

import yaml

from bin_picking import robot_profiles
from bin_picking.robot_profiles import validator as V
from bin_picking.robot_profiles import vendor_yaml


# =====================================================================
# 공통 헬퍼
# =====================================================================
def _get(name):
    try:
        return robot_profiles.get(name)
    except robot_profiles.ProfileNotFound as exc:
        print(str(exc), file=sys.stderr)
        raise SystemExit(2)


def _ament_helpers():
    """패키지/파일 존재 확인용 콜백. ament 를 못 쓰면 (None, None)."""
    try:
        from ament_index_python.packages import get_package_share_directory
    except ImportError:
        return None, None
    return get_package_share_directory, os.path.exists


def _render_xacro(package, rel_path, args):
    """프로파일이 가리키는 xacro 를 실제로 렌더한다. 실패하면 (None, 오류문)."""
    get_share, _ = _ament_helpers()
    if get_share is None:
        return None, 'ament_index_python 을 못 찾음 (ROS 를 source 했는지 확인)'
    try:
        path = os.path.join(get_share(package), rel_path)
    except Exception as exc:                       # noqa: BLE001
        return None, f'패키지 {package!r} 를 찾을 수 없음 ({exc})'
    cmd = ['xacro', path] + [f'{k}:={v}' for k, v in sorted(args.items())]
    try:
        out = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
    except FileNotFoundError:
        return None, 'xacro 실행 파일을 못 찾음 (ROS 를 source 했는지 확인)'
    except subprocess.TimeoutExpired:
        return None, 'xacro 가 120초 안에 끝나지 않음'
    if out.returncode != 0:
        tail = (out.stderr or '').strip().splitlines()[-5:]
        return None, 'xacro 렌더 실패:\n      ' + '\n      '.join(tail)
    return out.stdout, None


# =====================================================================
# list / show
# =====================================================================
def cmd_list(_args):
    found = robot_profiles.discover()
    active = robot_profiles.active_model_name()

    print(f'탐색 경로: {robot_profiles.search_dirs()}')
    print(f'활성 모델: {active}'
          + ('' if active in found else '   ⛔ 등록되지 않음!'))
    print()
    if not found:
        print('등록된 모델이 없습니다. `binpick_model new <이름>` 으로 시작하세요.')
    else:
        # 두 축을 나란히 보여 준다 — '안전 검증'과 '작업 성능'은 별개다.
        print(f'{"":2} {"이름":<20} {"안전검증":<14} {"작업성능":<12} {"제조사":<24} 출처')
        for name in sorted(found):
            p = found[name]
            mark = '*' if name == active else ' '
            status = '✅ verified' if p.is_verified else '⬜ draft'
            task = '✅ 성공확인' if p.task_validated else '— 미확인'
            print(f'{mark:2} {p.name:<20} {status:<14} {task:<12} {p.vendor:<24} '
                  f'{p.source_path}')
        print('\n  안전검증 = 프로파일 값이 실제 URDF/SRDF/런타임과 대조됨 (전환 게이트)')
        print('  작업성능 = 이 팔로 실제 빈피킹을 성공시켜 본 기록이 있는가')

    errors = robot_profiles.discover_errors()
    if errors:
        # 깨진 파일을 조용히 숨기면 "왜 내 모델이 안 보이지"로 시간을 버린다.
        print(f'\n⛔ 읽지 못한 프로파일 {len(errors)}건:')
        for path, msg in errors:
            print(f'   {path}\n     {msg}')
    return 0 if active in found else 1


def cmd_show(args):
    p = _get(args.name)
    print(f'# {p.display_name} ({p.vendor}) — status: {p.status}')
    print(f'# 출처: {p.source_path}')
    if p.notes:
        print(f'# 비고: {p.notes}')
    print(yaml.safe_dump(p.to_dict(), allow_unicode=True, sort_keys=False,
                         default_flow_style=False))
    return 0


# =====================================================================
# new — 등록 뼈대 생성
# =====================================================================
_SCAFFOLD_HEADER = """\
# =====================================================================
#  {name} — 로봇 모델 프로파일 (등록 대기)
# =====================================================================
# 이 파일은 뼈대입니다. 아래 값들은 **{template} 의 값을 복사해 둔 것**이라
# 그대로 두면 거의 확실히 틀립니다. 항목마다 실제 로봇의 값으로 바꾸세요.
#
# 채우는 순서 (앞의 것이 뒤의 것을 결정합니다):
#
#   1. description  — 이 로봇의 URDF/SRDF/MoveIt 설정이 어느 패키지에 있는가.
#                     여기가 맞아야 나머지를 URDF 로 대조할 수 있습니다.
#   2. arm          — planning group / base·TCP 프레임 / 관절 이름.
#                     `xacro <urdf> | grep '<link name'` 으로 실제 이름을 확인하세요.
#   3. arm.joint_limits — 관절 한계(rad). URDF 값보다 **넓게 적지 마세요** —
#                     넓으면 '한계 근접' 경고가 침묵한 채 계획이 거부됩니다.
#   4. gripper      — 지령 단위가 무엇인지 먼저 정하세요(kind: linear=m / angular=rad).
#                     angular 면 halfwidth_scale/offset 에 실측 선형근사가 필요합니다.
#   5. gripper.geometry — TCP 와 손끝의 z 차이, 손끝 팁 반폭. URDF collision box
#                     치수에서 뽑으세요(추측 금지 — 파지 깊이가 여기서 결정됩니다).
#   6. workspace    — **실측값입니다.** 카탈로그 도달반경을 베끼지 마세요.
#                     통 위치·설치 높이·그리퍼 길이가 모두 섞인 값입니다.
#
# 다 채운 뒤:
#   binpick_model validate {name}   # 값의 자기모순 + 파일 존재 확인
#   binpick_model verify   {name}   # 실제 URDF/SRDF/실행 중 시스템과 대조
#   → 통과하면 아래 status 를 verified 로 바꾸세요. 그래야 `use` 가 허용됩니다.
# ---------------------------------------------------------------------
"""


def cmd_new(args):
    template = _get(args.template)
    target_dir = args.dir or robot_profiles.user_profile_dir()
    os.makedirs(target_dir, exist_ok=True)
    path = os.path.join(target_dir, f'{args.name}.yaml')

    if os.path.exists(path) and not args.force:
        print(f'이미 있습니다: {path}\n덮어쓰려면 --force', file=sys.stderr)
        return 2

    d = template.to_dict()
    d['name'] = args.name
    d['display_name'] = args.name
    d['vendor'] = 'TODO — 제조사'
    # 뼈대는 반드시 미검증으로 태어난다. 이걸 verified 로 만들어 두면 사람이
    # 값을 채우기도 전에 `use` 가 통과해 버린다.
    d['status'] = 'draft'
    d['notes'] = (f'{template.name} 프로파일에서 생성한 뼈대. '
                  f'모든 값을 실제 로봇 값으로 교체한 뒤 verify 할 것.')

    body = yaml.safe_dump(d, allow_unicode=True, sort_keys=False,
                          default_flow_style=False)
    with open(path, 'w', encoding='utf-8') as f:
        f.write(_SCAFFOLD_HEADER.format(name=args.name, template=template.name))
        f.write(body)

    print(f'생성했습니다: {path}')
    print(f'  1) 파일을 열어 값을 실제 로봇 값으로 교체')
    print(f'  2) binpick_model validate {args.name}')
    print(f'  3) binpick_model verify {args.name}')
    print(f'  4) status 를 verified 로 바꾼 뒤 binpick_model use {args.name}')
    return 0


# =====================================================================
# validate — 정적
# =====================================================================
def cmd_validate(args):
    p = _get(args.name)
    get_share, exists = _ament_helpers()
    rep = V.validate_static(p, package_share=get_share, path_exists=exists)
    if get_share is None:
        print('ℹ ROS 를 source 하지 않아 패키지/파일 존재 확인은 건너뜁니다.')
    print(rep.format())
    return 0 if rep.ok else 1


# =====================================================================
# verify — URDF/SRDF + 실행 중 시스템 대조
# =====================================================================
def _collect_runtime(timeout_sec):
    """실행 중인 ROS 그래프에서 관절/액션/컨트롤러 목록을 긁는다.

    아무것도 안 떠 있으면 (None, None, None) 을 돌려 '그 검사는 건너뜀'이 되게
    한다 — 로봇이 없는 상태의 verify 도 URDF 대조까지는 유효하기 때문이다.
    """
    try:
        import rclpy
        from rclpy.node import Node
        from sensor_msgs.msg import JointState
    except ImportError:
        print('ℹ rclpy 를 못 찾아 실행 중 시스템 대조는 건너뜁니다.')
        return None, None, None

    joint_names = None
    action_names = None
    controller_names = None

    rclpy.init(args=None)
    node = Node('binpick_model_verify')
    try:
        received = {}

        def _cb(msg):
            received['names'] = list(msg.name)

        node.create_subscription(JointState, 'joint_states', _cb, 10)
        deadline = node.get_clock().now().nanoseconds + int(timeout_sec * 1e9)
        while ('names' not in received
               and node.get_clock().now().nanoseconds < deadline):
            rclpy.spin_once(node, timeout_sec=0.1)
        joint_names = received.get('names')
        if joint_names is None:
            print(f'ℹ /joint_states 가 {timeout_sec:.0f}초 안에 안 와서 '
                  f'관절 대조는 건너뜁니다(시뮬이 안 떠 있는 듯).')

        # 액션 이름은 이름/타입 목록에서 뽑는다. 액션은 내부적으로 여러 토픽/
        # 서비스로 펼쳐지므로, get_action_names_and_types 가 있으면 그걸 쓴다.
        try:
            action_names = [n for n, _t in node.get_action_names_and_types()]
        except AttributeError:
            action_names = None

        controller_names = _list_controllers(node, timeout_sec)
    finally:
        node.destroy_node()
        rclpy.shutdown()
    return joint_names, action_names, controller_names


def _list_controllers(node, timeout_sec):
    """controller_manager 에 올라온 컨트롤러 이름들. 없으면 None(=검사 건너뜀)."""
    try:
        from controller_manager_msgs.srv import ListControllers
    except ImportError:
        return None
    cli = node.create_client(ListControllers, '/controller_manager/list_controllers')
    if not cli.wait_for_service(timeout_sec=timeout_sec):
        print('ℹ controller_manager 서비스가 없어 컨트롤러 대조는 건너뜁니다.')
        return None
    import rclpy
    fut = cli.call_async(ListControllers.Request())
    rclpy.spin_until_future_complete(node, fut, timeout_sec=timeout_sec)
    if not fut.done() or fut.result() is None:
        return None
    return [c.name for c in fut.result().controller]


def _check_planner_names(profile, report):
    """PLANNER_FALLBACK 이름이 그 모델의 ompl 설정에 실제로 있는지 본다.

    이름이 안 맞으면 MoveIt 이 조용히 기본 플래너로 폴백해서, 어려운 구간용
    폴백 로직 전체가 아무 일도 안 하게 된다 — 가장 알아채기 힘든 종류의 오설정.
    """
    get_share, _ = _ament_helpers()
    if get_share is None:
        return
    desc = profile.description
    try:
        path = os.path.join(get_share(desc.moveit_package),
                            desc.moveit_files['ompl'])
        ompl = vendor_yaml.load(path) or {}
    except Exception as exc:                       # noqa: BLE001
        report.add(V.WARN, 'description.moveit.files.ompl',
                   f'ompl 설정을 읽지 못해 플래너 이름을 대조하지 못했다 — {exc}')
        return
    report.checked.append('planners')

    # 런치가 하는 것과 같은 순서로 오버레이를 얹은 뒤 대조해야, 실제로 MoveIt 이
    # 보게 될 이름 집합과 같아진다.
    merged = dict(ompl)
    merged.update(desc.ompl_overlay or {})

    configs = set((merged.get('planner_configs') or {}).keys())
    group = merged.get(profile.arm.planning_group)
    group_planners = set((group or {}).get('planner_configs') or [])
    known = configs | group_planners
    if not known:
        report.add(V.ERROR, 'workspace.planner_fallback',
                   f'ompl 설정({path})에도 프로파일 오버레이에도 planner_configs 가 '
                   f'없다 — planner_fallback 의 이름이 하나도 매칭되지 않아 MoveIt 이 '
                   f'조용히 기본 플래너로 폴백하고 폴백 로직이 통째로 no-op 이 된다. '
                   f'description.moveit.ompl_overlay 로 planner_configs 를 채우세요')
        return
    unknown = [n for n in profile.workspace.planner_fallback if n not in known]
    if unknown:
        report.add(V.ERROR, 'workspace.planner_fallback',
                   f'ompl 설정에 없는 플래너 이름 {unknown} — MoveIt 이 조용히 기본 '
                   f'플래너로 폴백해 폴백 로직이 no-op 이 된다 '
                   f'(사용 가능: {sorted(known)})')


def cmd_verify(args):
    p = _get(args.name)
    get_share, exists = _ament_helpers()

    rep = V.validate_static(p, package_share=get_share, path_exists=exists)

    # --- URDF/SRDF 를 실제로 렌더해서 대조 ---
    desc = p.description
    urdf, urdf_err = _render_xacro(desc.urdf_package, desc.urdf_path,
                                   desc.urdf_args)
    if urdf_err:
        rep.add(V.ERROR, 'description.urdf', urdf_err)
    srdf, srdf_err = _render_xacro(desc.srdf_package, desc.srdf_path,
                                   desc.srdf_args)
    if srdf_err:
        rep.add(V.ERROR, 'description.srdf', srdf_err)
    rep.extend(V.validate_against_model(p, urdf_xml=urdf, srdf_xml=srdf))

    _check_planner_names(p, rep)

    # --- 실행 중 시스템 대조 (안 떠 있으면 건너뜀) ---
    if not args.offline:
        joints, actions, controllers = _collect_runtime(args.timeout)
        rep.extend(V.validate_against_runtime(
            p, joint_state_names=joints, action_names=actions,
            controller_names=controllers))

    print(rep.format())

    if not rep.ok:
        if args.promote:
            print('\n⛔ 오류가 있어 승격하지 않았습니다. 위 항목을 고친 뒤 다시 실행하세요.')
        return 1

    if p.is_verified:
        return 0

    if args.promote:
        return _promote(p)

    print(f'\n검증을 통과했습니다. `--promote` 를 붙이면 status 를 verified 로 '
          f'올려 전환할 수 있게 됩니다:\n'
          f'  binpick_model verify {p.name} --promote')
    return 0


def _promote(profile):
    """검증을 통과한 프로파일의 status 를 verified 로 올린다.

    ⚠ `yaml.safe_dump` 로 파일을 다시 쓰지 않는다. 프로파일의 주석은 "왜 이 값인지"
      를 담은 자산이라 통째로 날아가면 안 된다 → `status:` 한 줄만 치환한다.

    ⚠ 사람이 verify 없이 손으로 `verified` 를 적어 넣는 것을 막는 것이 이 명령의
      목적이다. 그래서 승격 경로는 여기 하나뿐이고, 반드시 0 오류 통과 뒤에만 온다.
    """
    path = profile.source_path
    if not path or not os.path.exists(path):
        print(f'⛔ 프로파일 파일을 찾을 수 없어 승격하지 못했습니다: {path}',
              file=sys.stderr)
        return 2

    # colcon 이 빌드 트리로 복사한 사본을 고치면 다음 빌드에 덮여 사라진다.
    if os.sep + 'build' + os.sep in path or os.sep + 'install' + os.sep in path:
        print(f'⚠ 이 파일은 빌드 산출물입니다: {path}')
        print('  여기를 고쳐도 다음 `colcon build` 에 덮어써집니다. '
              '소스 트리의 원본을 고친 뒤 다시 빌드하세요:')
        print('    src/bin_picking/bin_picking/robot_profiles/data/'
              f'{profile.name}.yaml')
        return 2

    with open(path, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    # 최상위 `status:` 는 들여쓰기 없는 줄이다(하위 키와 헷갈리지 않게).
    hits = [i for i, ln in enumerate(lines) if ln.startswith('status:')]
    if len(hits) != 1:
        print(f'⛔ 최상위 `status:` 줄을 정확히 하나 찾지 못했습니다({len(hits)}개) — '
              f'수동으로 고치세요: {path}', file=sys.stderr)
        return 2

    lines[hits[0]] = 'status: verified\n'
    tmp = path + '.tmp'
    with open(tmp, 'w', encoding='utf-8') as f:
        f.writelines(lines)
    os.replace(tmp, path)

    print(f'\n✅ status 를 verified 로 올렸습니다 — {path}')
    if not profile.task_validated:
        print('   ※ task_validated 는 false 그대로입니다. 안전 검증은 통과했지만 '
              '이 팔로 실제 작업을 성공시킨 기록은 아직 없다는 뜻입니다.')
    print(f'\n이제 전환할 수 있습니다:\n  binpick_model use {profile.name}')
    return 0


# =====================================================================
# use — 원클릭 전환
# =====================================================================
def cmd_use(args):
    try:
        p = robot_profiles.set_active(args.name, allow_draft=args.allow_draft)
    except robot_profiles.ProfileNotFound as exc:
        print(str(exc), file=sys.stderr)
        return 2
    except robot_profiles.ProfileError as exc:
        print(f'⛔ {exc}', file=sys.stderr)
        return 2

    print(f'활성 모델을 {p.name} ({p.display_name}) 로 바꿨습니다.')
    print(f'  저장 위치: {robot_profiles.active_model_file()}')
    if not p.is_verified:
        print('  ⚠ 이 모델은 미검증(draft)입니다 — --allow-draft 로 강제 전환했습니다.')
    env = os.environ.get(robot_profiles.ENV_MODEL, '').strip()
    if env and env != p.name:
        # 환경변수가 저장된 선택을 이깁니다. 이걸 안 알려주면 "바꿨는데 왜 안
        # 바뀌지"로 한참 헤맵니다.
        print(f'  ⚠ 그런데 이 셸에는 {robot_profiles.ENV_MODEL}={env!r} 가 설정돼 '
              f'있어 그쪽이 우선합니다. `unset {robot_profiles.ENV_MODEL}` 하세요.')
    print('\n이미 떠 있는 노드에는 적용되지 않습니다 — 런치를 다시 띄우세요:')
    print('  ros2 launch bin_picking desktop_integration_demo.launch.py')
    return 0


# =====================================================================
def build_parser():
    ap = argparse.ArgumentParser(
        prog='binpick_model',
        description='빈피킹 파이프라인의 로봇 모델 등록·검증·전환')
    sub = ap.add_subparsers(dest='cmd', required=True)

    sub.add_parser('list', help='등록된 모델과 검증 상태').set_defaults(
        func=cmd_list)

    p_show = sub.add_parser('show', help='프로파일 전체 내용 출력')
    p_show.add_argument('name')
    p_show.set_defaults(func=cmd_show)

    p_new = sub.add_parser('new', help='새 모델 등록용 뼈대 생성')
    p_new.add_argument('name', help='새 모델 이름(파일명이 된다)')
    p_new.add_argument('--template', default=robot_profiles.DEFAULT_MODEL,
                       help='뼈대로 삼을 기존 모델 (기본: %(default)s)')
    p_new.add_argument('--dir', default=None,
                       help='생성 위치 (기본: 사용자 프로파일 디렉터리)')
    p_new.add_argument('--force', action='store_true', help='기존 파일 덮어쓰기')
    p_new.set_defaults(func=cmd_new)

    p_val = sub.add_parser('validate', help='정적 검증 (로봇 없이)')
    p_val.add_argument('name')
    p_val.set_defaults(func=cmd_validate)

    p_ver = sub.add_parser(
        'verify', help='URDF/SRDF + 실행 중 시스템과 대조 (가장 강한 검증)')
    p_ver.add_argument('name')
    p_ver.add_argument('--offline', action='store_true',
                       help='실행 중 시스템 대조는 생략하고 URDF/SRDF 만 대조')
    p_ver.add_argument('--timeout', type=float, default=5.0,
                       help='실행 중 시스템 응답 대기(초, 기본 %(default)s)')
    p_ver.add_argument('--promote', action='store_true',
                       help='0 오류로 통과하면 status 를 verified 로 올린다 '
                            '(손으로 적어 넣는 것을 막는 유일한 승격 경로)')
    p_ver.set_defaults(func=cmd_verify)

    p_use = sub.add_parser('use', help='활성 모델 전환')
    p_use.add_argument('name')
    p_use.add_argument('--allow-draft', action='store_true',
                       help='미검증(draft) 모델로도 강제 전환 (권장하지 않음)')
    p_use.set_defaults(func=cmd_use)

    return ap


def main(argv=None):
    args = build_parser().parse_args(argv)
    return args.func(args)


if __name__ == '__main__':
    sys.exit(main())
