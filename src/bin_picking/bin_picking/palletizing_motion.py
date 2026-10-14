"""MoveIt 실행 + Gazebo 물리 흡착을 이용한 혼합 박스 운반 데모.

박스는 픽업 지점에 1개씩 생성한다. 운반 중 pose를 강제로 갱신하지 않고
DetachableJoint로 연결하며, 해제 후 실제 위치를 확인해야 완료로 센다.
"""
import json
import math
import time

import numpy as np
import rclpy
from rclpy.action import ActionClient
from rclpy.node import Node
from rclpy.qos import DurabilityPolicy, QoSProfile
from geometry_msgs.msg import Pose
from moveit_msgs.action import ExecuteTrajectory, MoveGroup
from moveit_msgs.msg import (AllowedCollisionEntry, AttachedCollisionObject, CollisionObject,
                            MoveItErrorCodes, PlanningScene, PlanningSceneComponents)
from moveit_msgs.srv import (ApplyPlanningScene, GetCartesianPath, GetPlanningScene,
                            GetPositionFK, GetPositionIK)
from ros_gz_interfaces.srv import SpawnEntity
from sensor_msgs.msg import JointState
from shape_msgs.msg import SolidPrimitive
from std_msgs.msg import Empty, String
from tf2_msgs.msg import TFMessage
from tf_transformations import quaternion_from_euler, quaternion_inverse, quaternion_matrix, quaternion_multiply
from visualization_msgs.msg import Marker, MarkerArray

from bin_picking.moveit_io import MoveItIOMixin
from bin_picking.robot_state import RobotStateMixin
from bin_picking.robot_profiles import get
from bin_picking.palletizing_robot import tool_config
from bin_picking.palletizing_cell import CONVEYOR, PALLET, fixture_sdf, motion_plan
from bin_picking.palletizing_layout import body_sdf


def pose_at(position, yaw=0.0):
    pose = Pose()
    pose.position.x, pose.position.y, pose.position.z = map(float, position)
    q = quaternion_from_euler(math.pi, 0, yaw)
    pose.orientation.x, pose.orientation.y, pose.orientation.z, pose.orientation.w = map(float, q)
    return pose


