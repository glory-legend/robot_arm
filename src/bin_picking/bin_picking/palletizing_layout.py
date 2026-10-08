"""PDF 1단계 오프라인 배치 결과 → Gazebo/MoveIt 공통 장면(ROS 무의존)."""
from dataclasses import dataclass
import xml.etree.ElementTree as ET
import zlib

from bin_picking.palletizing_planner import demo_boxes, plan_boxes


@dataclass(frozen=True)
class SceneBody:
    name: str
    size: tuple[float, float, float]
    position: tuple[float, float, float]
    mass: float
    color: tuple[float, float, float, float]
    static: bool = False


PALLET = SceneBody('pallet_outbound', (0.6, 0.4, 0.04), (0.5, 0.0, 0.02),
                   5.0, (0.25, 0.7, 0.35, 1.0), True)
BOX_COLORS = (
    (0.90, 0.45, 0.15, 1.0), (0.85, 0.65, 0.15, 1.0), (0.70, 0.30, 0.55, 1.0),
)


def make_layout(seed=20260909, box_count=12, strategy='compact'):
    """팔레트 로컬 모서리 좌표를 Gazebo world 중심 좌표로 변환한다."""
    plan = plan_boxes(demo_boxes(seed, box_count), strategy=strategy)
    bodies = [PALLET]
    corner = (PALLET.position[0] - PALLET.size[0] / 2,
              PALLET.position[1] - PALLET.size[1] / 2,
              PALLET.position[2] + PALLET.size[2] / 2)
    for placement in plan.placements:
        size = placement.size
        position = tuple(corner[k] + placement.origin[k] + size[k] / 2 for k in range(3))
        color = BOX_COLORS[(0.06, 0.08, 0.10).index(placement.box.size[2])]
        bodies.append(SceneBody(placement.box.box_id, size, position,
                                placement.box.weight_kg, color))
    return bodies


def body_sdf(body):
    """MoveIt과 같은 직육면체 SDF. 원점은 물체 중심, 자세는 world 기준."""
    sdf = ET.Element('sdf', version='1.8')
    model = ET.SubElement(sdf, 'model', name=body.name)
    ET.SubElement(model, 'static').text = str(body.static).lower()
    ET.SubElement(model, 'pose').text = ' '.join(map(str, (*body.position, 0, 0, 0)))
    link = ET.SubElement(model, 'link', name='body')
    inertial = ET.SubElement(link, 'inertial')
    ET.SubElement(inertial, 'mass').text = str(body.mass)
    inertia = ET.SubElement(inertial, 'inertia')
    x, y, z = body.size
    for axis, value in (
        ('ixx', body.mass * (y*y + z*z) / 12),
        ('iyy', body.mass * (x*x + z*z) / 12),
        ('izz', body.mass * (x*x + y*y) / 12),
        ('ixy', 0), ('ixz', 0), ('iyz', 0),
    ):
        ET.SubElement(inertia, axis).text = str(value)
    for tag in ('collision', 'visual'):
        element = ET.SubElement(link, tag, name=tag)
        box = ET.SubElement(ET.SubElement(element, 'geometry'), 'box')
        ET.SubElement(box, 'size').text = ' '.join(map(str, body.size))
        if tag == 'visual':
            material = ET.SubElement(element, 'material')
            for kind in ('ambient', 'diffuse'):
                ET.SubElement(material, kind).text = ' '.join(map(str, body.color))
    if body.name.startswith('pallet_box_'):
        # 라벨/테이프는 visual만 추가하여 물리·계획 충돌 치수는 보존한다.
        x, y, z = body.size
        _visual_box(link, 'packing_tape', (0, 0, z / 2 + 0.0004),
                    (0.014, y, 0.0006), (0.48, 0.32, 0.15, 1))
        _visual_box(link, 'shipping_label', (0, -y / 2 - 0.0005, 0),
                    (0.065, 0.0007, 0.032), (0.96, 0.95, 0.88, 1))
        bits = zlib.crc32(body.name.encode())
        for i in range(24):
            if (bits >> i) & 1 or i in (0, 1, 22, 23):
                _visual_box(link, f'barcode_{i}',
                            ((i - 11.5) * 0.0022, -y / 2 - 0.0010, 0),
                            (0.0012, 0.0005, 0.023), (0.04, 0.035, 0.03, 1))
    if not body.static:
        plugin = ET.SubElement(model, 'plugin', {
            'filename': 'gz-sim-pose-publisher-system',
            'name': 'gz::sim::systems::PosePublisher',
        })
        for key, value in {
            'publish_link_pose': 'false', 'publish_visual_pose': 'false',
            'publish_collision_pose': 'false', 'publish_sensor_pose': 'false',
            'publish_model_pose': 'true', 'publish_nested_model_pose': 'false',
            'use_pose_vector_msg': 'true', 'static_publisher': 'false',
            'update_frequency': '10',
        }.items():
            ET.SubElement(plugin, key).text = value
    return ET.tostring(sdf, encoding='unicode')


def _visual_box(link, name, position, size, color):
    visual = ET.SubElement(link, 'visual', name=name)
    ET.SubElement(visual, 'pose').text = ' '.join(map(str, (*position, 0, 0, 0)))
    box = ET.SubElement(ET.SubElement(visual, 'geometry'), 'box')
    ET.SubElement(box, 'size').text = ' '.join(map(str, size))
    material = ET.SubElement(visual, 'material')
    for kind in ('ambient', 'diffuse'):
        ET.SubElement(material, kind).text = ' '.join(map(str, color))
    return visual
