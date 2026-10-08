"""3단 밀집 적재: 양방향 모서리 후보, 0/90° 회전, 다중 지지와 누적 하중.

제한된 다중 시작 탐색이며 전역 최적해를 보장하지 않는다. 접촉 면적에 비례한
하중 분배는 강체 박스의 정적 근사다. 로봇 실행 가능성은 별도 검증한다.
"""
from dataclasses import replace
import math
import random

from bin_picking.palletizing_planner import EPS, PackingPlan, Placement, plan_quality


def support_contacts(candidate, placed, min_ratio=0.90, edge_inset=0.006):
    """실제 박스 상면들의 겹침 면적. 서로 겹치지 않는 지지면만 합산한다."""
    if candidate.origin[2] < EPS:
        return ()
    rectangles = []
    for p in placed:
        if abs(p.origin[2] + p.size[2] - candidate.origin[2]) > 1e-7:
            continue
        lo = [max(p.origin[k], candidate.origin[k]) for k in (0, 1)]
        hi = [min(p.origin[k]+p.size[k], candidate.origin[k]+candidate.size[k]) for k in (0, 1)]
        if min(hi[k]-lo[k] for k in (0, 1)) > EPS:
            rectangles.append((p.box.box_id, lo, hi, (hi[0]-lo[0])*(hi[1]-lo[1])))
    area = sum(r[3] for r in rectangles)
    if area + EPS < min_ratio*candidate.size[0]*candidate.size[1]:
        return None
    # 90% 면적만으로 외곽 한쪽이 길게 돌출하는 것을 허용하지 않는다.
    # 각 모서리에서 6 mm 안쪽의 4점을 실제 지지면이 받쳐야 한다.
    for x in (candidate.origin[0]+min(edge_inset, candidate.size[0]/4),
              candidate.origin[0]+candidate.size[0]-min(edge_inset, candidate.size[0]/4)):
        for y in (candidate.origin[1]+min(edge_inset, candidate.size[1]/4),
                  candidate.origin[1]+candidate.size[1]-min(edge_inset, candidate.size[1]/4)):
            if not any(lo[0]-EPS <= x <= hi[0]+EPS and lo[1]-EPS <= y <= hi[1]+EPS
                       for _, lo, hi, _ in rectangles):
                return None
    return tuple((name, a/area) for name, _, _, a in rectangles)


def distributed_loads(placed):
    """상부 자중+전달 하중을 아래 방향 DAG로 한 번씩 전파한다."""
    loads = {p.box.box_id: 0.0 for p in placed}
    for p in reversed(placed):
        for name, share in p.support_shares:
            loads[name] += (p.box.weight_kg + loads[p.box.box_id])*share
    return loads


def _separated(a, b, gap):
    if a.origin[2]+a.size[2] <= b.origin[2]+EPS or b.origin[2]+b.size[2] <= a.origin[2]+EPS:
        return True
    return any(a.origin[k]+a.size[k]+gap <= b.origin[k]+EPS
               or b.origin[k]+b.size[k]+gap <= a.origin[k]+EPS for k in (0, 1))


