# -*- coding: utf-8 -*-
"""등록된 로봇 모델 프로파일의 탐색·조회·활성 모델 선택 (순수, ROS 무의존).

**등록(registration)이 이 기능의 핵심이다.** 전환은 그 부산물일 뿐이다 — 업체마다
관절 이름부터 그리퍼 지령 단위까지 전부 다르고, 그 차이는 자동 추론이 불가능해
사람이 실측해 채워 넣어야 한다. 그래서 이 모듈이 하는 일은 "어디에 적힌 것을
등록으로 인정할 것인가"를 정하고, 그 결과를 한 곳에서 꺼내 주는 것뿐이다.

탐색 순서(뒤가 앞을 덮어쓴다):
  1. 내장 프로파일 — 이 패키지의 `data/*.yaml`
  2. 사용자 프로파일 — `~/.config/bin_picking/robot_profiles/*.yaml`
  3. `BIN_PICKING_PROFILE_PATH` (콜론 구분 디렉터리 목록)

같은 `name` 이 여러 곳에 있으면 **뒤에서 찾은 것이 이긴다** — 사용자가 내장
프로파일의 워크스페이스 실측값만 자기 설치 상태에 맞게 덮어쓰는 것이 정상적인
운용이기 때문이다. 어느 파일에서 왔는지는 `profile.source_path` 에 남는다.

활성 모델 결정 순서:
  1. `BIN_PICKING_ROBOT_MODEL` 환경변수 (런치/일회성 실행이 이걸 쓴다)
  2. `~/.config/bin_picking/active_model` 상태 파일 (`binpick_model use` 가 쓴다)
  3. `DEFAULT_MODEL` (= 'fr3')
"""
import os

import yaml

from bin_picking.robot_profiles.schema import ProfileError, RobotProfile

DEFAULT_MODEL = 'fr3'

ENV_MODEL = 'BIN_PICKING_ROBOT_MODEL'
ENV_PROFILE_PATH = 'BIN_PICKING_PROFILE_PATH'

_BUILTIN_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data')


class ProfileNotFound(KeyError):
    """요청한 이름의 프로파일이 등록돼 있지 않다."""

    def __init__(self, name, available):
        self.name = name
        self.available = list(available)
        super().__init__(
            f'등록되지 않은 로봇 모델: {name!r} — 등록된 모델: '
            f'{self.available or "(없음)"}. '
            f'`binpick_model list` 로 확인하고 `binpick_model new {name}` 으로 '
            f'새로 등록하세요.')

    def __str__(self):
        # KeyError.__str__ 은 인자를 repr 로 감싸 읽기 나쁘다 → 원문 그대로.
        return self.args[0]


def user_config_dir():
    """사용자 프로파일/활성모델 상태가 사는 디렉터리.

    XDG 를 존중하되 기본은 `~/.config/bin_picking`. 저장소 안이 아니라 홈에 두는
    이유는 `attempts.jsonl`/`selector_model.pkl` 과 같다 — 설치 상태에 따라 달라지는
    런타임 상태라 커밋 대상이 아니다.
    """
    base = os.environ.get('XDG_CONFIG_HOME') or os.path.expanduser('~/.config')
    return os.path.join(base, 'bin_picking')


def user_profile_dir():
    return os.path.join(user_config_dir(), 'robot_profiles')


def active_model_file():
    return os.path.join(user_config_dir(), 'active_model')


def search_dirs():
    """프로파일을 찾을 디렉터리들. 앞이 낮은 우선순위."""
    dirs = [_BUILTIN_DIR, user_profile_dir()]
    extra = os.environ.get(ENV_PROFILE_PATH, '')
    dirs.extend(p for p in extra.split(os.pathsep) if p.strip())
    return dirs


def load_profile_file(path):
    """YAML 파일 하나 → RobotProfile. 실패는 어느 파일인지 밝히고 던진다."""
    try:
        with open(path, 'r', encoding='utf-8') as f:
            raw = yaml.safe_load(f)
    except OSError as exc:
        raise ProfileError(f'{path}: 읽을 수 없다 — {exc}')
    except yaml.YAMLError as exc:
        raise ProfileError(f'{path}: YAML 파싱 실패 — {exc}')
    if raw is None:
        raise ProfileError(f'{path}: 파일이 비어 있다')
    try:
        return RobotProfile.from_dict(raw, source_path=path)
    except ProfileError as exc:
        # 어느 파일의 어느 필드인지가 한 줄에 다 보이게 재포장한다.
        raise ProfileError(f'{path}: {exc}')


