#!/usr/bin/env python3
"""회수 실행가능성 검증 시뮬레이터 — 물품 적재/회수 모델 + 물리 3항 게이트(G1·G2·G3).

특허 초안: docs/virtual_retrieval_patent_spec_draft_2026-09-09.md (청구항 1)
이 디렉토리는 기존 로봇암(src/bin_picking)과 **분리**된 실험 공간이나, 로봇의 실제
기하 엔진을 **재사용**한다:
  - G2(회수 경로 충돌)는 src/bin_picking/bin_picking/geometry.py 의
    GeometryMixin._seg_seg_dist / _ray_rect_travel 를 그대로 호출한다.
    (이 두 함수는 빈피킹 파지 개구 계산 = 선분–선분 거리 + 레이–사각형 벽거리와
     동일한 메커니즘으로, 회수 시 그리퍼·박스 스윕과 이웃 박스 간섭 판정에 재사용된다.)

모델(Block Relocation Problem + 상면 흡착 + 물리 게이트):
- 임시 적층부 = S개 스택(컬럼), 각 최대 높이 H. 박스는 스택에 위로 적층.
- 좌표: 스택 s의 중심 x = s·PITCH, 레벨 k(0=바닥)의 박스 상면 z = (k+1)·UNIT_H.
- 상면 흡착: 스택 맨 위 박스만 상면 노출 → 파지 가능(G1).
- 각 박스: id, 폭 width∈{1,2,3}(실폭 = width·W_UNIT), 중량, 외부 부여 회수순서(order).
"""
import os
import sys

import numpy as np

# ── 기존 로봇암 기하 엔진 로드(재사용) ─────────────────────────────
_HERE = os.path.dirname(os.path.abspath(__file__))
_BINPICK = os.path.normpath(os.path.join(_HERE, '..', '..', 'src', 'bin_picking'))
sys.path.insert(0, _BINPICK)
try:
    from bin_picking.geometry import GeometryMixin as _Geom
    SEG_SEG = _Geom._seg_seg_dist
    RAY_RECT = _Geom._ray_rect_travel
    GEOM_SOURCE = 'src/bin_picking/bin_picking/geometry.py:GeometryMixin'
except Exception as exc:                        # pragma: no cover
    raise RuntimeError(
        f'기존 로봇암 기하 엔진 로드 실패({exc!r}). '
        f'경로 확인: {_BINPICK}') from None

# ── 물리 치수 파라미터(로봇암 config 스케일 참고: 통·그리퍼 mm 단위) ──
W_UNIT = 0.10          # 폭 1단위 = 100mm
BOX_D = 0.20           # 박스 안쪽 깊이(y) = 200mm
UNIT_H = 0.15          # 적층 1단 높이 = 150mm
PITCH = 0.34           # 스택 중심 간격 = 340mm (폭 3단=300mm + 여유 40mm)
GRIP_CLEAR = 0.03      # 상면 흡착 그리퍼 몸체(흡착 패드+마운트)가 이웃 박스로부터
                       # 필요로 하는 최소 측면 여유 = 30mm. 흡착식이므로 박스는 그리퍼
                       # 아래에 매달려 상승 → 반출 스윕은 박스 형상 그대로(집게처럼
                       # 측면을 감싸 넓어지지 않음). (src/bin_picking 그리퍼 스케일 참고)
SUPPORT_RATIO = 0.6    # 위 박스가 아래 박스에 받쳐지는 최소 폭 비율(G3)


class Box:
    __slots__ = ('id', 'width', 'weight', 'order')

    def __init__(self, id, width, weight, order):
        self.id = id
        self.width = width
        self.weight = weight
        self.order = order

    def real_w(self):
        return self.width * W_UNIT

    def clone(self):
        return Box(self.id, self.width, self.weight, self.order)


