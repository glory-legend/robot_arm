"""볼트 통 + M8 볼트(눕힘)를 이미 떠 있는 Gazebo Sim에 스폰.

franka_gazebo_moveit.launch.py 로 시뮬을 먼저 띄운 뒤 실행:
  ros2 launch bin_picking spawn_bolts.launch.py

기본 (0.5, 0, 0) 지면에 정적 통을 놓고 그 안에 M8 볼트 7개를 눕혀 담는다.
동일 배치가 robot_arm_tutorials/bolt_scene.py 의 MoveIt planning-scene에도
반영된다(둘을 일치시켜야 계획이 실제와 맞음).

  ⚠ BIN_XYZ / BOLT_REST_Z 는 bolt_scene.py 와 반드시 동일.
  배치(BOLT_LAYOUT)는 매 launch 마다 랜덤 생성되고, 그 결과를
  /tmp/bolt_layout.json 에 기록한다 → bolt_scene.py 가 이 파일을 읽어
  planning-scene 초기 등록/폴백에 '같은 배치'를 쓴다(수동 동기화 불필요).
"""
import json
import math
import os
import random
import tempfile
import time

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch_ros.actions import Node

# 집는 통을 로봇 쪽으로 당겼다: x=0.50 → 0.40 (바닥 볼트 도달성 확보).
# ⚠ bolt_scene.py 의 BIN_XYZ 와 반드시 동일. (근거는 bolt_scene 주석 참고)
BIN_XYZ = (0.40, 0.00, 0.00)       # 집는 통 바닥면 중심 (지면)
DROP_BIN_XYZ = (0.00, 0.45, 0.00)  # 놓는 통 — 같은 모델, 좌측
BOLT_REST_Z = 0.0115               # 바닥 상면(0.005) + 머리 반경(0.0065)

# ---- 낱개 분리(singulation) 배치 파라미터 ----
# [사용자 선택: 옵션 3] 무더기를 없애고 바닥에 한 겹으로, 겹치지 않게 흩어 놓는다
# (평행 그리퍼가 무더기 깊은/낀 볼트를 못 집는 근본 한계를 회피). 핵심: X·Y 범위를
# 둘 다 '수직 파지 도달권' 안으로 조인다 — 좌우 |y|≤55mm(한계 60), 앞뒤 x=0.35~0.45
# (통 0.40 ± 50, 먼쪽 한계 ~0.45). 이전 단일레이어(±65/±80)가 볼트를 도달 밖으로
# 벌려 구석 실패를 양산했던 것을 도달권에 맞춰 되돌린다.
N_BOLTS = 5                # 도달권 면적이 좁아 5개로(겹침 없이 + 앞쪽 도달권 여유)
SLOT_NX = 3               # 격자 열(x)
SLOT_NY = 3               # 격자 행(y) — NX*NY >= N_BOLTS
SLOT_HALF_X = 0.043       # 볼트 중심 x 범위 ± (통 0.40 → 0.357~0.443, +지터 ≤0.45)
SLOT_HALF_Y = 0.050       # 볼트 중심 y 범위 ± (좌우 도달권 ±0.055 안)
SLOT_JITTER = 0.007       # 슬롯 중심 무작위 흔들림 ±
# 랜덤 배치를 데모(bolt_scene.py)와 공유하는 파일. launch 시마다 새로 쓴다.
LAYOUT_FILE = os.path.join(tempfile.gettempdir(), 'bolt_layout.json')


def _random_layout(n=N_BOLTS):
    """겹치지 않는 단일 레이어 배치 (dx, dy, dz=0, yaw). 위치·방향 랜덤.
    격자 슬롯을 섞어 n개 고르고 지터를 더한다 → 매 실행 달라지되 안 겹친다.
    dz=0 → 전부 바닥 안착(들린 볼트 없음 → 전부 수직 파지, 기울임 불필요)."""
    slots = []
    for iy in range(SLOT_NY):
        for ix in range(SLOT_NX):
            sx = -SLOT_HALF_X + (2 * SLOT_HALF_X) * ix / max(1, SLOT_NX - 1)
            sy = -SLOT_HALF_Y + (2 * SLOT_HALF_Y) * iy / max(1, SLOT_NY - 1)
            slots.append((sx, sy))
    random.shuffle(slots)
    return [(round(sx + random.uniform(-SLOT_JITTER, SLOT_JITTER), 3),
             round(sy + random.uniform(-SLOT_JITTER, SLOT_JITTER), 3),
             0.0,
             round(random.uniform(-math.pi, math.pi), 3))
            for (sx, sy) in slots[:n]]