def discover(strict=False):
    """등록된 모든 프로파일을 {name: RobotProfile} 로.

    `strict=False`(기본)면 깨진 파일 하나가 나머지 전체를 못 쓰게 만들지 않는다 —
    대신 깨진 파일은 `discover_errors()` 로 따로 보고된다. `binpick_model list` 가
    그 둘을 함께 보여 주므로 오류가 조용히 묻히지는 않는다.
    `strict=True` 면 첫 오류에서 즉시 던진다(검증 명령이 쓴다).
    """
    found, _ = _discover_with_errors(strict)
    return found


def discover_errors():
    """깨져서 등록되지 못한 파일들 → [(경로, 오류메시지)]."""
    _, errors = _discover_with_errors(strict=False)
    return errors


def _discover_with_errors(strict):
    found = {}
    errors = []
    for d in search_dirs():
        if not os.path.isdir(d):
            continue
        for fname in sorted(os.listdir(d)):
            if not fname.endswith(('.yaml', '.yml')):
                continue
            path = os.path.join(d, fname)
            try:
                profile = load_profile_file(path)
            except ProfileError as exc:
                if strict:
                    raise
                errors.append((path, str(exc)))
                continue
            found[profile.name] = profile
    return found, errors


def names():
    """등록된 모델 이름 목록(정렬)."""
    return sorted(discover().keys())


def get(name):
    """이름으로 프로파일 조회. 없으면 ProfileNotFound."""
    found = discover()
    if name not in found:
        raise ProfileNotFound(name, sorted(found))
    return found[name]


def active_model_name():
    """지금 어떤 모델이 활성인가 (파일/환경변수만 보고 결정 — 로딩은 안 한다)."""
    env = os.environ.get(ENV_MODEL, '').strip()
    if env:
        return env
    path = active_model_file()
    try:
        with open(path, 'r', encoding='utf-8') as f:
            saved = f.read().strip()
    except OSError:
        saved = ''
    return saved or DEFAULT_MODEL


def active_profile():
    """활성 모델의 프로파일. 등록돼 있지 않으면 ProfileNotFound."""
    return get(active_model_name())


def set_active(name, allow_draft=False):
    """활성 모델을 바꾼다 — 원클릭 전환의 실제 구현부.

    ⚠ 등록되지 않았거나 아직 검증되지 않은(`status: draft`) 모델로는 전환하지
      않는다. 검증 전 모델로 로봇을 움직이면 관절 한계·그리퍼 지령 단위가 틀린
      채로 실행되어 실물에서는 충돌·과주행로 직결된다. 굳이 넘기려면 호출자가
      `allow_draft=True` 를 명시해야 한다(검증 작업 자체를 위해 필요하다).

    ※ 이 게이트는 **안전 검증**만 본다. 작업 성능(`task_validated`)이 false 여도
      전환은 허용된다 — "안전하게 로드는 되지만 이 작업엔 아직 안 맞는 팔"은
      정상적인 상태이고, 그걸 막을 이유는 없다.

    반환: 전환된 RobotProfile.
    """
    profile = get(name)          # 미등록이면 여기서 ProfileNotFound
    if not profile.is_verified and not allow_draft:
        raise ProfileError(
            f'{name!r} 은 아직 검증되지 않았다(status: {profile.status}) — '
            f'`binpick_model verify {name} --promote` 로 실제 모델/런타임과 대조해 '
            f'통과시키면 status 가 verified 로 올라간다. '
            f'({profile.source_path})')
    path = active_model_file()
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + '.tmp'
    with open(tmp, 'w', encoding='utf-8') as f:
        f.write(profile.name + '\n')
    os.replace(tmp, path)        # 원자적 교체 — 읽는 쪽이 반쪽 파일을 못 본다
    return profile
