import os
from glob import glob

from setuptools import find_packages, setup

package_name = 'bin_picking'


def data_tree(dest_root, src_root):
    """src_root(예: models/) 하위 디렉터리까지 통째로 share/ 에 설치.

    ament_python 의 data_files 는 디렉터리 재귀를 지원하지 않으므로,
    파일을 (설치경로, [파일들]) 튜플로 직접 열거해 준다.
    """
    out = []
    for path, _dirs, files in os.walk(src_root):
        files = [f for f in files if not f.endswith(('.pyc', 'Zone.Identifier'))]
        if not files:
            continue
        dest = os.path.join(dest_root, os.path.relpath(path, os.path.dirname(src_root)))
        out.append((dest, [os.path.join(path, f) for f in files]))
    return out


share = 'share/' + package_name

setup(
    name=package_name,
    version='0.1.0',
    packages=find_packages(exclude=['test']),
    data_files=[
        ('share/ament_index/resource_index/packages',
            ['resource/' + package_name]),
        (share, ['package.xml']),
        (share + '/launch', glob('launch/*.launch.py')),
        (share + '/urdf', glob('urdf/*')),
        (share + '/worlds', glob('worlds/*')),
        *data_tree(share, 'models'),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='slfkalstks',
    maintainer_email='slfkalstks@gmail.com',
    description='FR3 M8 볼트 빈피킹 데모 (ROS2 Jazzy + Gazebo Harmonic). '
                '비전 인식 → 볼트 선택 → MoveIt 파지/이동/놓기.',
    license='Apache-2.0',
    tests_require=['pytest'],
    entry_points={
        'console_scripts': [
            # 통합 픽앤플레이스 데모 (ros2 run bin_picking integrated_pick_place --auto)
            'integrated_pick_place = bin_picking.pick_place_node:main',
            # 카메라 포인트클라우드 → 볼트 6D 자세 인식 노드
            'bolt_vision = bin_picking.bolt_vision:main',
            # 누적된 attempts.jsonl 로 파지 선택기 오프라인 학습
            'train_selector = bin_picking.train_selector:main',
        ],
    },
)