# 이 모듈은 `ros2 launch` 때마다 새로 임포트되므로, 여기서 만들면 매 스폰마다
# 새 랜덤 배치가 된다. 실제 안착 위치는 물리로 정해지고 pose 브리지 센싱으로
# 읽으므로, 이 값은 초기 배치용이다.
BOLT_LAYOUT = _random_layout()
try:
    with open(LAYOUT_FILE, 'w') as _f:
        json.dump({'stamp': time.time(), 'layout': BOLT_LAYOUT}, _f)
    print(f'[spawn_bolts] 랜덤 배치 {N_BOLTS}개 생성 → {LAYOUT_FILE}')
except OSError as e:
    # 파일을 못 써도 스폰은 진행한다 — 이때 planning-scene 은 고정 폴백을
    # 쓰므로 배치가 어긋난다는 경고만 남긴다(센싱이 있으면 어차피 덮인다).
    print(f'[spawn_bolts] ⚠ 배치 파일 기록 실패({e}) — '
          f'bolt_scene 폴백이 이번 랜덤 배치와 어긋납니다')


# 볼트별 pose 토픽. m8_bolt/model.sdf 의 PosePublisher 플러그인이
# /model/<모델이름>/pose 로 발행하고, 아래에서 볼트마다 브리지를 하나씩 띄운다.
# ⚠ 토픽을 하나로 remap 하지 않는 이유는 franka_integrated_pick_place.py 의
#   POSE_TOPIC_FMT 주석 참고 (토픽 이름 자체가 볼트 신원이 되게 두는 것).
POSE_TOPIC_FMT = '/model/{}/pose'

# [진단 토글] 집는 통(bolt_bin)을 Gazebo 에 스폰할지. False 면 볼트를 맨바닥에
# 흩어 놓는다("통이 범인인가?" 격리 테스트). ⚠ franka_integrated_pick_place.py 의
# USE_PICK_BIN 과 반드시 동일해야 Gazebo·planning-scene 이 짝이 맞는다.
SPAWN_PICK_BIN = True


def generate_launch_description():
    share = get_package_share_directory('bin_picking')
    bin_sdf = os.path.join(share, 'models', 'bolt_bin', 'model.sdf')
    bolt_sdf = os.path.join(share, 'models', 'm8_bolt', 'model.sdf')

    bx, by, bz = BIN_XYZ
    actions = []
    if SPAWN_PICK_BIN:
        actions.append(Node(
            package='ros_gz_sim', executable='create', output='screen',
            arguments=[
                '-file', bin_sdf, '-name', 'bolt_bin',
                '-x', str(bx), '-y', str(by), '-z', str(bz),
            ],
        ))
    else:
        print('[spawn_bolts] ⚠ 집는 통 없이 스폰 — 맨바닥 볼트 파지 진단 모드')
    actions += [
        # 놓는 통 (집는 통과 완전히 동일한 모델, 위치만 다름)
        Node(
            package='ros_gz_sim', executable='create', output='screen',
            arguments=[
                '-file', bin_sdf, '-name', 'drop_bin',
                '-x', str(DROP_BIN_XYZ[0]), '-y', str(DROP_BIN_XYZ[1]),
                '-z', str(DROP_BIN_XYZ[2]),
            ],
        ),
    ]
    for i, (dx, dy, dz, yaw) in enumerate(BOLT_LAYOUT):
        name = f'bolt_{i}'
        actions.append(Node(
            package='ros_gz_sim', executable='create', output='screen',
            arguments=[
                '-file', bolt_sdf, '-name', name,
                '-x', str(bx + dx), '-y', str(by + dy),
                '-z', str(bz + BOLT_REST_Z + dz),
                '-Y', str(yaw),
            ],
        ))
        # 볼트 실제 위치를 ROS 로 흘려보내는 브리지(볼트당 하나).
        # 데모(franka_integrated_pick_place)가 이 토픽들을 각각 구독해 남은
        # 볼트의 실제 좌표를 매 사이클 다시 읽는다. remap 없이 gz 토픽 이름을
        # 그대로 ROS 토픽 이름으로 쓴다 → 토픽 = 볼트 신원.
        topic = POSE_TOPIC_FMT.format(name)
        actions.append(Node(
            package='ros_gz_bridge', executable='parameter_bridge',
            name=f'{name}_pose_bridge', output='screen',
            arguments=[f'{topic}@tf2_msgs/msg/TFMessage[gz.msgs.Pose_V'],
        ))
    return LaunchDescription(actions)
