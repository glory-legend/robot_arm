# -*- coding: utf-8 -*-
"""로봇 모델 프로파일 — 팔을 갈아끼우기 위한 등록/검증/전환 계층.

빈피킹 파이프라인은 원래 FR3 하나에 맞춰져 있었다. 업체마다 다른 값(관절 이름,
관절 한계, 그리퍼 지령 단위, 손끝 기하, 도달성 한계, MoveIt 설정 위치)이
`config.py` 의 클래스 상수로 굳어 있어, 다른 팔을 붙이려면 코드를 고쳐야 했다.

이 패키지는 그 값들을 **등록 가능한 데이터**로 바꾼다:

    schema.py    — 등록자가 무엇을 채워야 하는가 (필드 정의 + 자기모순 검사)
    registry.py  — 어디에 적힌 것을 등록으로 인정하는가 + 활성 모델 선택
    validator.py — 채워 넣은 값이 실제 로봇과 맞는가 (정적 + 라이브 대조)
    data/        — 내장 프로파일 (fr3.yaml)

사용:
    from bin_picking.robot_profiles import active_profile, get, names
"""
from bin_picking.robot_profiles.registry import (  # noqa: F401
    DEFAULT_MODEL,
    ENV_MODEL,
    ENV_PROFILE_PATH,
    ProfileNotFound,
    active_model_file,
    active_model_name,
    active_profile,
    discover,
    discover_errors,
    get,
    load_profile_file,
    names,
    search_dirs,
    set_active,
    user_profile_dir,
)
from bin_picking.robot_profiles.schema import (  # noqa: F401
    GRIPPER_ACTION_TYPES,
    GRIPPER_KINDS,
    STATUSES,
    ArmSpec,
    DescriptionSpec,
    GripperSpec,
    ProfileError,
    RobotProfile,
    WorkspaceSpec,
)

__all__ = [
    'DEFAULT_MODEL', 'ENV_MODEL', 'ENV_PROFILE_PATH',
    'ProfileError', 'ProfileNotFound',
    'RobotProfile', 'ArmSpec', 'GripperSpec', 'WorkspaceSpec', 'DescriptionSpec',
    'GRIPPER_KINDS', 'GRIPPER_ACTION_TYPES', 'STATUSES',
    'active_model_file', 'active_model_name', 'active_profile',
    'discover', 'discover_errors', 'get', 'load_profile_file', 'names',
    'search_dirs', 'set_active', 'user_profile_dir',
]