class Buffer:
    def __init__(self, S, H, stacks=None):
        self.S = S
        self.H = H
        self.stacks = stacks if stacks is not None else [[] for _ in range(S)]

    def height(self, s):
        return len(self.stacks[s])

    def top(self, s):
        return self.stacks[s][-1] if self.stacks[s] else None

    def clone(self):
        return Buffer(self.S, self.H, [list(st) for st in self.stacks])


# ── 물리 3항 게이트 ────────────────────────────────────────────────
def g1_graspable(buf, s, idx):
    """G1: 상면 흡착 파지 가능 = 대상이 스택 맨 위여야 상면이 노출되어 흡착 패드가
    상면에 밀착할 수 있다. 위에 다른 박스가 있으면 상면이 덮여 흡착 불가(측면·하부
    대안 접근이 없는 상면 흡착식의 근본 제약)."""
    return idx == buf.height(s) - 1


def g2_path_clear(buf, s):
    """G2: 스택 s 맨 위 박스를 수직 반출할 때 이웃 스택과 충돌하지 않는가.
    기존 로봇암 _seg_seg_dist(대상 상승 수직 모서리 vs 이웃 상단 수평 모서리)로 판정."""
    h = buf.height(s)
    if h == 0:
        return True
    target = buf.stack_top_box(s) if hasattr(buf, 'stack_top_box') else buf.top(s)
    x_s = s * PITCH
    grasp_z = (h - 1) * UNIT_H          # 파지 시작(대상 박스 바닥)
    lift_z = buf.H * UNIT_H + UNIT_H    # 반출 최고점(버퍼 최상단 위로)
    tw = target.real_w()
    for adj in (s - 1, s + 1):
        if not (0 <= adj < buf.S):
            continue
        h_adj = buf.height(adj)
        if h_adj <= h:
            continue                    # 이웃이 대상보다 낮거나 같으면 상승 간섭 없음
        sign = 1 if adj > s else -1
        # 대상 박스의 이웃 쪽 수직 모서리(상승 경로)
        edge_x = x_s + sign * tw / 2.0
        p1 = (edge_x, 0.0, grasp_z)
        q1 = (edge_x, 0.0, lift_z)
        # 이웃 스택 맨 위 박스의 대상 쪽 상단 수평 모서리
        adj_box = buf.top(adj)
        aw = adj_box.real_w()
        adj_edge_x = adj * PITCH - sign * aw / 2.0
        adj_top_z = h_adj * UNIT_H
        p2 = (adj_edge_x, -BOX_D / 2.0, adj_top_z)
        q2 = (adj_edge_x, BOX_D / 2.0, adj_top_z)
        if SEG_SEG(p1, q1, p2, q2) < GRIP_CLEAR:
            return False
    return True


def g3_place_stable(buf, s, box):
    """G3(배치/재배치 목적지): box를 스택 s에 올릴 때 지지 안정성.
    넓은 박스를 좁은 박스 위에 올려 지지 폭 비율이 SUPPORT_RATIO 미만이면 불안정."""
    below = buf.top(s)
    if below is None:
        return True                     # 바닥은 항상 안정
    # 위 박스가 아래보다 넓으면 오버행. 아래폭/위폭 ≥ SUPPORT_RATIO 여야 지지.
    return (below.real_w() / box.real_w()) >= SUPPORT_RATIO if box.width > below.width else True


# Buffer에 top 박스 헬퍼(위 g2에서 참조)
Buffer.stack_top_box = lambda self, s: self.stacks[s][-1] if self.stacks[s] else None


def can_place(buf, s, box, use_g3):
    if buf.height(s) >= buf.H:
        return False
    if use_g3 and not g3_place_stable(buf, s, box):
        return False
    return True


