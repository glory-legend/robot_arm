"""PDF §12 1단계: 혼합 박스 3종의 오프라인 팔레트 배치(ROS 무의존).

입력 순서대로 extreme-point 후보와 0/90도 회전을 검사하는 greedy 기준선이다.
경계·겹침·상면 지지·지지물 허용하중을 검사한다. 로봇 IK/모션 검증이나
바코드/출고 순서 정책은 아직 포함하지 않는다(PDF의 후속 단계).
"""
from dataclasses import asdict, dataclass
import json
import math
import random


EPS = 1e-9


@dataclass(frozen=True)
class BoxSpec:
    box_id: str
    size: tuple[float, float, float]  # m
    weight_kg: float
    max_load_kg: float = 5.0        # 실측값이 아닌 데모 입력
    orientations: tuple[int, ...] = (0, 90)

    def __post_init__(self):
        if len(self.size) != 3 or not all(math.isfinite(v) and v > 0 for v in self.size):
            raise ValueError('box dimensions must be three positive finite values')
        if not math.isfinite(self.weight_kg) or self.weight_kg <= 0:
            raise ValueError('weight_kg must be positive and finite')
        if not math.isfinite(self.max_load_kg) or self.max_load_kg < 0:
            raise ValueError('max_load_kg must be nonnegative and finite')
        if not self.orientations or any(o not in (0, 90) for o in self.orientations):
            raise ValueError('orientations must contain only 0/90 degrees')


@dataclass(frozen=True)
class Placement:
    box: BoxSpec
    origin: tuple[float, float, float]  # 팔레트 상면의 왼쪽 아래 모서리 기준
    size: tuple[float, float, float]    # 회전 후 world 축 방향 치수
    yaw_deg: int
    support_id: str | None
    support_shares: tuple[tuple[str, float], ...] = ()
    layer: int = 1


@dataclass(frozen=True)
class PackingPlan:
    pallet_size: tuple[float, float, float]
    placements: tuple[Placement, ...]
    rejected: tuple[str, ...]
    strategy: str = 'greedy'
    candidate_count: int = 1

    def to_dict(self):
        data = asdict(self)
        volume = sum(math.prod(p.size) for p in self.placements)
        used_height = max((p.origin[2] + p.size[2] for p in self.placements), default=0)
        data['metrics'] = {
            'placed': len(self.placements), 'rejected': len(self.rejected),
            'used_height_m': used_height,
            'capacity_utilization': volume / math.prod(self.pallet_size),
            'used_height_utilization': (
                volume / (self.pallet_size[0] * self.pallet_size[1] * used_height)
                if used_height else 0.0),
            'layers': max((p.layer for p in self.placements), default=0),
            'rotated_boxes': sum(p.yaw_deg == 90 for p in self.placements),
        }
        data['validation'] = 'geometry_only; robot IK, execution and verification pending'
        return data


def overlaps(a, b):
    """접촉은 허용하고 양의 부피 교차만 충돌로 판정한다."""
    return all(a.origin[k] < b.origin[k] + b.size[k] - EPS
               and b.origin[k] < a.origin[k] + a.size[k] - EPS for k in range(3))


def _support(candidate, placed):
    # 데모 첫 단계는 하나의 하부 박스가 바닥 전체를 지지하는 경우만 허용한다.
    # 다중 박스에 걸친 bridge/부분 지지의 하중 분배를 임의로 가정하지 않는다.
    for p in placed:
        if abs(p.origin[2] + p.size[2] - candidate.origin[2]) > EPS:
            continue
        if all(candidate.origin[k] >= p.origin[k] - EPS
               and candidate.origin[k] + candidate.size[k] <= p.origin[k] + p.size[k] + EPS
               for k in (0, 1)):
            return p.box.box_id
    return None


def _load_ok(support_id, box, placed):
    by_id = {p.box.box_id: p for p in placed}
    loads = {p.box.box_id: 0.0 for p in placed}
    for p in placed:
        ancestor = p.support_id
        while ancestor is not None:
            loads[ancestor] += p.box.weight_kg
            ancestor = by_id[ancestor].support_id
    ancestor = support_id
    while ancestor is not None:
        if loads[ancestor] + box.weight_kg > by_id[ancestor].box.max_load_kg + EPS:
            return False
        ancestor = by_id[ancestor].support_id
    return True


