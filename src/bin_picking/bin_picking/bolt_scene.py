#!/usr/bin/env python3
"""
볼트 통(bin) + M8 볼트들을 MoveIt planning-scene에 충돌 객체로 등록.
=====================================================================
Gazebo SDF 모델(franka_tutorials/models/{bolt_bin, m8_bolt})과 '같은 배치'를
MoveIt planning-scene에도 올려, move_group이 통/볼트를 충돌 대상으로 인지하게
한다. (Gazebo=물리, planning-scene=계획용 충돌 — 둘을 일치시켜야 계획이 실제와
맞는다.)

- 통  : 열린 상자 = 바닥 + 벽 4개 → 하나의 CollisionObject 'bolt_bin'(box 5개).
        속이 비어 있어야 그리퍼가 안으로 들어갈 수 있으므로 단일 박스가 아닌
        벽 5개로 표현한다.
- 볼트: 눕힌 원기둥 근사 → CollisionObject 'bolt_0'..'bolt_N'(CYLINDER 1개).

⚠ 아래 BIN_* / BOLT_LAYOUT 수치는 spawn_bolts.launch.py 및 SDF 모델과 반드시
  일치해야 한다.

단독 실행 (move_group 이 떠 있어야 함):
  python3 bolt_scene.py            # 등록
  python3 bolt_scene.py --remove   # 제거

다른 스크립트에서 재사용:
  from bolt_scene import all_objects, object_ids
"""
import json
import math
import os
import sys
import tempfile

import rclpy
import tf_transformations
from rclpy.node import Node
from rclpy.parameter import Parameter

from geometry_msgs.msg import Point, Pose, Quaternion
from moveit_msgs.msg import CollisionObject, PlanningScene
from moveit_msgs.srv import ApplyPlanningScene
from shape_msgs.msg import SolidPrimitive

from bin_picking import robot_profiles

# 로봇 베이스(= Gazebo 월드 원점). 팔마다 이름이 다르므로(fr3_link0 / base_link …)
# 활성 프로파일에서 가져온다. 아래 함수들이 이 값을 기본 인자로 쓰므로 임포트
# 시점에 확정돼야 한다 — 그래서 config.py 를 거치지 않고 레지스트리를 직접 읽는다
# (config.py 가 이 모듈을 임포트하므로 반대 방향은 순환이 된다).
REFERENCE_FRAME = robot_profiles.active_profile().arm.base_frame

# ---- 통 배치/치수 (SDF 스폰과 동일해야 함) ----
# 집는 통을 로봇 쪽으로 당겼다: x=0.50 → 0.40.
# [근거] 다중 시드 롤아웃(팔꿈치 7분기)조차 x=0.50 에서 바닥 볼트(z≈0.010)에
# 손끝을 못 넣었다(도달 하한 z≈0.017). 앞으로 멀리 뻗으며 손끝을 수직 아래로
# 두는 건 워크스페이스 경계라 마지막 몇 mm 가 안 나온다. 통을 10cm 당기면
# 같은 자세에서 아래로 내려갈 여유가 크게 늘어 바닥 볼트까지 닿는다.
# ⚠ spawn_bolts.launch.py 의 BIN_XYZ 와 반드시 동일해야 한다(함께 수정).
BIN_XYZ = (0.40, 0.00, 0.00)         # 집는 통(pick bin) 바닥면 중심
DROP_BIN_XYZ = (0.00, 0.45, 0.00)    # 놓는 통(drop bin) — 같은 모델, 좌측
BIN_OUTER = (0.24, 0.20, 0.025)      # 외형 L(x), W(y), H(z) — 얕고 넓은 트레이형
BIN_THICK = 0.005                    # 벽/바닥 두께
BIN_WALL_H = BIN_OUTER[2] - BIN_THICK  # 벽 높이 = 0.02

# ---- 볼트 근사 원기둥 (M8: Ø8 샤프트 + Ø13 머리 → 보수적 반경 7mm, 길이 45mm) ----
BOLT_LEN = 0.045
BOLT_RADIUS = 0.007
# 안착 높이는 '머리 반경'(0.0065)이 기준이다. 샤프트 반경(0.004)으로 잡으면
# 머리가 바닥을 2.5mm 파고든 채 스폰되어 첫 프레임에 전부 튀어오른다.
BOLT_REST_Z = BIN_THICK + 0.0065     # = 0.0115

