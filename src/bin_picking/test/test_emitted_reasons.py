# -*- coding: utf-8 -*-
"""방출 reason 드리프트 회귀 테스트 (ROS/rclpy 무의존 — AST 정적 분석만).

`pick_place_node.py::_pick()` 가 실제로 발행하는 실패 reason 문자열 집합과
`protocol.py::FAIL_REASON_MAP` 의 키가 **정확히 일치**하는지 검사한다.

왜 필요한가 (BP-C02): 리프트 실패 분기가 `descend_fail` 로 잘못 기록되던 버그가
있었다 — 매핑표에는 `lift_fail` 이 있는데 코드가 방출하지 않아, 표의 키와 실코드가
서로 다른 사건을 가리켰다. 단순히 표를 검증하는 테스트로는 "표에는 있지만 아무도
방출하지 않는 죽은 키"를 잡지 못한다. 그래서 여기서는 코드를 AST 로 파싱해 실제
방출되는 reason 리터럴을 뽑고, 표와 **양방향**으로 대조한다.

이 테스트는 `pick_place_node.py` 를 import 하지 않는다(그러면 rclpy/MoveIt 가
딸려와 Gazebo 없이는 못 돈다). 파일을 텍스트로 읽어 `ast` 로만 분석한다.
"""
import ast
from pathlib import Path

from bin_picking import protocol


# reason 문자열이지만 '실패' 사유가 아닌 것 — _log_attempt 의 성공 라벨.
_NON_FAIL_REASONS = {'success'}

_NODE_SRC = (
    Path(__file__).resolve().parent.parent / 'bin_picking' / 'pick_place_node.py'
)


def _collect_emitted_reasons():
    """pick_place_node.py 에서 방출되는 reason 문자열 리터럴을 AST 로 수집.

    출처 두 곳:
      1) `self._log_attempt(key, feat, label, reason, ...)` — 4번째 인자(idx 3).
         reason 이 문자열 상수일 때만(변수 `reason` 은 아래 fail() 정의에서 잡힘).
      2) 지역 `fail(msg, reason, ...)` 호출 — 2번째 인자(idx 1) 또는 `reason=` 키워드.
         `_drop()` 의 `fail(msg)` 는 인자가 하나뿐이라 아무것도 기여하지 않는다.
      3) `def fail(..., reason='abort', ...)` 의 기본값 — msg 만 넘겨 호출되는 경우 대비.
    """
    tree = ast.parse(_NODE_SRC.read_text(encoding='utf-8'), filename=str(_NODE_SRC))
    reasons = set()

    def _add_if_str(node):
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            reasons.add(node.value)

    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            func = node.func
            # 1) *._log_attempt(...) 의 4번째 위치 인자
            if isinstance(func, ast.Attribute) and func.attr == '_log_attempt':
                if len(node.args) >= 4:
                    _add_if_str(node.args[3])
            # 2) fail(...) 의 2번째 위치 인자 / reason= 키워드
            elif isinstance(func, ast.Name) and func.id == 'fail':
                if len(node.args) >= 2:
                    _add_if_str(node.args[1])
                for kw in node.keywords:
                    if kw.arg == 'reason':
                        _add_if_str(kw.value)
        # 3) def fail(..., reason=<default>, ...) 의 기본값
        elif isinstance(node, ast.FunctionDef) and node.name == 'fail':
            a = node.args
            names = [arg.arg for arg in a.args]
            defaults = a.defaults
            # 뒤에서부터 정렬: 마지막 len(defaults) 개 파라미터가 기본값을 가진다.
            for name, default in zip(names[len(names) - len(defaults):], defaults):
                if name == 'reason':
                    _add_if_str(default)

    return reasons - _NON_FAIL_REASONS


def test_pick_place_node_source_found():
    assert _NODE_SRC.exists(), f'대상 소스 없음: {_NODE_SRC}'


def test_emitted_reasons_are_all_mapped():
    """방출되는 모든 실패 reason 은 FAIL_REASON_MAP 에 매핑돼 있어야 한다.

    미매핑 시 desktop_bridge 가 UNKNOWN 을 내보내 데스크톱이 사유를 잃는다.
    """
    emitted = _collect_emitted_reasons()
    mapped = set(protocol.FAIL_REASON_MAP)
    missing = emitted - mapped
    assert not missing, f'매핑표에 없는 방출 reason: {sorted(missing)}'


def test_no_dead_map_entries():
    """FAIL_REASON_MAP 의 모든 키는 실제로 코드에서 방출돼야 한다(죽은 키 금지).

    이게 BP-C02 회귀의 핵심 가드다 — `lift_fail` 이 표에만 있고 방출되지 않던
    상태를 실패로 만든다.
    """
    emitted = _collect_emitted_reasons()
    mapped = set(protocol.FAIL_REASON_MAP)
    dead = mapped - emitted
    assert not dead, f'방출되지 않는 죽은 매핑 키: {sorted(dead)}'


def test_lift_fail_is_emitted():
    """BP-C02 직접 회귀: 리프트 실패는 lift_fail 로 기록돼야 한다."""
    emitted = _collect_emitted_reasons()
    assert 'lift_fail' in emitted, 'lift_fail 이 방출되지 않는다(리프트 실패 오기록 회귀)'