def pack_boxes(boxes, pallet_size=(0.6, 0.4, 0.5)):
    """최저 높이→작은 점유 외곽→좌표 순으로 결정. 배치 불가는 rejected에 남긴다."""
    if len(pallet_size) != 3 or not all(math.isfinite(v) and v > 0 for v in pallet_size):
        raise ValueError('pallet_size must contain three positive finite values')
    boxes = list(boxes)
    if len({b.box_id for b in boxes}) != len(boxes):
        raise ValueError('box_id must be unique')
    placed, rejected = [], []
    for box in boxes:
        axes = [{0.0} for _ in range(3)]
        for p in placed:
            for k in range(3):
                axes[k].update((p.origin[k], p.origin[k] + p.size[k]))
        candidates = []
        for yaw in box.orientations:
            size = box.size if yaw == 0 else (box.size[1], box.size[0], box.size[2])
            for z in sorted(axes[2]):
                for y in sorted(axes[1]):
                    for x in sorted(axes[0]):
                        origin = (x, y, z)
                        if any(origin[k] + size[k] > pallet_size[k] + EPS for k in range(3)):
                            continue
                        candidate = Placement(box, origin, size, yaw, None)
                        if any(overlaps(candidate, p) for p in placed):
                            continue
                        support = _support(candidate, placed) if z > EPS else None
                        if z > EPS and support is None:
                            continue
                        if not _load_ok(support, box, placed):
                            continue
                        layer = 1+next((p.layer for p in placed if p.box.box_id == support), 0)
                        candidate = Placement(box, origin, size, yaw, support,
                                              ((support, 1.0),) if support else (), layer)
                        area = (max([x + size[0]] + [p.origin[0] + p.size[0] for p in placed])
                                * max([y + size[1]] + [p.origin[1] + p.size[1] for p in placed]))
                        candidates.append(((z + size[2], area, y, x, yaw), candidate))
        if candidates:
            placed.append(min(candidates, key=lambda entry: entry[0])[1])
        else:
            rejected.append(box.box_id)
    return PackingPlan(tuple(pallet_size), tuple(placed), tuple(rejected))


def plan_quality(plan):
    """작을수록 좋다: 누락 수 → 누락 부피 → 적재 높이 → 질량의 높이 모멘트.

    같은 개수면 더 많은 물량을 수용하고, 같은 물량이면 낮고 무거운 박스가 아래인
    배치를 선호한다. 모두 오프라인 기하 지표이며 실행 성공률의 대체 지표는 아니다.
    """
    volume = sum(math.prod(p.size) for p in plan.placements)
    height = max((p.origin[2] + p.size[2] for p in plan.placements), default=0.0)
    mass_height = sum(p.box.weight_kg * (p.origin[2] + p.size[2] / 2)
                      for p in plan.placements)
    return (len(plan.rejected), -round(volume, 10), round(height, 10), round(mass_height, 10))


def plan_boxes(boxes, pallet_size=(0.6, 0.4, 0.5), strategy='compact'):
    """여러 오프라인 입력 우선순위를 비교하는 compact 전략.

    Greedy 결과도 후보에 포함하므로 위 품질 순서에서 기준선보다 나빠지지 않는다.
    이는 전체 입력을 아는 1단계 전용이다. 온라인 dispatcher에서 출고 순서를
    마음대로 바꾸는 용도로 재사용하면 안 된다.
    """
    boxes = list(boxes)
    if strategy == 'dense':
        from bin_picking.palletizing_dense import dense_plan
        return dense_plan(boxes, pallet_size, starts=128)
    if strategy == 'greedy':
        return pack_boxes(boxes, pallet_size)
    if strategy != 'compact':
        raise ValueError(f'unknown packing strategy: {strategy}')
    orders = [boxes]
    for key in (
        lambda b: (-b.size[0]*b.size[1], -b.weight_kg, -b.size[2]),
        lambda b: (-math.prod(b.size), -b.weight_kg),
        lambda b: (-b.weight_kg, -b.size[0]*b.size[1]),
        lambda b: (b.size[2], -b.size[0]*b.size[1], -b.weight_kg),
    ):
        orders.append(sorted(boxes, key=key))
    seen, plans = set(), []
    for order in orders:
        signature = tuple(b.box_id for b in order)
        if signature not in seen:
            seen.add(signature)
            plans.append(pack_boxes(order, pallet_size))
    best = min(plans, key=plan_quality)
    return PackingPlan(best.pallet_size, best.placements, best.rejected,
                       strategy='compact', candidate_count=len(plans))


def demo_boxes(seed=20260909, box_count=12):
    """3종·허용 방향·허용하중은 1단계용 모사 입력(실물 카탈로그 수치 아님)."""
    if not 1 <= box_count <= 60:
        raise ValueError('box_count must be 1..60')
    kinds = [((0.12, 0.08, 0.06), 0.4),
             ((0.16, 0.10, 0.08), 0.7),
             ((0.20, 0.12, 0.10), 1.0)]
    sequence = [kinds[i % 3] for i in range(box_count)]
    random.Random(seed).shuffle(sequence)
    return [BoxSpec(f'pallet_box_{i}', size, weight)
            for i, (size, weight) in enumerate(sequence)]


def main():
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--seed', type=int, default=20260909)
    parser.add_argument('--box-count', type=int, default=12)
    parser.add_argument('--strategy', choices=('greedy', 'compact', 'dense'), default='compact')
    args = parser.parse_args()
    print(json.dumps(plan_boxes(demo_boxes(args.seed, args.box_count),
                               strategy=args.strategy).to_dict(), indent=2))


if __name__ == '__main__':
    main()