# ---- 볼트 배치: (dx, dy, dz, yaw) — 통 바닥 중심 기준 오프셋. launch와 동일. ----
# '무더기(pile)': 가운데로 몰아 무작위 위치·방향으로 떨어뜨려 서로 얹히게 한다.
#  - dz 를 조금씩 높여 스폰 → 낙하하며 서로 위에 쌓임(자연스러운 더미).
#  - yaw 가 제각각이므로 파지 시 그리퍼 각도를 볼트 축에 맞춰 회전시켜야 한다
#    (franka_integrated_pick_place.grasp_quat_for_axis 참고).
#  - 스폰 후 위치는 물리로 달라지므로 이 값은 '초기 등록/폴백'용일 뿐이고,
#    실제 좌표는 Gazebo pose 브리지 센싱으로 매 사이클 갱신된다.
#  - seed 20260716 으로 생성, 벽 최소 여유 ≈29mm.
BOLT_LAYOUT = [
    (-0.023, -0.035, 0.000, -1.451),
    (-0.009, -0.034, 0.014, +2.631),
    (-0.020, +0.028, 0.028, -1.438),
    (+0.028, -0.009, 0.042, -1.545),
    (+0.015, -0.011, 0.056, +2.157),
    (-0.025, -0.000, 0.070, -1.709),
    (+0.012, -0.004, 0.084, +0.916),
]

# ---- 랜덤 배치 연동 (spawn_bolts.launch.py 가 기록) ----
# 스폰 런치가 매 실행 랜덤 배치를 생성해 아래 파일에 남긴다. 파일이 있으면
# 그것을 써서 Gazebo 스폰과 planning-scene 이 '같은 배치'를 자동 공유한다.
# 없거나 깨졌으면 위의 고정 배치 폴백(예전과 동일하게 동작).
# ⚠ 실행 순서 전제: 스폰(launch) → 데모 노드 시작. 노드를 먼저 켜면 직전
#   스폰의 배치를 읽는다(센싱이 살아 있으면 어차피 실측으로 덮인다).
LAYOUT_FILE = os.path.join(tempfile.gettempdir(), 'bolt_layout.json')
# 어떤 배치를 쓰게 됐는지 — 데모 노드가 시작 로그로 남긴다(디버깅 근거).
LAYOUT_SOURCE = '고정 배치(bolt_scene 내장 폴백) — 랜덤 배치 파일 없음'
try:
    with open(LAYOUT_FILE) as _f:
        _rows = json.load(_f)['layout']
    if _rows and all(len(r) == 4 for r in _rows):
        BOLT_LAYOUT = [tuple(float(v) for v in r) for r in _rows]
        LAYOUT_SOURCE = f'랜덤 배치 파일 {LAYOUT_FILE} (볼트 {len(BOLT_LAYOUT)}개)'
        print(f'[bolt_scene] 랜덤 배치 로드: {LAYOUT_FILE} '
              f'(볼트 {len(BOLT_LAYOUT)}개)')
except (OSError, ValueError, KeyError, TypeError):
    pass    # 파일 없음/형식 불량 → 고정 배치 폴백


def _box(size, xyz):
    prim = SolidPrimitive()
    prim.type = SolidPrimitive.BOX
    prim.dimensions = list(size)
    pose = Pose()
    pose.position = Point(x=xyz[0], y=xyz[1], z=xyz[2])
    pose.orientation.w = 1.0
    return prim, pose


def bin_collision_object(frame=REFERENCE_FRAME, bin_xyz=BIN_XYZ,
                         obj_id='bolt_bin'):
    """통을 바닥+벽4 = box 5개짜리 CollisionObject 하나로 구성.
    집는 통/놓는 통 모두 같은 모델이라 obj_id 와 bin_xyz 만 바꿔 재사용한다."""
    bx, by, bz = bin_xyz
    lx, wy, _ = BIN_OUTER
    t = BIN_THICK
    zc = t / 2.0                     # 바닥 박스 중심 z
    wz = t + BIN_WALL_H / 2.0        # 벽 중심 z
    ox = lx / 2.0 - t / 2.0          # 벽 중심 x 오프셋
    oy = wy / 2.0 - t / 2.0          # 벽 중심 y 오프셋
    boxes = [
        ((lx, wy, t),         (bx,      by,      bz + zc)),   # 바닥
        ((t, wy, BIN_WALL_H), (bx + ox, by,      bz + wz)),   # +X 벽
        ((t, wy, BIN_WALL_H), (bx - ox, by,      bz + wz)),   # -X 벽
        ((lx, t, BIN_WALL_H), (bx,      by + oy, bz + wz)),   # +Y 벽
        ((lx, t, BIN_WALL_H), (bx,      by - oy, bz + wz)),   # -Y 벽
    ]
    co = CollisionObject()
    co.header.frame_id = frame
    co.id = obj_id
    for size, xyz in boxes:
        prim, pose = _box(size, xyz)
        co.primitives.append(prim)
        co.primitive_poses.append(pose)
    co.operation = CollisionObject.ADD
    return co


