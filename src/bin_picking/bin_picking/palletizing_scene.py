"""Gazebo 실측 박스 자세를 MoveIt 충돌체와 RViz 박스 라벨로 동기화한다.

PDF 1단계 독립 노드. 모션/흡착은 실행하지 않는다. 모든 박스의 pose 수신 및
ApplyPlanningScene 성공 뒤에만 STAGE1_READY를 기록한다.
"""
import json
import math
import time

import rclpy
from rclpy.node import Node
from rclpy.qos import QoSProfile, DurabilityPolicy
from geometry_msgs.msg import Pose
from moveit_msgs.msg import CollisionObject, ObjectColor, PlanningScene
from moveit_msgs.srv import ApplyPlanningScene
from shape_msgs.msg import SolidPrimitive
from std_msgs.msg import String
from tf2_msgs.msg import TFMessage
from visualization_msgs.msg import Marker, MarkerArray

from bin_picking.palletizing_layout import make_layout
from bin_picking.palletizing_planner import demo_boxes, plan_boxes
from bin_picking.robot_profiles import get


class PalletizingScene(Node):
    def __init__(self):
        super().__init__('palletizing_scene')
        model = self.declare_parameter('robot_model', 'fr3').value
        self.frame = get(model).arm.base_frame
        seed = self.declare_parameter('seed', 20260909).value
        count = self.declare_parameter('box_count', 12).value
        strategy = self.declare_parameter('strategy', 'compact').value
        self.plan = plan_boxes(demo_boxes(seed, count), strategy=strategy)
        self.bodies = make_layout(seed, count, strategy)
        self.poses = {}
        self.subscriptions_ = [
            self.create_subscription(
                TFMessage, f'/model/{body.name}/pose',
                lambda msg, name=body.name: self._on_pose(name, msg), 10)
            for body in self.bodies if not body.static
        ]
        self.client = self.create_client(ApplyPlanningScene, '/apply_planning_scene')
        qos = QoSProfile(depth=1, durability=DurabilityPolicy.TRANSIENT_LOCAL)
        self.labels = self.create_publisher(MarkerArray, '/palletizing/labels', qos)
        self.plan_pub = self.create_publisher(String, '/packing/plan', qos)
        self.plan_pub.publish(String(data=json.dumps(self.plan.to_dict())))
        if self.plan.rejected:
            self.get_logger().warning(f'Unplaced boxes: {self.plan.rejected}')
        self.future = None
        self.ready = False
        self.started = time.monotonic()
        self.sent_at = None
        self.create_timer(0.5, self._tick)

    def _on_pose(self, name, message):
        # PosePublisher의 모델 pose만 사용한다. link 상대좌표는 제외한다.
        for transform in message.transforms:
            if transform.child_frame_id != name:
                continue
            t, q = transform.transform.translation, transform.transform.rotation
            if not all(math.isfinite(v) for v in (t.x, t.y, t.z, q.x, q.y, q.z, q.w)):
                continue
            if abs(q.x*q.x + q.y*q.y + q.z*q.z + q.w*q.w - 1) > 0.01:
                continue
            pose = Pose()
            pose.position.x, pose.position.y, pose.position.z = t.x, t.y, t.z
            pose.orientation = q
            self.poses[name] = pose

    def _scene(self):
        scene = PlanningScene()
        scene.is_diff = True
        scene.robot_state.is_diff = True
        labels = MarkerArray()
        for index, body in enumerate(self.bodies):
            pose = Pose()
            pose.position.x, pose.position.y, pose.position.z = body.position
            pose.orientation.w = 1.0
            if not body.static:
                pose = self.poses[body.name]
            obj = CollisionObject()
            obj.id, obj.header.frame_id = body.name, self.frame
            primitive = SolidPrimitive()
            primitive.type, primitive.dimensions = SolidPrimitive.BOX, list(body.size)
            obj.primitives, obj.primitive_poses = [primitive], [pose]
            obj.operation = CollisionObject.ADD
            scene.world.collision_objects.append(obj)
            color = ObjectColor()
            color.id = body.name
            color.color.r, color.color.g, color.color.b, color.color.a = body.color
            scene.object_colors.append(color)
            marker = Marker()
            marker.header.frame_id = self.frame
            marker.ns, marker.id = 'palletizing', index
            marker.type, marker.action = Marker.TEXT_VIEW_FACING, Marker.ADD
            marker.pose.position.x = pose.position.x
            marker.pose.position.y = pose.position.y
            marker.pose.position.z = pose.position.z + body.size[2] / 2 + 0.025
            marker.pose.orientation.w = 1.0
            marker.scale.z = 0.018
            marker.color.r = marker.color.g = marker.color.b = marker.color.a = 1.0
            marker.text = body.name.removeprefix('pallet_')
            labels.markers.append(marker)
        return scene, labels

    def _tick(self):
        now = time.monotonic()
        if not self.ready and now - self.started > 90:
            missing = [b.name for b in self.bodies if not b.static and b.name not in self.poses]
            raise RuntimeError(f'Stage 1 readiness timeout: missing poses={missing}, '
                               f'MoveIt service={self.client.service_is_ready()}')
        if self.future is not None:
            if not self.future.done():
                if now - self.sent_at > 15:
                    raise RuntimeError('ApplyPlanningScene response timed out')
                return
            response = self.future.result()
            self.future = None
            if response is None or not response.success:
                raise RuntimeError('MoveIt rejected palletizing scene')
            if not self.ready:
                self.ready = True
                self.get_logger().info(
                    f'STAGE1_READY: {len(self.bodies)} collision objects; '
                    'Gazebo box poses received, MoveIt scene applied')
                self.get_logger().info(json.dumps(self.plan.to_dict()['metrics']))
        if not self.client.service_is_ready():
            return
        if any(not b.static and b.name not in self.poses for b in self.bodies):
            return
        scene, labels = self._scene()
        request = ApplyPlanningScene.Request()
        request.scene = scene
        self.future = self.client.call_async(request)
        self.sent_at = now
        self.labels.publish(labels)


def main(args=None):
    rclpy.init(args=args)
    node = None
    try:
        node = PalletizingScene()
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        if node is not None:
            node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()
