# -*- coding: utf-8 -*-
"""PlanningScene 충돌객체 등록/제거와 볼트 attach/detach.

SceneMixin 은 IntegratedPickPlace 에 섞이는 책임 단위다(상태는 노드가 소유).
"""
import json
import math
import os
import random
import re
import sys
import threading
import time
import xml.etree.ElementTree as ET

import numpy as np
import rclpy
import tf_transformations
from rclpy.action import ActionClient
from rclpy.node import Node
from rclpy.parameter import Parameter
from rclpy.parameter_client import AsyncParameterClient
from rclpy.qos import DurabilityPolicy, QoSProfile, ReliabilityPolicy

from builtin_interfaces.msg import Duration
from control_msgs.action import FollowJointTrajectory
from geometry_msgs.msg import Point, Pose, PoseStamped, Quaternion, Vector3
from moveit_msgs.action import ExecuteTrajectory, MoveGroup
from moveit_msgs.msg import (
    AttachedCollisionObject,
    BoundingVolume,
    CollisionObject,
    Constraints,
    JointConstraint,
    MotionPlanRequest,
    MoveItErrorCodes,
    OrientationConstraint,
    PlanningOptions,
    PlanningScene,
    PositionConstraint,
    RobotState,
)
from moveit_msgs.srv import (
    ApplyPlanningScene,
    GetCartesianPath,
    GetPositionFK,
    GetPositionIK,
)
from sensor_msgs.msg import JointState
from shape_msgs.msg import SolidPrimitive
from std_msgs.msg import ColorRGBA, Empty
from tf2_msgs.msg import TFMessage
from trajectory_msgs.msg import JointTrajectory, JointTrajectoryPoint
from visualization_msgs.msg import Marker, MarkerArray

# 볼트 통/볼트 자산 (SDF 스폰과 동일한 배치를 planning-scene에 재사용)
from bin_picking.bolt_scene import (
    BIN_OUTER,
    BIN_THICK,
    BIN_XYZ,
    BOLT_LAYOUT,
    BOLT_LEN,
    BOLT_RADIUS,
    BOLT_REST_Z,
    DROP_BIN_XYZ,
    LAYOUT_SOURCE,
    bin_collision_object,
    bolt_collision_objects,
    drop_bin_collision_object,
    object_ids as bolt_object_ids,
)

# 학습형 파지 선택기(ROS 무의존). 임포트 자체가 실패해도(파일 없음 등) 데모는
# 기존 휴리스틱으로 굴러가야 하므로 감싸 둔다 → GraspSelector=None 이면 R3 경로 비활성.
try:
    from bin_picking.grasp_selector import GraspSelector
    _SELECTOR_IMPORT_ERR = ''
except Exception as _exc:                       # noqa: BLE001
    GraspSelector = None
    _SELECTOR_IMPORT_ERR = repr(_exc)