def bolt_collision_objects(frame=REFERENCE_FRAME, bin_xyz=BIN_XYZ):
    """각 볼트를 눕힌 원기둥 CollisionObject로 구성."""
    bx, by, bz = bin_xyz
    objs = []
    for i, (dx, dy, dz, yaw) in enumerate(BOLT_LAYOUT):
        co = CollisionObject()
        co.header.frame_id = frame
        co.id = f'bolt_{i}'
        cyl = SolidPrimitive()
        cyl.type = SolidPrimitive.CYLINDER
        cyl.dimensions = [BOLT_LEN, BOLT_RADIUS]   # [height, radius]
        pose = Pose()
        # SDF 링크 원점은 샤프트 중심(비대칭: 축 -0.020..+0.025)이라 볼트 무게중심은
        # 축 방향 +0.0025 지점. 대칭 실린더를 실제 볼트에 맞추려 그만큼 밀어준다.
        axis_off = (BOLT_LEN / 2.0) - 0.020   # = 0.0025
        pose.position = Point(
            x=bx + dx + axis_off * math.cos(yaw),
            y=by + dy + axis_off * math.sin(yaw),
            z=bz + BOLT_REST_Z + dz)
        # 원기둥 기본 축(+Z)을 수평으로 눕히고(pitch 90°) yaw 회전
        q = tf_transformations.quaternion_from_euler(0.0, 1.5708, yaw)
        pose.orientation = Quaternion(x=q[0], y=q[1], z=q[2], w=q[3])
        co.primitives.append(cyl)
        co.primitive_poses.append(pose)
        co.operation = CollisionObject.ADD
        objs.append(co)
    return objs


def drop_bin_collision_object(frame=REFERENCE_FRAME, bin_xyz=DROP_BIN_XYZ):
    """놓는 통(drop bin) — 집는 통과 동일 모델, 위치만 다름."""
    return bin_collision_object(frame, bin_xyz, obj_id='drop_bin')


def all_objects(frame=REFERENCE_FRAME, bin_xyz=BIN_XYZ):
    return ([bin_collision_object(frame, bin_xyz),
             drop_bin_collision_object(frame)]
            + bolt_collision_objects(frame, bin_xyz))


def object_ids():
    return (['bolt_bin', 'drop_bin']
            + [f'bolt_{i}' for i in range(len(BOLT_LAYOUT))])


class BoltSceneNode(Node):
    def __init__(self):
        super().__init__(
            'bolt_scene',
            parameter_overrides=[Parameter('use_sim_time', value=True)],
        )
        self._client = self.create_client(
            ApplyPlanningScene, 'apply_planning_scene')

    def _apply(self, objects):
        if not self._client.wait_for_service(timeout_sec=10.0):
            raise RuntimeError('apply_planning_scene 서비스 연결 실패')
        scene = PlanningScene()
        scene.is_diff = True
        scene.world.collision_objects.extend(objects)
        req = ApplyPlanningScene.Request()
        req.scene = scene
        fut = self._client.call_async(req)
        rclpy.spin_until_future_complete(self, fut, timeout_sec=10.0)
        resp = fut.result()
        return resp is not None and resp.success

    def add(self):
        ok = self._apply(all_objects())
        self.get_logger().info(
            f'볼트 통 + 볼트 {len(BOLT_LAYOUT)}개 등록 '
            f'{"성공" if ok else "실패"}')
        return ok

    def remove(self):
        objs = []
        for oid in object_ids():
            co = CollisionObject()
            co.header.frame_id = REFERENCE_FRAME
            co.id = oid
            co.operation = CollisionObject.REMOVE
            objs.append(co)
        ok = self._apply(objs)
        self.get_logger().info(
            f'볼트 통 + 볼트 제거 {"성공" if ok else "실패"}')
        return ok


def main(args=None):
    rclpy.init(args=args)
    node = BoltSceneNode()
    try:
        if '--remove' in sys.argv[1:]:
            node.remove()
        else:
            node.add()
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