def _pack(order, pallet_size, gap, max_layers, policy):
    placed, rejected = [], []
    for box in order:
        by_id = {p.box.box_id: p for p in placed}
        zs = sorted({0.0, *(round(p.origin[2]+p.size[2], 8) for p in placed)})
        candidates = []
        for yaw in box.orientations:
            size = box.size if yaw == 0 else (box.size[1], box.size[0], box.size[2])
            for z in zs:
                if z+size[2] > pallet_size[2]+EPS:
                    continue
                axes = [{0.0, round(pallet_size[k]-size[k], 8)} for k in (0, 1)]
                for p in placed:
                    if p.origin[2] <= z+size[2]+EPS and p.origin[2]+p.size[2] >= z-EPS:
                        for k in (0, 1):
                            axes[k].update(round(v, 8) for v in
                                (p.origin[k], p.origin[k]+p.size[k]-size[k],
                                 p.origin[k]+p.size[k]+gap, p.origin[k]-size[k]-gap))
                xs, ys = [sorted(v for v in axes[k] if -EPS <= v <= pallet_size[k]-size[k]+EPS)
                          for k in (0, 1)]
                for y in ys:
                    for x in xs:
                        p = Placement(box, (x, y, z), size, yaw, None)
                        if any(not _separated(p, other, gap) for other in placed):
                            continue
                        shares = support_contacts(p, placed)
                        if shares is None:
                            continue
                        layer = 1+max((by_id[name].layer for name, _ in shares), default=0)
                        if layer > max_layers:
                            continue
                        p = replace(p, support_id=shares[0][0] if shares else None,
                                    support_shares=shares, layer=layer)
                        loads = distributed_loads([*placed, p])
                        if any(loads[q.box.box_id] > q.box.max_load_kg+EPS for q in placed):
                            continue
                        # 좁은 잔여 띠를 줄이고 벽/기존 박스 옆에 맞춘다. 방향을 강제하지 않는다.
                        contacts = sum(size[1-k] for k in (0, 1)
                                       if p.origin[k] < EPS or abs(p.origin[k]+size[k]-pallet_size[k]) < EPS)
                        for other in placed:
                            if abs(other.origin[2]-z) > EPS:
                                continue
                            for k in (0, 1):
                                if min(abs(p.origin[k]+size[k]+gap-other.origin[k]),
                                       abs(other.origin[k]+other.size[k]+gap-p.origin[k])) < 1e-7:
                                    j = 1-k
                                    contacts += max(0, min(p.origin[j]+size[j], other.origin[j]+other.size[j])
                                                    -max(p.origin[j], other.origin[j]))
                        extent = (max([x+size[0]]+[q.origin[0]+q.size[0] for q in placed if abs(q.origin[2]-z)<EPS])
                                  *max([y+size[1]]+[q.origin[1]+q.size[1] for q in placed if abs(q.origin[2]-z)<EPS]))
                        if policy == 0:
                            score = (z, round(extent, 8), -round(contacts, 8), y, x, yaw)
                        else:
                            score = (z, -round(contacts, 8), round(extent, 8), y, x, yaw)
                        candidates.append((score, p))
        if candidates:
            placed.append(min(candidates, key=lambda v: v[0])[1])
        else:
            rejected.append(box.box_id)
    # 계획 탐색 중 먼저 찾은 상단보다, 모든 하단을 먼저 실행한다.
    placed.sort(key=lambda p: (p.origin[2], -p.origin[0], p.origin[1], p.box.box_id))
    return PackingPlan(tuple(pallet_size), tuple(placed), tuple(rejected), 'dense')


def dense_plan(boxes, pallet_size=(0.6, 0.4, 0.5), gap=0.003, max_layers=3, starts=8):
    boxes = list(boxes)
    if len(pallet_size) != 3 or not all(math.isfinite(v) and v > 0 for v in pallet_size):
        raise ValueError('pallet_size must contain three positive finite values')
    if len({b.box_id for b in boxes}) != len(boxes):
        raise ValueError('box_id must be unique')
    if not math.isfinite(gap) or gap < 0 or not isinstance(max_layers, int) or max_layers < 1 or starts < 1:
        raise ValueError('invalid gap/max_layers/starts')
    orders = [sorted(boxes, key=lambda b: (-b.size[2], -b.size[0]*b.size[1], b.box_id)),
              sorted(boxes, key=lambda b: (-b.size[0]*b.size[1], -b.size[2], b.box_id)),
              sorted(boxes, key=lambda b: (-math.prod(b.size), b.box_id)), boxes]
    rng = random.Random(31090)
    while len(orders) < starts:
        order = list(boxes)
        rng.shuffle(order)
        orders.append(order)
    plans = [_pack(order, pallet_size, gap, max_layers, i % 2) for i, order in enumerate(orders[:starts])]
    best = min(plans, key=plan_quality)
    return replace(best, candidate_count=len(plans))