class SceneMixin:

    def _bolt_world_co(self, bolt_id, pos, quat):
        """볼트 하나를 '실제 6D 자세'의 눕힌 원기둥 CollisionObject 로."""
        co = CollisionObject()
        co.header.frame_id = self.REFERENCE_FRAME
        co.id = bolt_id
        cyl = SolidPrimitive()
        cyl.type = SolidPrimitive.CYLINDER
        cyl.dimensions = [BOLT_LEN, BOLT_RADIUS]
        # 실린더 기본 축(+Z)을 볼트 로컬 +X 에 맞춤: q_bolt ⊗ Ry(90°)
        qy = tf_transformations.quaternion_from_euler(0.0, math.pi / 2, 0.0)
        q = tf_transformations.quaternion_multiply(list(quat), list(qy))
        axis = self.bolt_axis_from_quat(quat)
        off = (BOLT_LEN / 2.0) - 0.020        # 무게중심 보정(+2.5mm, 축 방향)
        pose = Pose()
        pose.position = Point(x=pos[0] + off * float(axis[0]),
                              y=pos[1] + off * float(axis[1]),
                              z=max(pos[2] + off * float(axis[2]), 0.009))
        pose.orientation = Quaternion(x=q[0], y=q[1], z=q[2], w=q[3])
        co.primitives.append(cyl)
        co.primitive_poses.append(pose)
        co.operation = CollisionObject.ADD
        return co

    def _refresh_bolt_scene(self):
        """모든 볼트의 충돌 객체를 실제 6D 자세로 갱신.

        ⚠ '이미 놓은 볼트'도 계속 등록해야 한다. 빼버리면 drop_bin 이 계획상
        빈 통이 되어, 다음 볼트를 놓으러 내려갈 때 쌓인 볼트를 밀어 쓸어낸다.
        지금 손에 부착 중인 볼트만 제외한다(그건 로봇 몸의 일부라 별도 관리).
        센싱이 없으면 BOLT_LAYOUT 폴백으로라도 복원한다(임시 제거분 영구 소실 방지).
        """
        objs = []
        for i in range(len(BOLT_LAYOUT)):
            bid = f'bolt_{i}'
            if bid in (self._attached_id, self._attached_src_id):
                continue
            p = self._bolt_sensed.get(bid)
            if p is not None:
                objs.append(self._bolt_world_co(bid, p[0], p[1]))
            else:
                pos, quat = self._bolt_pose(i)
                objs.append(self._bolt_world_co(bid, pos, quat))
        if objs:
            self.add_collision_objects(objs)   # 같은 id 는 ADD 로 위치 덮어씀

    def _set_bin_floor(self, enabled):
        """[현재 미사용 — 적응형 하강(GRASP_RAISE_STEP)으로 대체된 대안]
        집는 통 'bolt_bin' 충돌 모델을 바닥 포함/벽만으로 교체.

        [당시 가설 — 20260722 20판 전패 분석]
        손가락 충돌 지오메트리는 TCP(손끝 기준점)보다 몇 mm 아래까지 내려온다.
        바닥에 누운 볼트(중심 z≈0.010)를 집으려면 TCP 가 z≈0.0096 까지 가야
        하는데, 그 '최종 상태'는 통 바닥 충돌박스(상면 0.005)와 계획상 반드시
        겹친다 → 하강 Cartesian 이 모든 볼트·모든 자세에서 마지막 한 스텝 직전
        (TCP z≈0.017)에 잘렸다. z≥0.0215 목표가 전부 100% 통과한 것과 정확히
        경계가 일치한다.
        실물 손끝은 바닥 위 ~4.6mm(GRASP_FLOOR_CLEAR)를 유지하므로 물리적으로
        안전하며, 바닥 박스는 '계획용 모델'일 뿐이다 → 하강~리프트 동안만
        벽 4개 버전으로 교체(같은 id 로 ADD = 덮어쓰기)하고 끝나면 복원한다.
        벽은 남겨 두므로 벽 회피는 계속 유효하다.
        """
        co = bin_collision_object()
        if not enabled:
            # bolt_scene 구성 순서 전제: boxes[0]=바닥, [1:]=벽 4개
            co.primitives = co.primitives[1:]
            co.primitive_poses = co.primitive_poses[1:]
        ok = self._apply_scene([co])
        self.get_logger().info(
            f'[씬] bolt_bin {"바닥 복원" if enabled else "바닥 임시 제거(벽만)"} '
            f'{"성공" if ok else "실패"}')
        return ok

    # =========================================================
    # 충돌 객체 (ex09) — ApplyPlanningScene 서비스로 직접 등록
    # =========================================================
    def make_box_collision_object(self, name, position, dimensions):
        co = CollisionObject()
        co.header.frame_id = self.REFERENCE_FRAME
        co.id = name
        box = SolidPrimitive()
        box.type = SolidPrimitive.BOX
        box.dimensions = list(dimensions)
        pose = Pose()
        pose.position = Point(x=position[0], y=position[1], z=position[2])
        pose.orientation.w = 1.0
        co.primitives.append(box)
        co.primitive_poses.append(pose)
        co.operation = CollisionObject.ADD
        return co

    def _apply_scene(self, collision_objects):
        scene = PlanningScene()
        scene.is_diff = True
        scene.world.collision_objects.extend(collision_objects)
        req = ApplyPlanningScene.Request()
        req.scene = scene
        fut = self._scene_client.call_async(req)
        resp = self._spin_future(fut, self.SERVICE_TIMEOUT)
        return resp is not None and resp.success

    def add_collision_objects(self, objects):
        ok = self._apply_scene(objects)
        names = ', '.join(o.id for o in objects)
        self.get_logger().info(
            f'충돌 객체 추가 {"성공" if ok else "실패"}: {names}')
        return ok

    def remove_collision_objects(self, names):
        objs = []
        for n in names:
            co = CollisionObject()
            co.header.frame_id = self.REFERENCE_FRAME
            co.id = n
            co.operation = CollisionObject.REMOVE
            objs.append(co)
        ok = self._apply_scene(objs)
        self.get_logger().info(
            f'충돌 객체 제거 {"성공" if ok else "실패"}: {", ".join(names)}')
        return ok

    # =========================================================
    # 파지 물체 부착/분리 (AttachedCollisionObject)
    # =========================================================
    def _apply_attached(self, aco):
        """robot_state diff 로 AttachedCollisionObject 적용."""
        scene = PlanningScene()
        scene.is_diff = True
        scene.robot_state.is_diff = True
        scene.robot_state.attached_collision_objects.append(aco)
        req = ApplyPlanningScene.Request()
        req.scene = scene
        fut = self._scene_client.call_async(req)
        resp = self._spin_future(fut, self.SERVICE_TIMEOUT)
        return resp is not None and resp.success

    def attach_bolt(self, bolt_id):
        """파지한 볼트를 EE 링크에 부착 → 이후 계획이 '볼트를 든' 상태로 회피.
        전제: grasp_quat_for_axis 가 x_tool 을 볼트 축과 정렬시키므로
        볼트 축 = hand X 가 항상 성립한다(볼트 yaw 가 제각각이어도 무방).
        (씬의 월드 객체 bolt_id 는 하강 전 이미 제거되어 있어야 함)"""
        co = CollisionObject()
        co.header.frame_id = self.END_EFFECTOR_LINK
        co.id = bolt_id
        cyl = SolidPrimitive()
        cyl.type = SolidPrimitive.CYLINDER
        cyl.dimensions = [BOLT_LEN, BOLT_RADIUS]   # [height, radius]
        pose = Pose()
        # 원기둥 기본 축(Z)을 hand X로: pitch 90°
        q = tf_transformations.quaternion_from_euler(0.0, math.pi / 2, 0.0)
        pose.orientation = Quaternion(x=q[0], y=q[1], z=q[2], w=q[3])
        co.primitives.append(cyl)
        co.primitive_poses.append(pose)
        co.operation = CollisionObject.ADD

        aco = AttachedCollisionObject()
        aco.link_name = self.END_EFFECTOR_LINK
        # 부착한 볼트와의 충돌을 허용할 링크들(손/손가락/TCP). 링크 이름이
        # 그리퍼마다 다르므로 프로파일이 준다 — 이 목록이 실제 URDF 와 어긋나면
        # 파지 직후 모든 계획이 자기충돌로 실패한다(`binpick_model verify` 가 대조).
        aco.touch_links = list(self.GRIPPER_TOUCH_LINKS)
        aco.object = co
        aco.weight = 0.025
        ok = self._apply_attached(aco)
        if ok:
            self._bolt_attached = True
            self._attached_id = bolt_id
        self.get_logger().info(
            f'볼트 부착(attach) {bolt_id} {"성공" if ok else "실패"}')
        return ok

    def detach_bolt(self, bolt_id):
        """부착한 볼트를 분리 → MoveIt이 현재 위치의 월드 객체로 되돌림."""
        co = CollisionObject()
        co.header.frame_id = self.END_EFFECTOR_LINK
        co.id = bolt_id
        co.operation = CollisionObject.REMOVE
        aco = AttachedCollisionObject()
        aco.link_name = self.END_EFFECTOR_LINK
        aco.object = co
        ok = self._apply_attached(aco)
        if ok:
            self._bolt_attached = False
            self._attached_id = None
        self.get_logger().info(
            f'볼트 분리(detach) {bolt_id} {"성공" if ok else "실패"}')
        return ok

    # =========================================================
    # 정리 (중단/완료 공통)
    # =========================================================
    def _cleanup_scene(self, names=None):
        """충돌 객체 제거 + EE 경로 마커 삭제. 중단·완료 모두에서 재사용.
        기본값: 통 + 볼트 전부."""
        if names is None:
            names = list(bolt_object_ids())
            # 외부 pose 경로의 합성 id 는 bolt_object_ids 에 없어 누수하므로 추가
            if self._attached_id and self._attached_id not in names:
                names.append(self._attached_id)
        # 중단 경로에서 아직 볼트를 든 상태면 먼저 분리(재실행 시 부착 잔재 방지)
        if getattr(self, '_bolt_attached', False) and self._attached_id:
            self.detach_bolt(self._attached_id)
        self.remove_collision_objects(list(names))
        self.clear_ee_path()
