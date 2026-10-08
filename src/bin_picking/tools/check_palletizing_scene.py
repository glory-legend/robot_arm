"""실행 중인 PDF 1단계 장면 검증: Gazebo pose ↔ MoveIt ↔ 오프라인 계획.

ROS 환경을 source한 뒤 실행한다. 장면을 수정하거나 로봇을 움직이지 않는다.
"""
import argparse
import json
import math
import time
from dataclasses import replace

import rclpy
from rclpy.qos import DurabilityPolicy, QoSProfile
from std_msgs.msg import String
from moveit_msgs.msg import PlanningSceneComponents
from moveit_msgs.srv import GetPlanningScene
from tf2_msgs.msg import TFMessage

from bin_picking.palletizing_layout import make_layout


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--seed', type=int, default=20260909)
    parser.add_argument('--mode', choices=('motion', 'preview'), default='motion')
    parser.add_argument('--box-count', type=int)
    parser.add_argument('--strategy', choices=('greedy', 'compact', 'dense'))
    parser.add_argument('--timeout', type=float, default=180.0)
    args = parser.parse_args()
    count = args.box_count if args.box_count is not None else (36 if args.mode == 'motion' else 12)
    args.strategy = args.strategy or ('dense' if args.mode == 'motion' else 'compact')
    if args.mode == 'motion':
        from bin_picking.palletizing_cell import PALLET, CONVEYOR, motion_plan
        plan, jobs = motion_plan(args.seed, count, args.strategy)
        if plan.rejected:
            raise ValueError(f'Plan has unplaced boxes: {plan.rejected}')
        bodies = [PALLET, CONVEYOR] + [replace(b, position=target) for b, target, _ in jobs]
        expected_yaws = {b.name: yaw for b, _, yaw in jobs}
    else:
        bodies = make_layout(args.seed, count, args.strategy)
    sensed = {}
    rclpy.init()
    node = rclpy.create_node('check_palletizing_scene')
    status = {}
    qos = QoSProfile(depth=1, durability=DurabilityPolicy.TRANSIENT_LOCAL)
    status_sub = node.create_subscription(String, '/palletizing/status',
                                         lambda msg: status.update(json.loads(msg.data)), qos)

    def receive(name, message):
        for tr in message.transforms:
            if tr.child_frame_id == name:
                sensed[name] = tr.transform

    subscriptions = [node.create_subscription(
        TFMessage, f'/model/{b.name}/pose',
        lambda message, name=b.name: receive(name, message), 10)
        for b in bodies if not b.static]
    client = node.create_client(GetPlanningScene, '/get_planning_scene')
    deadline = time.monotonic() + args.timeout
    try:
        while time.monotonic() < deadline:
            rclpy.spin_once(node, timeout_sec=0.1)
            if status.get('phase') == 'FAULT':
                raise RuntimeError(f'Motion fault: {status}')
            done = args.mode == 'preview' or status.get('phase') == 'COMPLETE'
            if done and len(sensed) == len(subscriptions) and client.service_is_ready():
                break
        else:
            raise RuntimeError(f'pose/service timeout: got={sorted(sensed)}')
        request = GetPlanningScene.Request()
        request.components.components = (PlanningSceneComponents.WORLD_OBJECT_GEOMETRY
                                         | PlanningSceneComponents.ROBOT_STATE_ATTACHED_OBJECTS)
        future = client.call_async(request)
        rclpy.spin_until_future_complete(node, future, timeout_sec=15)
        if not future.done() or future.result() is None:
            raise RuntimeError('GetPlanningScene timeout')
        objects = {o.id: o for o in future.result().scene.world.collision_objects}
        errors = []
        if future.result().scene.robot_state.attached_collision_objects:
            errors.append('A box is still attached after completion')
        max_plan_error = max_sync_error = 0.0
        for body in bodies:
            if body.name not in objects:
                errors.append(f'{body.name}: missing MoveIt object')
                continue
            obj = objects[body.name]
            if len(obj.primitives) != 1 or len(obj.primitive_poses) != 1:
                errors.append(f'{body.name}: unexpected shape')
                continue
            if len(obj.primitives[0].dimensions) != 3 or any(
                    abs(a-b) > 1e-8 for a, b in zip(obj.primitives[0].dimensions, body.size)):
                errors.append(f'{body.name}: dimensions mismatch')
            # GetPlanningScene may move world translation into CollisionObject.pose.
            local = obj.primitive_poses[0].position
            origin = obj.pose.position
            scene_pos = tuple(getattr(local, k) + getattr(origin, k) for k in 'xyz')
            if body.static:
                physical_pos = body.position
            else:
                tr = sensed[body.name]
                physical_pos = tuple(getattr(tr.translation, k) for k in 'xyz')
                if 1 - 2*(tr.rotation.x**2 + tr.rotation.y**2) < 0.98:
                    errors.append(f'{body.name}: unexpected physical tilt')
                if args.mode == 'motion':
                    q = tr.rotation
                    yaw = math.atan2(2*(q.w*q.z+q.x*q.y), 1-2*(q.y*q.y+q.z*q.z))
                    if abs((yaw-expected_yaws[body.name]+math.pi/2) % math.pi-math.pi/2) > 0.035:
                        errors.append(f'{body.name}: physical orientation differs from plan')
            plan_error = math.dist(physical_pos, body.position)
            sync_error = math.dist(scene_pos, physical_pos)
            max_plan_error = max(max_plan_error, plan_error)
            max_sync_error = max(max_sync_error, sync_error)
            if plan_error > 0.005 or sync_error > 0.005:
                errors.append(f'{body.name}: plan error={plan_error:.4f} m, '
                              f'sync error={sync_error:.4f} m')
        result = {'objects': len(bodies), 'gazebo_box_poses': len(sensed),
                  'mode': args.mode, 'motion_status': status,
                  'max_plan_error_mm': max_plan_error * 1000,
                  'max_sync_error_mm': max_sync_error * 1000, 'errors': errors}
        print(json.dumps(result, indent=2))
        if errors:
            raise SystemExit(1)
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
