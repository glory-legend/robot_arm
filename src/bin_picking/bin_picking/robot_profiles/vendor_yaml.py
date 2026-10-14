# -*- coding: utf-8 -*-
"""벤더 YAML 관용 로더 — 커스텀 단위 태그를 SI 단위로 풀어 읽는다.

일부 벤더 설정은 순정 `yaml.safe_load` 로 못 읽는다. 예를 들어
`ur_description/config/ur5e/joint_limits.yaml` 은 이렇게 쓴다:

    max_position: !degrees  360.0

`!degrees` 는 YAML 표준이 아니라 **xacro 가 정의한 태그**다. safe_load 로 읽으면
`ConstructorError: could not determine a constructor for the tag '!degrees'` 로
죽는다 — 런치가 기동 도중 알 수 없는 이유로 넘어지는 셈이다.

여기서는 xacro 의 정의(`xacro/__init__.py` 의 `ConstructUnits`)를 그대로 옮겨
같은 변환 상수를 쓴다. **값을 다르게 해석하면 도(°)를 라디안으로 읽는 종류의
사고가 나므로, 상수는 반드시 xacro 와 일치해야 한다.**

모르는 태그는 조용히 넘기지 않는다. 값을 그냥 통과시키면 단위가 틀린 숫자가
파이프라인 깊숙이 흘러들어가 아무도 못 찾는다("침묵은 버그다") → 어떤 태그인지
밝히고 실패한다.
"""
import math

import yaml

# xacro 의 ConstructUnits 와 동일한 태그 → SI 기본단위 변환 상수.
# 각도의 기본단위는 라디안, 길이의 기본단위는 미터.
UNIT_TAGS = {
    '!radians': 1.0,
    '!degrees': math.pi / 180.0,
    '!meters': 1.0,
    '!millimeters': 0.001,
    '!foot': 0.3048,
    '!inches': 0.0254,
}


class VendorYamlError(ValueError):
    """벤더 YAML 을 안전하게 해석할 수 없다."""


class _VendorLoader(yaml.SafeLoader):
    """단위 태그를 아는 SafeLoader. 전역 SafeLoader 를 오염시키지 않는다."""


def _make_unit_constructor(factor):
    def _construct(loader, node):
        raw = loader.construct_scalar(node)
        try:
            return float(raw) * factor
        except (TypeError, ValueError):
            raise VendorYamlError(
                f'단위 태그 값을 숫자로 읽을 수 없다: {raw!r}')
    return _construct


for _tag, _factor in UNIT_TAGS.items():
    _VendorLoader.add_constructor(_tag, _make_unit_constructor(_factor))


def _unknown(loader, tag_suffix, node):
    raise VendorYamlError(
        f'알 수 없는 YAML 태그 {node.tag!r} — 이 값을 어떤 단위로 읽어야 할지 '
        f'알 수 없다. 아는 태그: {sorted(UNIT_TAGS)}. '
        f'값을 SI 단위(라디안/미터)로 바꿔 적거나 vendor_yaml.UNIT_TAGS 에 '
        f'변환 상수를 추가하세요.')


_VendorLoader.add_multi_constructor('', _unknown)


def load(path):
    """벤더 YAML 파일 하나를 읽는다. 단위 태그는 SI 로 변환된다."""
    with open(path, 'r', encoding='utf-8') as f:
        return loads(f.read(), where=path)


def loads(text, where='<string>'):
    """문자열에서 읽는다(테스트용)."""
    try:
        return yaml.load(text, Loader=_VendorLoader)
    except VendorYamlError as exc:
        raise VendorYamlError(f'{where}: {exc}')
    except yaml.YAMLError as exc:
        raise VendorYamlError(f'{where}: YAML 파싱 실패 — {exc}')