class PalletizingMotion(Node, MoveItIOMixin, RobotStateMixin):
    ACCEPT_TIMEOUT = 10.0
    RESULT_TIMEOUT = 60.0
    SERVICE_TIMEOUT = 15.0
    CART_MAX_STEP = 0.005
    GRIPPER_JOINT = ''
    GRIPPER_STATE_JOINTS = ()

    def __init__(self):
        super().__init__('palletizing_motion')
        cfg = tool_config()
        self.profile = get(cfg['robot_model'])
        self.REFERENCE_FRAME = self.profile.arm.base_frame
        self.PLANNING_GROUP = self.profile.arm.planning_group
        self.END_EFFECTOR_LINK = cfg['tcp_frame']
        self.ARM_JOINTS = self.profile.arm.joints
        self.JOINT_LIMITS = self.profile.arm.joint_limits
        self.LIMIT_MARGIN = self.profile.arm.limit_margin
        self.touch_links = cfg['touch_links']
        seed = self.declare_parameter('seed', 20260909).value
        count = self.declare_parameter('box_count', 36).value
        strategy = self.declare_parameter('strategy', 'dense').value
        self.resume = self.declare_parameter('resume', False).value
        self.resume_held = self.declare_parameter('resume_held', False).value
        self.velocity = self.declare_parameter('velocity', 0.35).value
        if not 0 < self.velocity <= 0.6:
            raise ValueError('velocity must be in (0, 0.6]')
        self.plan, self.jobs = motion_plan(seed, count, strategy)
        self.placements = {p.box.box_id: p for p in self.plan.placements}
        self.placed_bodies = []
        self.restored_boxes = set()
        self.restored_held = None
        self._joint_state = None
        self._finger_seq = 0
        self._move_client = ActionClient(self, MoveGroup, 'move_action')
        self._execute_client = ActionClient(self, ExecuteTrajectory, 'execute_trajectory')
        self._fk_client = self.create_client(GetPositionFK, 'compute_fk')
        self._ik_client = self.create_client(GetPositionIK, 'compute_ik')
        self._cart_client = self.create_client(GetCartesianPath, 'compute_cartesian_path')
        self._scene_client = self.create_client(ApplyPlanningScene, 'apply_planning_scene')
        self.get_scene = self.create_client(GetPlanningScene, 'get_planning_scene')
        self.spawn_client = self.create_client(SpawnEntity, '/world/empty/create')
        self.create_subscription(JointState, '/joint_states', self._joint_state_cb, 10)
        self.poses, self.vacuum_states = {}, {}
        self.attach_pubs, self.detach_pubs = {}, {}
        for box, _, _ in self.jobs:
            name = box.name
            self.create_subscription(TFMessage, f'/model/{name}/pose',
                                     lambda msg, name=name: self._pose_cb(name, msg), 10)
            self.create_subscription(String, f'/vacuum/{name}/state',
                                     lambda msg, name=name: self.vacuum_states.update({name: msg.data}), 10)
            self.attach_pubs[name] = self.create_publisher(Empty, f'/vacuum/{name}/attach', 10)
            self.detach_pubs[name] = self.create_publisher(Empty, f'/vacuum/{name}/detach', 10)
        self.cancelled = False
        self.active_handle = None
        self.create_subscription(Empty, '/palletizing/stop', self._stop, 10)
        qos = QoSProfile(depth=1, durability=DurabilityPolicy.TRANSIENT_LOCAL)
        self.status_pub = self.create_publisher(String, '/palletizing/status', qos)
        self.marker_pub = self.create_publisher(MarkerArray, '/palletizing/labels', qos)
        self.plan_pub = self.create_publisher(String, '/packing/plan', qos)
        self.plan_pub.publish(String(data=json.dumps(self.plan.to_dict())))
        self.completed, self.active_box, self.attached = 0, '', None
        self.phase = 'STARTING'
        self.started = time.monotonic()
        self.create_timer(0.25, self._status)

    @staticmethod
    def error_name(code):
        return next((k for k in dir(MoveItErrorCodes)
                     if k.isupper() and getattr(MoveItErrorCodes, k) == code), str(code))

    def _stop(self, _msg):
        self.cancelled = True
        if self.active_handle is not None:
            self.active_handle.cancel_goal_async()

    def _pose_cb(self, name, message):
        for tr in message.transforms:
            if tr.child_frame_id == name:
                p = Pose()
                p.position.x = tr.transform.translation.x
                p.position.y = tr.transform.translation.y
                p.position.z = tr.transform.translation.z
                p.orientation = tr.transform.rotation
                self.poses[name] = (p, time.monotonic())

    def _wait(self, predicate, timeout=15.0):
        deadline = time.monotonic() + timeout
        while rclpy.ok() and time.monotonic() < deadline:
            if self.cancelled:
                raise RuntimeError('STOP requested; held box remains attached')
            rclpy.spin_once(self, timeout_sec=0.05)
            if predicate():
                return
        raise RuntimeError(f'{self.phase}: condition timed out')

    def _settle(self, seconds):
        end = time.monotonic() + seconds
        self._wait(lambda: time.monotonic() >= end, seconds + 2)

    def _set_phase(self, phase):
        if self.cancelled:
            raise RuntimeError('STOP requested')
        self.phase = phase
        self.get_logger().info(f'{phase}: {self.active_box} ({self.completed}/{len(self.jobs)})')
        self._status()

    def _status(self):
        data = {'phase': self.phase, 'box_id': self.active_box, 'completed': self.completed,
                'total': len(self.jobs), 'vacuum': self.attached is not None,
                'elapsed_s': round(time.monotonic() - self.started, 1)}
        data['layer'] = self.placements[self.active_box].layer if self.active_box else 0
        data['layers'] = max((p.layer for p in self.plan.placements), default=0)
        self.status_pub.publish(String(data=json.dumps(data)))
        marker = Marker()
        marker.header.frame_id = self.REFERENCE_FRAME
        marker.ns, marker.id = 'cell_status', 0
        marker.type, marker.action = Marker.TEXT_VIEW_FACING, Marker.ADD
        marker.pose.position.x, marker.pose.position.y, marker.pose.position.z = 0.3, 0.2, 0.95
        marker.pose.orientation.w = 1.0
        marker.scale.z = 0.04
        marker.color.r, marker.color.g, marker.color.b, marker.color.a = 0.15, 0.85, 0.95, 1.0
        marker.text = (f'{self.phase}  LAYER {data["layer"]}/{data["layers"]}\n'
                       f'{self.completed}/{len(self.jobs)}  {self.active_box}')
        self.marker_pub.publish(MarkerArray(markers=[marker]))

    def _apply(self, scene):
        scene.is_diff = True
        scene.robot_state.is_diff = True
        request = ApplyPlanningScene.Request(scene=scene)
        result = self._spin_future(self._scene_client.call_async(request), self.SERVICE_TIMEOUT)
        if result is None or not result.success:
            raise RuntimeError('Planning scene update failed')

    def _object(self, body, pose=None):
        obj = CollisionObject()
        obj.id, obj.header.frame_id = body.name, self.REFERENCE_FRAME
        primitive = SolidPrimitive(type=SolidPrimitive.BOX, dimensions=list(body.size))
        if pose is None:
            pose = Pose()
            pose.position.x, pose.position.y, pose.position.z = body.position
            pose.orientation.w = 1.0
        obj.primitives, obj.primitive_poses = [primitive], [pose]
        obj.operation = CollisionObject.ADD
        return obj

    def _world_object(self, box):
        scene = PlanningScene()
        pose, stamp = self.poses[box.name]
        if time.monotonic() - stamp > 2:
            raise RuntimeError(f'{box.name}: stale physical pose')
        scene.world.collision_objects = [self._object(box, pose)]
        self._apply(scene)

    def _spawn(self, body, sdf):
        req = SpawnEntity.Request()
        req.entity_factory.name, req.entity_factory.sdf = body.name, sdf
        req.entity_factory.pose.position.x = body.position[0]
        req.entity_factory.pose.position.y = body.position[1]
        req.entity_factory.pose.position.z = body.position[2]
        req.entity_factory.pose.orientation.w = 1.0
        resp = self._spin_future(self.spawn_client.call_async(req), 20)
        if resp is None or not resp.success:
            raise RuntimeError(f'Gazebo spawn failed: {body.name}')

    def _vacuum(self, name, enabled):
        wanted = 'attached' if enabled else 'detached'
        pub = self.attach_pubs[name] if enabled else self.detach_pubs[name]
        deadline = time.monotonic() + 8
        while time.monotonic() < deadline:
            pub.publish(Empty())
            self._settle(0.15)
            if self.vacuum_states.get(name) == wanted:
                self.attached = name if enabled else None
                return
        raise RuntimeError(f'Vacuum {name}: no {wanted} acknowledgement')

    def _contact(self, name, support, allowed):
        req = GetPlanningScene.Request()
        req.components.components = PlanningSceneComponents.ALLOWED_COLLISION_MATRIX
        resp = self._spin_future(self.get_scene.call_async(req), self.SERVICE_TIMEOUT)
        if resp is None:
            raise RuntimeError('Could not read collision matrix')
        matrix = resp.scene.allowed_collision_matrix
        for item in (name, support):
            if item not in matrix.entry_names:
                matrix.entry_names.append(item)
                for row in matrix.entry_values:
                    row.enabled.append(False)
                matrix.entry_values.append(AllowedCollisionEntry(enabled=[False]*len(matrix.entry_names)))
        a, b = matrix.entry_names.index(name), matrix.entry_names.index(support)
        matrix.entry_values[a].enabled[b] = allowed
        matrix.entry_values[b].enabled[a] = allowed
        scene = PlanningScene(allowed_collision_matrix=matrix)
        self._apply(scene)

    def _tcp_pose(self):
        req = GetPositionFK.Request()
        req.header.frame_id = self.REFERENCE_FRAME
        req.fk_link_names = [self.END_EFFECTOR_LINK]
        req.robot_state = self._current_arm_state()
        resp = self._spin_future(self._fk_client.call_async(req), self.SERVICE_TIMEOUT)
        if resp is None or resp.error_code.val != MoveItErrorCodes.SUCCESS:
            raise RuntimeError('TCP FK failed')
        return resp.pose_stamped[0].pose

    def _attach_scene(self, box):
        tcp = self._tcp_pose()
        actual = self.poses[box.name][0]
        q_tcp = [getattr(tcp.orientation, k) for k in 'xyzw']
        inv = quaternion_inverse(q_tcp)
        offset = np.array([getattr(actual.position, k)-getattr(tcp.position, k) for k in 'xyz'])
        local_xyz = quaternion_matrix(inv)[:3, :3] @ offset
        local_q = quaternion_multiply(inv, [getattr(actual.orientation, k) for k in 'xyzw'])
        local = Pose()
        local.position.x, local.position.y, local.position.z = map(float, local_xyz)
        local.orientation.x, local.orientation.y, local.orientation.z, local.orientation.w = map(float, local_q)
        obj = self._object(box, local)
        obj.header.frame_id = self.END_EFFECTOR_LINK
        attached = AttachedCollisionObject(link_name=self.END_EFFECTOR_LINK, object=obj,
                                           touch_links=self.touch_links, weight=box.mass)
        scene = PlanningScene()
        # AttachedCollisionObject.ADD가 같은 ID의 world 객체를 제거한다.
        # 같은 diff에 REMOVE도 넣으면 이중 제거가 되어 서비스가 실패한다.
        scene.robot_state.attached_collision_objects = [attached]
        self._apply(scene)
        self.attached = box.name

    def _verify_contact(self, box):
        tcp = self._tcp_pose()
        actual, stamp = self.poses[box.name]
        q = [getattr(actual.orientation, k) for k in 'xyzw']
        displacement = np.array([getattr(tcp.position, k)-getattr(actual.position, k) for k in 'xyz'])
        local = quaternion_matrix(quaternion_inverse(q))[:3, :3] @ displacement
        gap = local[2] - box.size[2]/2
        tool_z = quaternion_matrix([getattr(tcp.orientation, k) for k in 'xyzw'])[:3, 2]
        box_z = quaternion_matrix(q)[:3, 2]
        if (time.monotonic()-stamp > 1 or not -0.002 <= gap <= 0.006
                or abs(local[0])+0.037 > box.size[0]/2
                or abs(local[1])+0.028 > box.size[1]/2 or np.dot(tool_z, box_z) > -0.995):
            raise RuntimeError(f'Vacuum contact invalid: gap={gap*1000:.1f} mm')

    def _detach_scene(self, box):
        scene = PlanningScene()
        scene.robot_state.attached_collision_objects = [AttachedCollisionObject(
            link_name=self.END_EFFECTOR_LINK,
            object=CollisionObject(id=box.name, operation=CollisionObject.REMOVE))]
        scene.world.collision_objects = [self._object(box, self.poses[box.name][0])]
        self._apply(scene)
        self.attached = None

    def execute_trajectory(self, trajectory):
        if self.cancelled or trajectory is None or not trajectory.joint_trajectory.points:
            return False
        future = self._execute_client.send_goal_async(ExecuteTrajectory.Goal(trajectory=trajectory))
        handle = self._spin_future(future, self.ACCEPT_TIMEOUT)
        if handle is None or not handle.accepted:
            if handle is None:
                def cancel_late(done):
                    late = done.result()
                    if late is not None and late.accepted:
                        late.cancel_goal_async()
                future.add_done_callback(cancel_late)
            return False
        self.active_handle = handle
        response = self._spin_future(handle.get_result_async(), self.RESULT_TIMEOUT)
        if response is None:
            self._spin_future(handle.cancel_goal_async(), self.ACCEPT_TIMEOUT)
            raise RuntimeError('Execution timed out; cancel requested')
        self.active_handle = None
        return not self.cancelled and response.result.error_code.val == MoveItErrorCodes.SUCCESS

    def _move(self, position, yaw=0.0, straight=False):
        goal = pose_at(position, yaw)
        if straight:
            trajectory, fraction = self.compute_cartesian([goal], vel=min(self.velocity, 0.25))
            if fraction < 0.999:
                raise RuntimeError(f'{self.phase}: Cartesian path incomplete ({fraction:.1%})')
        else:
            trajectory = None
            for seed in (self._arm_joint_positions(), self._ready_target):
                joints = self._ik_joint_goal(goal, seed)
                if joints is not None:
                    ok, trajectory = self.plan_to_joint_goal(joints, vel=self.velocity)
                    if ok:
                        break
                    trajectory = None
            if trajectory is None:
                ok, trajectory = self.plan_to_pose_goal(goal, vel=self.velocity)
                if not ok:
                    raise RuntimeError(f'{self.phase}: no collision-free pose plan')
        if not self.execute_trajectory(trajectory):
            raise RuntimeError(f'{self.phase}: trajectory execution failed')
        self._settle(0.15)
        actual = self._tcp_pose().position
        error = math.dist(position, (actual.x, actual.y, actual.z))
        if error > 0.012:
            raise RuntimeError(f'{self.phase}: TCP error {error*1000:.1f} mm')

    def _place_approach(self, target, yaw, travel_z, place_z):
        # 동일한 직사각형 배치인 yaw와 yaw+π의 손목 자세, 여러 IK 해를 비교한다.
        # 먼저 전체 수직 하강을 검사해야 도착 후 특이점/관절 한계에 갇히지 않는다.
        best_fraction = 0.0
        for approach_z in (travel_z, place_z+0.04):
            for heading in (yaw, yaw-math.pi):
                goal = pose_at((target[0], target[1], approach_z), heading)
                for seed in (self._arm_joint_positions(), self._ready_target):
                    joints = self._ik_joint_goal(goal, seed)
                    if joints is None:
                        continue
                    _, fraction = self.compute_cartesian(
                        [pose_at((target[0], target[1], place_z), heading)],
                        vel=min(self.velocity, 0.25), start_joints=joints)
                    best_fraction = max(best_fraction, fraction)
                    if fraction < 0.999:
                        continue
                    ok, trajectory = self.plan_to_joint_goal(joints, vel=self.velocity)
                    if ok:
                        if not self.execute_trajectory(trajectory):
                            raise RuntimeError('Placement approach execution failed')
                        self._settle(0.15)
                        # 가상 IK와 실제 도착 관절값의 차이도 좁은 배치에서 중요하다.
                        descent, actual_fraction = self.compute_cartesian(
                            [pose_at((target[0], target[1], place_z), heading)],
                            vel=min(self.velocity, .25))
                        if actual_fraction >= .999:
                            return heading, approach_z, descent
                        self.get_logger().info(f'Actual descent {actual_fraction:.1%}; testing another approach')
        raise RuntimeError(f'No validated placement descent; best={best_fraction:.1%}')

    def _descend_checked(self, trajectory, position):
        if not self.execute_trajectory(trajectory):
            raise RuntimeError(f'{self.phase}: validated descent execution failed')
        self._settle(.25)
        p = self._tcp_pose().position
        if math.dist(position, (p.x, p.y, p.z)) > .002:
            raise RuntimeError(f'{self.phase}: descent endpoint outside 2 mm tolerance')

    def _restore_completed(self):
        """명시적 resume에서만 무부착·정지·실측 계획 일치를 확인한다."""
        self._set_phase('RECONCILING')
        self._settle(0.5)
        if any(abs(v) > 0.01 for v in self._joint_state.velocity):
            raise RuntimeError('Resume requires a stationary robot')
        req = GetPlanningScene.Request()
        req.components.components = (PlanningSceneComponents.WORLD_OBJECT_GEOMETRY
                                     | PlanningSceneComponents.ROBOT_STATE_ATTACHED_OBJECTS)
        resp = self._spin_future(self.get_scene.call_async(req), self.SERVICE_TIMEOUT)
        if resp is None:
            raise RuntimeError('Resume planning scene unavailable')
        attached = resp.scene.robot_state.attached_collision_objects
        if attached and (not self.resume_held or len(attached) != 1):
            raise RuntimeError('Held resume requires explicit resume_held and exactly one known box')
        held = attached[0].object.id if attached else None
        if held and (held not in self.placements or attached[0].link_name != self.END_EFFECTOR_LINK):
            raise RuntimeError('Unknown held object or attachment link')
        objects = {o.id: o for o in resp.scene.world.collision_objects}
        if not all(b.name in objects for b in (PALLET, CONVEYOR)):
            raise RuntimeError('Resume fixtures missing')
        existing = [b.name for b, _, _ in self.jobs if b.name in objects or b.name == held]
        self._wait(lambda: all(n in self.poses for n in existing), 15)
        pending = False
        for box, target, yaw in self.jobs:
            if box.name == held:
                if pending:
                    raise RuntimeError('Held box is not the next pending job')
                self._verify_contact(box)
                self._settle(.3)
                self._verify_contact(box)
                self.restored_held = box.name
                self.attached = box.name
                pending = True
                continue
            if box.name not in objects:
                pending = True
                continue
            obj = objects[box.name]
            if (len(obj.primitives) != 1 or len(obj.primitives[0].dimensions) != 3
                    or any(abs(a-b) > 1e-8 for a, b in zip(obj.primitives[0].dimensions, box.size))):
                raise RuntimeError(f'Resume shape mismatch: {box.name}')
            physical, stamp = self.poses[box.name]
            xyz = (physical.position.x, physical.position.y, physical.position.z)
            q = physical.orientation
            mat = quaternion_matrix([q.x, q.y, q.z, q.w])
            heading = math.atan2(mat[1, 0], mat[0, 0])
            aligned = abs((heading-yaw+math.pi/2) % math.pi-math.pi/2) < .035
            if math.dist(xyz, target) <= .005 and mat[2, 2] > .995 and aligned:
                if pending:
                    raise RuntimeError('Resume found a gap in completed job sequence')
                self.placed_bodies.append(box)
                self.completed += 1
            elif not pending and math.dist(xyz, box.position) <= .005 and mat[2, 2] > .995:
                pending = True  # 하강 전에 중단된 현재 픽업 박스는 재생성하지 않는다.
            else:
                raise RuntimeError(f'Resume pose does not match plan or pickup: {box.name}')
            if time.monotonic()-stamp > 2:
                raise RuntimeError('Resume physical pose stale')
            # 상태 토픽은 상태 변경 시에만 발행되므로 새 구독자는 과거 detached를 못 받는다.
            # 계획/픽업 지지면 위에 있고 MoveIt 무부착인 박스만 명시적으로 해제 상태로 만든다.
            # 공중에 있거나 위치가 불명확한 물품에는 이 경로가 적용되지 않는다.
            for _ in range(3):
                self.detach_pubs[box.name].publish(Empty())
                self._settle(.15)
            if self.vacuum_states.get(box.name) == 'attached':
                raise RuntimeError(f'Resume detach failed: {box.name}')
            after = self.poses[box.name][0].position
            if math.dist(xyz, (after.x, after.y, after.z)) > .002:
                raise RuntimeError(f'Resume support moved after detach: {box.name}')
            self.restored_boxes.add(box.name)
            self._world_object(box)
        self.get_logger().info(f'RECONCILED {self.completed}/{len(self.jobs)} physical placements')

    def run(self):
        if self.plan.rejected:
            raise RuntimeError(f'Unplaced boxes in plan: {self.plan.rejected}')
        for client in (self._move_client, self._execute_client):
            if not client.wait_for_server(timeout_sec=60):
                raise RuntimeError('MoveIt action unavailable')
        for client in (self.spawn_client, self._scene_client, self._ik_client,
                       self._fk_client, self._cart_client, self.get_scene):
            if not client.wait_for_service(timeout_sec=60):
                raise RuntimeError(f'Service unavailable: {client.srv_name}')
        self._wait(lambda: self._arm_joint_positions() is not None, 60)
        if self.get_node_names().count(self.get_name()) > 1:
            raise RuntimeError('Another palletizing executor is running; stop it before resuming')
        self._ready_target = self.load_named_pose(self.profile.arm.home_state)
        if self.resume:
            self._restore_completed()
        else:
            for fixture in (PALLET, CONVEYOR):
                self._spawn(fixture, fixture_sdf(fixture))
            scene = PlanningScene()
            scene.world.collision_objects = [self._object(body) for body in (PALLET, CONVEYOR)]
            self._apply(scene)
            self._set_phase('HOMING')
            ok, trajectory = self.plan_to_joint_goal(self._ready_target, vel=self.velocity)
            if not ok or not self.execute_trajectory(trajectory):
                raise RuntimeError('Could not reach ready position')
        for box, target, yaw in self.jobs[self.completed:]:
            self.active_box = box.name
            if box.name == self.restored_held:
                tcp = self._tcp_pose()
                grip = (tcp.position.x, tcp.position.y, tcp.position.z)
                q = tcp.orientation
                m = quaternion_matrix([q.x, q.y, q.z, q.w])
                hold_heading = math.atan2(m[1, 0], m[0, 0])
                q = self.poses[box.name][0].orientation
                m = quaternion_matrix([q.x, q.y, q.z, q.w])
                pickup_yaw = hold_heading - math.atan2(m[1, 0], m[0, 0])
            else:
                self._set_phase('INFEED')
                if box.name not in self.poses:
                    self._spawn(box, body_sdf(box))
                self._wait(lambda: box.name in self.poses)
                # DetachableJoint는 최초 생성 시 attached이므로 움직이기 전에 해제한다.
                if box.name not in self.restored_boxes:
                    self._vacuum(box.name, False)
                self._settle(0.4)
                self._world_object(box)
                actual = self.poses[box.name][0].position
                source = (actual.x, actual.y, actual.z)
                if math.dist(source, box.position) > 0.015:
                    raise RuntimeError('Infeed box has moved out of pickup area')
                grip = (source[0], source[1], source[2] + box.size[2] / 2 + 0.002)
                self._set_phase('APPROACH')
                pickup_yaw, pickup_z, descent = self._place_approach(grip, 0.0, 0.50, grip[2])
                self._set_phase('DESCEND')
                self._descend_checked(descent, grip)
                self._set_phase('VACUUM_ON')
                self._verify_contact(box)
                self._vacuum(box.name, True)
                self._attach_scene(box)
                self._contact(box.name, CONVEYOR.name, True)
                self._set_phase('LIFT')
                self._move((grip[0], grip[1], pickup_z), pickup_yaw, straight=True)
                if pickup_z < 0.50:
                    self._contact(box.name, CONVEYOR.name, False)
                    self._move((grip[0], grip[1], 0.50), pickup_yaw)
                self._settle(0.25)
                if self.poses[box.name][0].position.z < source[2] + 0.08:
                    raise RuntimeError('Physical grasp verification failed: box did not lift')
                self._contact(box.name, CONVEYOR.name, False)
                hold_heading = pickup_yaw
            self._set_phase('TRANSFER')
            place_z = target[2] + box.size[2] / 2 + 0.004
            # 운반 박스의 바닥이 이미 쌓인 모든 상면보다 높도록 한다.
            stack_top = max((self.poses[b.name][0].position.z+b.size[2]/2
                             for b in self.placed_bodies), default=PALLET.size[2])
            travel_z = max(0.50, place_z + 0.06, stack_top + box.size[2] + 0.035)
            if travel_z > 0.50:
                self._move((grip[0], grip[1], travel_z), hold_heading, straight=True)
            placement = self.placements[box.name]
            supports = [name for name, _ in placement.support_shares]
            if not supports:
                supports = [placement.support_id or PALLET.name]
            for support in supports:
                self._contact(box.name, support, True)
            expected_yaw = yaw
            yaw, retreat_z, descent = self._place_approach(target, yaw+pickup_yaw, travel_z, place_z)
            self._set_phase('PLACE')
            self._descend_checked(descent, (target[0], target[1], place_z))
            self._set_phase('VACUUM_OFF')
            self._vacuum(box.name, False)
            self._settle(0.4)
            self._detach_scene(box)
            self._set_phase('RETREAT')
            self._move((target[0], target[1], retreat_z), yaw, straight=True)
            self._settle(0.5)
            self._world_object(box)
            measured = self.poses[box.name][0].position
            error = math.dist(target, (measured.x, measured.y, measured.z))
            rotation = self.poses[box.name][0].orientation
            matrix = quaternion_matrix([rotation.x, rotation.y, rotation.z, rotation.w])
            measured_yaw = math.atan2(matrix[1, 0], matrix[0, 0])
            yaw_error = abs((measured_yaw-expected_yaw+math.pi/2) % math.pi-math.pi/2)
            if error > 0.005 or matrix[2, 2] < 0.995 or yaw_error > 0.035:
                raise RuntimeError(f'Placement verification failed: {error*1000:.1f} mm')
            self.placed_bodies.append(box)
            # 상단 하중으로 하단이 미세하게 움직인 경우도 다음 계획에 반영한다.
            scene = PlanningScene()
            scene.world.collision_objects = [self._object(b, self.poses[b.name][0]) for b in self.placed_bodies]
            self._apply(scene)
            self.completed += 1
            self._set_phase('VERIFIED')
            self.get_logger().info(f'PLACED {box.name}: error={error*1000:.2f} mm; physical joint released')
        self.active_box = ''
        ok, trajectory = self.plan_to_joint_goal(self._ready_target, vel=self.velocity)
        if ok:
            self.execute_trajectory(trajectory)
        self._set_phase('COMPLETE')
        rclpy.spin(self)


def main(args=None):
    rclpy.init(args=args)
    node = PalletizingMotion()
    try:
        node.run()
    except KeyboardInterrupt:
        pass
    except Exception as exc:
        node.phase = 'FAULT'
        node.get_logger().error(str(exc))
        node._status()
        # 고장 장면과 부착 상태를 유지하여 진단한다. 자동 재시도/강제 해제는 하지 않는다.
        try:
            rclpy.spin(node)
        except KeyboardInterrupt:
            pass
    finally:
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()
