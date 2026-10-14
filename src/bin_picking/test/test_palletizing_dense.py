from dataclasses import replace
from itertools import combinations

import pytest

from bin_picking.palletizing_dense import dense_plan, distributed_loads, support_contacts
from bin_picking.palletizing_planner import BoxSpec, Placement, demo_boxes, overlaps


def test_rotation_increases_capacity_over_fixed_orientation():
    # 3x2 직사각형 다섯 개는 6x5 판을 서로 다른 방향으로 빈틈없이 채운다.
    boxes = [BoxSpec(str(i), (.3, .2, .1), 1) for i in range(5)]
    p = dense_plan(boxes, (.6, .5, .1), gap=0, max_layers=1, starts=4)
    fixed = dense_plan([replace(b, orientations=(0,)) for b in boxes],
                       (.6, .5, .1), gap=0, max_layers=1, starts=4)
    assert len(p.placements) == 5 > len(fixed.placements)
    assert {q.yaw_deg for q in p.placements} == {0, 90}


def test_multi_support_bridge_and_shared_load_limits():
    a = Placement(BoxSpec('a', (.1, .2, .1), 1, .6), (0, 0, 0), (.1, .2, .1), 0, None)
    b = replace(a, box=replace(a.box, box_id='b'), origin=(.1, 0, 0))
    upper = Placement(BoxSpec('c', (.2, .2, .1), 1), (0, 0, .1), (.2, .2, .1), 0, None)
    shares = support_contacts(upper, [a, b])
    assert dict(shares) == pytest.approx({'a': .5, 'b': .5})
    upper = replace(upper, support_shares=shares, layer=2)
    top = replace(upper, box=replace(upper.box, box_id='d'), origin=(0, 0, .2),
                  support_shares=(('c', 1.0),), layer=3)
    assert distributed_loads([a, b, upper, top]) == pytest.approx({'a': 1, 'b': 1, 'c': 1, 'd': 0})
    assert support_contacts(upper, [a]) is None
    assert support_contacts(replace(upper, origin=(.025, 0, .1)), [a, b]) is None


def test_dense_obeys_load_and_layer_limits():
    boxes = [BoxSpec(str(i), (.1, .1, .1), 1, 1.5) for i in range(4)]
    p = dense_plan(boxes, (.1, .1, .5), gap=0, starts=2)
    assert len(p.placements) == 2 and len(p.rejected) == 2
    p = dense_plan([replace(b, max_load_kg=10) for b in boxes], (.1, .1, .5), gap=0, starts=2)
    assert len(p.placements) == 3 and len(p.rejected) == 1
    assert max(q.layer for q in p.placements) == 3


def test_default_dense_plan_has_three_tiers_mixed_rotation_and_true_support():
    from bin_picking.palletizing_cell import motion_plan
    p, jobs = motion_plan()
    assert len(jobs) == 36 and not p.rejected
    baseline, _ = motion_plan(box_count=36, strategy='compact')
    assert not baseline.rejected
    assert p.to_dict()['metrics']['used_height_m'] < baseline.to_dict()['metrics']['used_height_m']
    assert baseline.to_dict()['metrics']['layers'] == 4
    assert {q.layer for q in p.placements} == {1, 2, 3}
    assert {q.yaw_deg for q in p.placements} == {0, 90}
    previous = []
    for q in p.placements:
        assert all(q.origin[k] >= 0 and q.origin[k]+q.size[k] <= p.pallet_size[k]+1e-8 for k in range(3))
        assert support_contacts(q, previous) is not None
        assert all(name in {r.box.box_id for r in previous} for name, _ in q.support_shares)
        previous.append(q)
    for a, b in combinations(p.placements, 2):
        assert not overlaps(a, b)
        if a.origin[2]+a.size[2] > b.origin[2]+1e-8 and b.origin[2]+b.size[2] > a.origin[2]+1e-8:
            assert max(max(a.origin[k]-b.origin[k]-b.size[k], b.origin[k]-a.origin[k]-a.size[k])
                       for k in (0, 1)) >= .003-1e-8
    loads = distributed_loads(p.placements)
    assert all(loads[q.box.box_id] <= q.box.max_load_kg+1e-8 for q in p.placements)


def test_dense_is_reproducible_and_accounts_for_overflow():
    boxes = demo_boxes(box_count=12)
    a = dense_plan(boxes, (.3, .2, .3), starts=3)
    assert a == dense_plan(boxes, (.3, .2, .3), starts=3)
    assert len(a.placements)+len(a.rejected) == len(boxes)
    assert set(q.box.box_id for q in a.placements).isdisjoint(a.rejected)
    assert a.rejected