def g2_after_place(buf, s):
    """box를 s에 올린 직후 그 박스의 반출 경로가 이웃과 간섭 없는지(사전 확인)."""
    trial = buf.clone()
    # 가상으로 한 칸 높였다고 보고 판정하기 위해, 높이 +1 상태의 top을 임시 사용
    # (실제 box는 호출 측에서 아직 안 올렸으므로, 높이만 기준으로 이웃 간섭 확인)
    h = buf.height(s) + 1
    x_s = s * PITCH
    for adj in (s - 1, s + 1):
        if not (0 <= adj < buf.S):
            continue
        if buf.height(adj) >= h:
            # 이웃이 새 박스보다 높으면 반출 시 간섭 가능 → _ray_rect_travel로 여유 확인
            # 새 박스 상면에서 이웃 방향으로 그리퍼가 빠질 여유
            sign = 1 if adj > s else -1
            # 이웃 벽까지 수평 여유가 GRIP_CLEAR 이상인지
            gap = PITCH - (W_UNIT * 3) / 2.0  # 최악(폭3) 기준 남는 수평 여유
            if gap < GRIP_CLEAR:
                return False
    return True


# ── 가상 회수 검증(T3 핵심, 청구항 1) ──────────────────────────────
def virtual_retrieval_ok(buf):
    """현재 버퍼 상태에서 부여 순서대로 재배치 없이 전량 회수 가능한가.
    매 단계 G1∧G2∧G3(맨 위 제거는 잔여 안정 자동)를 검사."""
    sim = buf.clone()
    orders = sorted(b.order for st in sim.stacks for b in st)
    for target in orders:
        loc = _find(sim, target)
        if loc is None:
            return False
        s, idx = loc
        if not g1_graspable(sim, s, idx):
            return False                # 위에 다른 박스 → 재배치 필요 → 후보 배제
        if not g2_path_clear(sim, s):
            return False
        sim.stacks[s].pop()             # 맨 위 제거(잔여 안정 자동)
    return True


def _find(buf, order):
    for s in range(buf.S):
        for idx, b in enumerate(buf.stacks[s]):
            if b.order == order:
                return (s, idx)
    return None


# ── 배치 전략 ──────────────────────────────────────────────────────
def choose_stack(strategy, buf, box):
    evals = 0
    cand = [s for s in range(buf.S) if buf.height(s) < buf.H]
    if not cand:
        return None, evals

    if strategy == 'T0':                         # 종래: 공간효율(최저 스택)
        return min(cand, key=lambda s: buf.height(s)), evals

    if strategy == 'T1':                         # 벌점(soft), 게이트 없음
        def pen(s):
            below = buf.top(s)
            p = 10 if (below is not None and below.order > box.order) else 0
            return (p, buf.height(s))
        return min(cand, key=pen), evals

    if strategy == 'T2':                         # G3(배치 안정성)만
        ok = [s for s in cand if can_place(buf, s, box, True)]
        evals += len(cand)
        return (min(ok or cand, key=lambda s: buf.height(s))), evals

    if strategy == 'T3':                         # 발명: 물리 3항 게이트 하 회수비용 최소 배치
        # 각 후보에 가상 배치 후, 부여 회수 순서로 가상 회수(evaluate_retrieval 재사용 =
        # G1∧G2∧G3 반영)하여 재배치·실패 비용을 계산하고 최소인 스택을 선택한다.
        # 안정성(G3) 통과 후보를 우선하되, 없으면 전체에서 최소 비용을 택한다(복구).
        def cost_if(s):
            trial = buf.clone()
            trial.stacks[s].append(box.clone())
            return retrieval_cost(trial)
        g3_ok = [s for s in cand if can_place(buf, s, box, True)]
        pool = g3_ok if g3_ok else cand
        evals += len(pool)
        best_s = min(pool, key=lambda s: (cost_if(s), buf.height(s)))
        return best_s, evals

    raise ValueError(strategy)


def _inversions(buf):
    """스택 내 '역전 쌍' 수 = 아래 박스를 먼저 꺼내야 하는데(order 작음) 그 위에 나중에
    꺼낼 박스(order 큼)가 얹힌 경우. 미래에 재배치를 유발할 잠재비용(online lookahead).
    아래 박스가 컨베이어에서 곧 도착할 나머지 박스로 더 묻히는 배치를 피하게 한다."""
    n = 0
    for st in buf.stacks:
        for i in range(len(st)):
            for j in range(i + 1, len(st)):
                if st[i].order < st[j].order:   # 아래(i)를 먼저 꺼내야 하는데 위(j)가 막음
                    n += 1
    return n


