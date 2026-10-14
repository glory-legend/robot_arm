"""벤더 원본을 수정하지 않고 FR3의 평행 그리퍼를 진공 툴로 교체한다."""
import os
import xml.etree.ElementTree as ET

from ament_index_python.packages import get_package_share_directory
import xacro
import yaml


def tool_config():
    path = os.path.join(get_package_share_directory('bin_picking'), 'config', 'palletizing_tool.yaml')
    with open(path) as stream:
        return yaml.safe_load(stream)


def _shape(link, name, xyz, shape, size, color, collision=True):
    for tag in (('visual', 'collision') if collision else ('visual',)):
        item = ET.SubElement(link, tag, name=name)
        ET.SubElement(item, 'origin', xyz=xyz, rpy='0 0 0')
        geometry = ET.SubElement(item, 'geometry')
        if shape == 'box':
            ET.SubElement(geometry, 'box', size=size)
        else:
            radius, length = size.split()
            ET.SubElement(geometry, 'cylinder', radius=radius, length=length)
        if tag == 'visual':
            material = ET.SubElement(item, 'material', name=name)
            ET.SubElement(material, 'color', rgba=color)


def vacuum_descriptions(profile, box_count):
    cfg = tool_config()
    if profile.name != cfg['robot_model']:
        raise ValueError('Vacuum demo currently requires robot_model:=fr3')
    desc = profile.description
    path = os.path.join(get_package_share_directory(desc.urdf_package), desc.urdf_path)
    args = {key: str(value).lower() if isinstance(value, bool) else str(value)
            for key, value in desc.urdf_args.items()}
    args.update(hand='false', ee_id='none')
    root = ET.fromstring(xacro.process_file(path, mappings=args).toxml())
    tool = ET.SubElement(root, 'link', name=cfg['body_link'])
    inertial = ET.SubElement(tool, 'inertial')
    ET.SubElement(inertial, 'origin', xyz='0 0 0.07')
    ET.SubElement(inertial, 'mass', value='0.35')
    ET.SubElement(inertial, 'inertia', ixx='0.0008', iyy='0.0008', izz='0.0004',
                  ixy='0', ixz='0', iyz='0')
    _shape(tool, 'aluminum_flange', '0 0 0.01', 'cylinder', '0.034 0.020', '0.65 0.68 0.72 1')
    _shape(tool, 'vacuum_manifold', '0 0 0.052', 'cylinder', '0.023 0.064', '0.08 0.24 0.40 1')
    _shape(tool, 'mounting_plate', '0 0 0.092', 'box', '0.082 0.062 0.016', '0.22 0.25 0.28 1')
    for i, (x, y) in enumerate(((-0.025, -0.016), (-0.025, 0.016),
                                (0.025, -0.016), (0.025, 0.016))):
        _shape(tool, f'stem_{i}', f'{x} {y} 0.116', 'cylinder', '0.006 0.032', '0.7 0.72 0.75 1')
        for j, z in enumerate((0.133, 0.138, 0.143)):
            _shape(tool, f'bellows_{i}_{j}', f'{x} {y} {z}', 'cylinder',
                   '0.012 0.004', '0.055 0.06 0.065 1', collision=(j == 2))
    joint = ET.SubElement(root, 'joint', name='vacuum_mount', type='fixed')
    ET.SubElement(joint, 'parent', link=cfg['mount_link'])
    ET.SubElement(joint, 'child', link=cfg['body_link'])
    gazebo = ET.SubElement(root, 'gazebo', reference='vacuum_mount')
    ET.SubElement(gazebo, 'preserveFixedJoint').text = 'true'
    gazebo = ET.SubElement(root, 'gazebo', reference=cfg['body_link'])
    ET.SubElement(gazebo, 'gravity').text = 'false'
    ET.SubElement(root, 'link', name=cfg['tcp_frame'])
    joint = ET.SubElement(root, 'joint', name='vacuum_tcp_joint', type='fixed')
    ET.SubElement(joint, 'parent', link=cfg['body_link'])
    ET.SubElement(joint, 'child', link=cfg['tcp_frame'])
    ET.SubElement(joint, 'origin', xyz=f"0 0 {cfg['tcp_offset']}")
    # 각 박스에 대해 물리 fixed joint를 생성/제거한다. 위치 갱신으로 운반하지 않는다.
    gazebo = ET.SubElement(root, 'gazebo')
    for i in range(box_count):
        name = f'pallet_box_{i}'
        plugin = ET.SubElement(gazebo, 'plugin', {
            'filename': 'gz-sim-detachable-joint-system',
            'name': 'gz::sim::systems::DetachableJoint',
        })
        for key, value in {
            'parent_link': cfg['body_link'], 'child_model': name, 'child_link': 'body',
            'attach_topic': f'/vacuum/{name}/attach', 'detach_topic': f'/vacuum/{name}/detach',
            'output_topic': f'/vacuum/{name}/state', 'suppress_child_warning': 'true',
        }.items():
            ET.SubElement(plugin, key).text = value
    srdf_path = os.path.join(get_package_share_directory(desc.srdf_package), desc.srdf_path)
    semantic = ET.fromstring(xacro.process_file(
        srdf_path, mappings={'hand': 'false', 'ee_id': 'none'}).toxml())
    for joint in semantic.findall('virtual_joint'):
        semantic.remove(joint)
    for chain in semantic.findall(f"group[@name='{profile.arm.planning_group}']/chain"):
        chain.set('tip_link', cfg['tcp_frame'])
    ET.SubElement(semantic, 'group', name='vacuum').append(ET.Element('link', name=cfg['body_link']))
    ET.SubElement(semantic, 'end_effector', name='vacuum', parent_link=cfg['mount_link'], group='vacuum')
    for link in cfg['touch_links']:
        if link != cfg['body_link']:
            ET.SubElement(semantic, 'disable_collisions', link1=link,
                          link2=cfg['body_link'], reason='Adjacent')
    return ET.tostring(root, encoding='unicode'), ET.tostring(semantic, encoding='unicode')
