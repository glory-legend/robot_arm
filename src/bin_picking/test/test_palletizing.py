"""PDF 1단계: 배치 불변조건과 Gazebo/계획 장면의 치수 일치 검증."""
from itertools import combinations
import math
import xml.etree.ElementTree as ET

import pytest

from bin_picking.palletizing_layout import PALLET, body_sdf, make_layout
from bin_picking.palletizing_planner import BoxSpec, demo_boxes, pack_boxes, plan_boxes, plan_quality


def test_rotation_is_required_to_fit():
    box = BoxSpec('rotated', (0.2, 0.3, 0.1), 1.0)
    plan = pack_boxes([box], (0.3, 0.2, 0.1))
    assert plan.placements[0].yaw_deg == 90
    assert not plan.rejected
    fixed = BoxSpec('fixed', box.size, 1.0, orientations=(0,))
    assert pack_boxes([fixed], (0.3, 0.2, 0.1)).rejected == ('fixed',)


def test_oversize_and_unsupported_boxes_are_not_silently_placed():
    boxes = [BoxSpec('small', (0.1, 0.1, 0.1), 1.0),
             BoxSpec('overhang', (0.2, 0.2, 0.1), 1.0),
             BoxSpec('oversize', (0.3, 0.3, 0.1), 1.0)]
    plan = pack_boxes(boxes, (0.2, 0.2, 0.3))
    assert [p.box.box_id for p in plan.placements] == ['small']
    assert plan.rejected == ('overhang', 'oversize')


def test_load_limit_includes_all_descendants():
    boxes = [BoxSpec('bottom', (0.1, 0.1, 0.1), 1.0, max_load_kg=1.5),
             BoxSpec('middle', (0.1, 0.1, 0.1), 1.0),
             BoxSpec('top', (0.1, 0.1, 0.1), 1.0)]
    plan = pack_boxes(boxes, (0.1, 0.1, 0.5))
    assert len(plan.placements) == 2
    assert plan.placements[1].support_id == 'bottom'
    assert plan.rejected == ('top',)


@pytest.mark.parametrize('seed', range(10))
@pytest.mark.parametrize('strategy', ['greedy', 'compact'])
def test_seeded_plans_preserve_geometry_and_account_for_every_box(seed, strategy):
    boxes = demo_boxes(seed, 24)
    plan = plan_boxes(boxes, strategy=strategy)
    assert plan == plan_boxes(boxes, strategy=strategy)
    assert plan_quality(plan) <= plan_quality(pack_boxes(boxes))
    assert set(p.box.box_id for p in plan.placements) | set(plan.rejected) == set(b.box_id for b in boxes)
    by_id = {p.box.box_id: p for p in plan.placements}
    for p in plan.placements:
        assert all(p.origin[k] >= 0 and p.origin[k] + p.size[k] <= plan.pallet_size[k] + 1e-8
                   for k in range(3))
        if p.origin[2] > 0:
            support = by_id[p.support_id]
            assert p.origin[2] == pytest.approx(support.origin[2] + support.size[2])
            assert all(p.origin[k] >= support.origin[k] - 1e-8 and
                       p.origin[k] + p.size[k] <= support.origin[k] + support.size[k] + 1e-8
                       for k in (0, 1))
    for a, b in combinations(plan.placements, 2):
        intersection = [min(a.origin[k] + a.size[k], b.origin[k] + b.size[k])
                        - max(a.origin[k], b.origin[k]) for k in range(3)]
        assert min(intersection) <= 1e-8


def test_world_layout_and_sdf_preserve_plan_geometry():
    bodies = make_layout()
    plan = plan_boxes(demo_boxes())
    assert PALLET.size[:2] == (0.6, 0.4)  # PDF §10, mm → m
    assert len(bodies) == 13
    for body, placement in zip(bodies[1:], plan.placements):
        root = ET.fromstring(body_sdf(body))
        collision = root.find('model/link/collision/geometry/box/size')
        assert tuple(map(float, collision.text.split())) == placement.size
        pose = tuple(map(float, root.find('model/pose').text.split()))[:3]
        expected = (0.2 + placement.origin[0] + placement.size[0] / 2,
                    -0.2 + placement.origin[1] + placement.size[1] / 2,
                    0.04 + placement.origin[2] + placement.size[2] / 2)
        assert pose == pytest.approx(expected)
        assert float(root.find('model/link/inertial/mass').text) == placement.box.weight_kg


@pytest.mark.parametrize('size', [(0, 1, 1), (-1, 1, 1), (math.nan, 1, 1), (math.inf, 1, 1)])
def test_invalid_geometry_is_rejected(size):
    with pytest.raises(ValueError):
        BoxSpec('invalid', size, 1)
    with pytest.raises(ValueError):
        pack_boxes([], size)


def test_duplicate_ids_rejected():
    box = BoxSpec('duplicate', (0.1, 0.1, 0.1), 1)
    with pytest.raises(ValueError, match='unique'):
        pack_boxes([box, box])


def test_compact_improves_default_height_without_losing_boxes():
    boxes = demo_boxes()
    greedy = plan_boxes(boxes, strategy='greedy')
    compact = plan_boxes(boxes, strategy='compact')
    assert not greedy.rejected and not compact.rejected
    assert greedy.to_dict()['metrics']['used_height_m'] == pytest.approx(0.16)
    assert compact.to_dict()['metrics']['used_height_m'] == pytest.approx(0.10)


@pytest.mark.parametrize('seed', range(5))
def test_motion_layout_reserves_clearance_and_preserves_box_geometry(seed):
    from bin_picking.palletizing_cell import PALLET as cell_pallet, motion_plan
    plan, jobs = motion_plan(seed, 6, 'compact')
    assert len(jobs) == 6 and not plan.rejected
    specs = {b.box_id: b for b in demo_boxes(seed, 6)}
    placed = []
    for box, target, yaw in jobs:
        assert box.size == specs[box.name].size
        assert box.mass == specs[box.name].weight_kg
        size = box.size if yaw == 0 else (box.size[1], box.size[0], box.size[2])
        for k in (0, 1):
            assert abs(target[k]-cell_pallet.position[k])+size[k]/2 <= cell_pallet.size[k]/2 + 1e-9
        assert target[2]-size[2]/2 >= 0.14 - 1e-9
        placed.append((target, size))
    for (a, sa), (b, sb) in combinations(placed, 2):
        if min(a[2]+sa[2]/2, b[2]+sb[2]/2) > max(a[2]-sa[2]/2, b[2]-sb[2]/2)+1e-9:
            assert max(abs(a[k]-b[k])-(sa[k]+sb[k])/2 for k in (0, 1)) >= 0.012 - 1e-9
