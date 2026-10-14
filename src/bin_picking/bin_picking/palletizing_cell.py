"""실제 운반 데모의 작업셀 기하: 롤러 컨베이어 → 목재 출고 팔레트."""
import math
import xml.etree.ElementTree as ET

from bin_picking.palletizing_layout import SceneBody, body_sdf, _visual_box
from bin_picking.palletizing_planner import BoxSpec, PackingPlan, Placement, demo_boxes, plan_boxes


PALLET = SceneBody('pallet_outbound', (0.4, 0.6, 0.14), (0.45, 0.15, 0.07),
                   5.0, (0.60, 0.43, 0.25, 1.0), True)
CONVEYOR = SceneBody('infeed_conveyor', (0.28, 0.65, 0.24), (0.26, -0.62, 0.12),
                    8.0, (0.12, 0.20, 0.28, 1.0), True)
PICKUP_XY = (0.26, -0.38)
PICKUP_SURFACE = 0.24


def motion_plan(seed=20260909, box_count=36, strategy='dense'):
    boxes = demo_boxes(seed, box_count)
    if strategy == 'dense':
        from bin_picking.palletizing_dense import dense_plan
        return _jobs(dense_plan(boxes, starts=128))
    by_id = {box.box_id: box for box in boxes}
    clearance = 0.012
    envelopes = [BoxSpec(b.box_id, (b.size[0]+clearance, b.size[1]+clearance, b.size[2]),
                         b.weight_kg, b.max_load_kg, b.orientations) for b in boxes]
    reserved = plan_boxes(envelopes, strategy=strategy)
    # 실행 여유를 둔 envelope로 공간을 예약하되, 물리/충돌/계측에는 실제 치수를 쓴다.
    placements = []
    for p in reserved.placements:
        original = by_id[p.box.box_id]
        size = original.size if p.yaw_deg == 0 else (original.size[1], original.size[0], original.size[2])
        placements.append(Placement(original,
                                    (p.origin[0]+clearance/2, p.origin[1]+clearance/2, p.origin[2]),
                                    size, p.yaw_deg, p.support_id, p.support_shares, p.layer))
    plan = PackingPlan(reserved.pallet_size, tuple(placements), reserved.rejected,
                       reserved.strategy, reserved.candidate_count)
    return _jobs(plan)


def _jobs(plan):
    jobs = []
    for p in plan.placements:
        # 600 mm 변을 world Y에 맞춰 FR3 도달 범위 안에 놓는다.
        center = (PALLET.position[0] - PALLET.size[0] / 2 + p.origin[1] + p.size[1] / 2,
                  PALLET.position[1] - PALLET.size[1] / 2 + p.origin[0] + p.size[0] / 2,
                  0.14 + p.origin[2] + p.size[2] / 2)
        yaw = 0.0 if p.yaw_deg == 90 else math.pi / 2
        box = SceneBody(p.box.box_id, p.box.size,
                        (*PICKUP_XY, PICKUP_SURFACE + p.box.size[2] / 2),
                        p.box.weight_kg, (0.66, 0.47, 0.29, 1.0))
        jobs.append((box, center, yaw))
    return plan, jobs


def fixture_sdf(body):
    root = ET.fromstring(body_sdf(body))
    link = root.find('model/link')
    for visual in list(link.findall('visual')):
        link.remove(visual)
    if body.name == PALLET.name:
        for i in range(7):
            _visual_box(link, f'deck_board_{i}', (0, (i - 3) * 0.086, 0.060),
                        (0.40, 0.076, 0.020), (0.57 + i * 0.012, 0.40, 0.23, 1))
        for x in (-0.15, 0, 0.15):
            _visual_box(link, f'stringer_{x}', (x, 0, -0.01), (0.055, 0.57, 0.12),
                        (0.48, 0.33, 0.18, 1))
    else:
        for x in (-0.125, 0.125):
            _visual_box(link, f'frame_{x}', (x, 0, 0.095), (0.025, 0.65, 0.040),
                        (0.12, 0.23, 0.32, 1))
            for y in (-0.26, 0.26):
                _visual_box(link, f'leg_{x}_{y}', (x, y, -0.025), (0.035, 0.035, 0.19),
                            (0.32, 0.35, 0.38, 1))
        for i in range(17):
            v = ET.SubElement(link, 'visual', name=f'roller_{i}')
            ET.SubElement(v, 'pose').text = f'0 {(i-8)*0.037} 0.102 0 {math.pi/2} 0'
            cylinder = ET.SubElement(ET.SubElement(v, 'geometry'), 'cylinder')
            ET.SubElement(cylinder, 'radius').text = '0.018'
            ET.SubElement(cylinder, 'length').text = '0.23'
            mat = ET.SubElement(v, 'material')
            ET.SubElement(mat, 'diffuse').text = '0.60 0.64 0.68 1'
            ET.SubElement(mat, 'ambient').text = '0.45 0.48 0.52 1'
    return ET.tostring(root, encoding='unicode')