def retrieval_cost(buf):
    """버퍼를 부여 순서로 가상 회수했을 때의 비용.
    = 현재 알려진 박스의 재배치 + 실패×페널티 + 역전 쌍(미래 재배치 잠재비용)
      + 최고 스택 높이(회수 시 위 박스를 치울 여유 공간 확보 = 회수 실행가능성).
    마지막 항이 없으면 재배치만 줄이려 스택을 깊게 쌓아 회수 시 목적지 부족으로
    회수 실패가 늘어난다 — 발명의 '회수할 공간을 남기며 배치'를 반영한다.
    실제 회수 국면과 동일한 evaluate_retrieval 로직을 clone 위에서 돌린다."""
    reloc, fail = evaluate_retrieval(buf.clone())
    max_h = max((len(st) for st in buf.stacks), default=0)
    # 우선순위: 실패 회피(1e6) ≫ 먼저 꺼낼 박스 묻힘 방지(inv×50) > 실제 재배치 > 높이 여유
    return fail * 1_000_000 + _inversions(buf) * 50 + reloc + 1.5 * max_h


# ── 회수 국면 평가(모든 전략 공통, 표준 BRP) ───────────────────────
def _reloc_dest(buf, src, mv):
    """재배치 목적지 선택(모든 전략에 동일 고정 정책). src가 아닌 스택 중 가장 낮은 곳.
    임시 재배치는 곧 다시 꺼낼 이동이므로 G3(적층 안정성)를 목적지 제약으로 강제하지
    않는다(적재 배치에는 G3 유지). 높이 여유만 본다. 없으면 None(진짜 포화)."""
    best = None
    for d in range(buf.S):
        if d == src or buf.height(d) >= buf.H:
            continue
        if best is None or buf.height(d) < buf.height(best):
            best = d
    return best


def evaluate_retrieval(buf):
    """부여 순서대로 실제 회수. 재배치 횟수·회수 실패 건수 반환.
    표준 Block Relocation: 대상 위 박스를 다른 스택으로 옮긴 뒤 대상을 꺼낸다.
    옮길 스택이 없으면(버퍼 포화) 그 대상 회수 실패."""
    relocations = 0
    failures = 0
    orders = sorted(b.order for st in buf.stacks for b in st)
    for target in orders:
        loc = _find(buf, target)
        if loc is None:
            continue
        s, idx = loc
        blocked = False
        # 대상 위 박스들을 재배치
        while buf.height(s) - 1 > idx:
            mv = buf.top(s)
            dest = _reloc_dest(buf, s, mv)
            if dest is None:
                blocked = True
                break
            buf.stacks[dest].append(buf.stacks[s].pop())
            relocations += 1
        if blocked:
            failures += 1
            buf.stacks[s].pop()                 # 대상 강제 제거 후 다음 진행
            continue
        # 대상이 맨 위. G2(경로) 확인 후 회수
        if g2_path_clear(buf, s):
            buf.stacks[s].pop()
        else:
            # 경로가 이웃 스택 높이로 막힘 → 이웃을 낮추는 재배치 시도
            resolved = False
            for adj in (s - 1, s + 1):
                if not (0 <= adj < buf.S):
                    continue
                while buf.height(adj) > buf.height(s):
                    mv = buf.top(adj)
                    dest = _reloc_dest(buf, adj, mv)
                    if dest is None:
                        break
                    buf.stacks[dest].append(buf.stacks[adj].pop())
                    relocations += 1
                if g2_path_clear(buf, s):
                    resolved = True
                    break
            if resolved:
                buf.stacks[s].pop()
            else:
                failures += 1
                buf.stacks[s].pop()
    return relocations, failures
