# -*- coding: utf-8 -*-
"""RViz 마커(경로/라벨) 발행.

MarkersMixin 은 IntegratedPickPlace 에 섞이는 책임 단위다(상태는 노드가 소유).
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




class MarkersMixin:

    def _republish_markers(self):
        if self._markers.markers:
            self._marker_pub.publish(self._markers)

    def _next_id(self):
        self._marker_id += 1
        return self._marker_id

    def publish_ee_path(self, ee_points, color):
        """끝단 경로 LINE_STRIP (ns/id 고정 — 매번 교체)"""
        if not ee_points:
            return
        line = Marker()
        line.header.frame_id = self.REFERENCE_FRAME
        line.header.stamp = self.get_clock().now().to_msg()
        line.ns = 'ee_path'
        line.id = 0
        line.type = Marker.LINE_STRIP
        line.action = Marker.ADD
        line.pose.orientation.w = 1.0
        line.scale.x = 0.008
        line.color = color
        line.points = [Point(x=p[0], y=p[1], z=p[2]) for p in ee_points]
        self._markers.markers = [
            m for m in self._markers.markers if (m.ns, m.id) != ('ee_path', 0)
        ]
        self._markers.markers.append(line)
        self._marker_pub.publish(self._markers)

    def clear_ee_path(self):
        delete = Marker()
        delete.header.frame_id = self.REFERENCE_FRAME
        delete.header.stamp = self.get_clock().now().to_msg()
        delete.ns = 'ee_path'
        delete.id = 0
        delete.action = Marker.DELETE
        ma = MarkerArray()
        ma.markers.append(delete)
        self._markers.markers = [
            m for m in self._markers.markers if (m.ns, m.id) != ('ee_path', 0)
        ]
        self._marker_pub.publish(ma)

    # =========================================================
    # 위치 라벨 마커
    # =========================================================
    def add_label_marker(self, pos, label):
        text = Marker()
        text.header.frame_id = self.REFERENCE_FRAME
        text.header.stamp = self.get_clock().now().to_msg()
        text.ns = 'labels'
        text.id = self._next_id()
        text.type = Marker.TEXT_VIEW_FACING
        text.action = Marker.ADD
        text.pose.position = Point(x=pos[0], y=pos[1], z=pos[2] + 0.10)
        text.pose.orientation.w = 1.0
        text.scale.z = 0.05
        text.color = self.COLOR_TEXT
        text.text = label   # RViz2 한글 렌더링 이슈 회피 위해 영문 권장
        self._markers.markers.append(text)
        self._marker_pub.publish(self._markers)
