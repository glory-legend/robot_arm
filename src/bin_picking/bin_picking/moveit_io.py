# -*- coding: utf-8 -*-
"""MoveIt 입출력: 계획/실행/Cartesian/IK/FK 서비스·액션 래퍼.

MoveItIOMixin 은 IntegratedPickPlace 에 섞이는 책임 단위다(상태는 노드가 소유).
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




class MoveItIOMixin:

    def _spin_future(self, future, timeout_sec):
        """future 완료까지 스핀. 완료 시 결과 반환, 미완료(타임아웃/종료)면 None."""
        rclpy.spin_until_future_complete(self, future, timeout_sec=timeout_sec)
        if not future.done():
            return None
        return future.result()

    def _log_failure(self, stage, reason, target=None):
        """실패 단계·사유·관절 상태를 한 블록으로 보기 좋게 출력."""
        self.get_logger().error(
            f'\n╔═══ [{stage}] 실패 ═══\n'
            f'║ 사유: {reason}\n'
            f'║ 현재 관절 상태:\n'
            f'{self._format_joint_report(target)}\n'
            f'╚══════════════════════')

    def wait_for_ready(self, timeout_sec=30.0):
        if not self._move_client.wait_for_server(timeout_sec=timeout_sec):
            raise RuntimeError('MoveGroup 액션 서버 연결 실패')
        if not self._execute_client.wait_for_server(timeout_sec=timeout_sec):
            raise RuntimeError('ExecuteTrajectory 액션 서버 연결 실패')
        if not self._gripper_client.wait_for_server(timeout_sec=timeout_sec):
            raise RuntimeError('Gripper 액션 서버 연결 실패')
        if not self._fk_client.wait_for_service(timeout_sec=timeout_sec):
            raise RuntimeError('compute_fk 서비스 연결 실패')
        if not self._ik_client.wait_for_service(timeout_sec=timeout_sec):
            raise RuntimeError('compute_ik 서비스 연결 실패')
        if not self._cart_client.wait_for_service(timeout_sec=timeout_sec):
            raise RuntimeError('compute_cartesian_path 서비스 연결 실패')
        if not self._scene_client.wait_for_service(timeout_sec=timeout_sec):
            raise RuntimeError('apply_planning_scene 서비스 연결 실패')
        start = time.time()
        while self._joint_state is None:
            rclpy.spin_once(self, timeout_sec=0.1)
            if time.time() - start > timeout_sec:
                raise RuntimeError('joint_states 수신 실패')
        self.get_logger().info('모든 서버/서비스/joint_states 준비 완료')

    # =========================================================
    # SRDF에서 이름 포즈 읽기 (ex07)
    # =========================================================
    def load_named_pose(self, name, timeout_sec=10.0):
        client = AsyncParameterClient(self, 'move_group')
        if not client.wait_for_services(timeout_sec=timeout_sec):
            raise RuntimeError('move_group 파라미터 서비스 연결 실패')
        future = client.get_parameters(['robot_description_semantic'])
        result = self._spin_future(future, timeout_sec)
        if result is None or not result.values:
            raise RuntimeError('robot_description_semantic 파라미터 수신 실패(타임아웃)')
        srdf_xml = result.values[0].string_value
        if not srdf_xml:
            raise RuntimeError('robot_description_semantic 값이 비어 있음')

        root = ET.fromstring(srdf_xml)
        for gs in root.findall('group_state'):
            if (gs.attrib.get('group') == self.PLANNING_GROUP
                    and gs.attrib.get('name') == name):
                return {j.attrib['name']: float(j.attrib.get('value', '0'))
                        for j in gs.findall('joint')}
        raise RuntimeError(f'SRDF group_state "{name}" 없음')

    # =========================================================
    # MoveGroup 빌딩블록 — Constraints / MotionPlanRequest (ex07)
    # =========================================================
    def _make_joint_constraints(self, joint_values, tol=0.01):
        c = Constraints()
        for jname, val in joint_values.items():
            c.joint_constraints.append(JointConstraint(
                joint_name=jname, position=val,
                tolerance_above=tol, tolerance_below=tol, weight=1.0,
            ))
        return c

    def _make_position_constraint(self, pose, tol=0.01):
        pc = PositionConstraint()
        pc.header.frame_id = self.REFERENCE_FRAME
        pc.link_name = self.END_EFFECTOR_LINK
        pc.target_point_offset = Vector3(x=0.0, y=0.0, z=0.0)
        bv = BoundingVolume()
        sphere = SolidPrimitive()
        sphere.type = SolidPrimitive.SPHERE
        sphere.dimensions = [tol]
        bv.primitives.append(sphere)
        sp = Pose()
        sp.position = Point(
            x=pose.position.x, y=pose.position.y, z=pose.position.z)
        sp.orientation.w = 1.0
        bv.primitive_poses.append(sp)
        pc.constraint_region = bv
        pc.weight = 1.0
        return pc

    def _make_orientation_constraint(self, pose, tol=0.05):
        oc = OrientationConstraint()
        oc.header.frame_id = self.REFERENCE_FRAME
        oc.link_name = self.END_EFFECTOR_LINK
        oc.orientation = pose.orientation
        oc.absolute_x_axis_tolerance = tol
        oc.absolute_y_axis_tolerance = tol
        oc.absolute_z_axis_tolerance = tol
        oc.weight = 1.0
        return oc

    def _make_plan_request(self, vel=0.3, acc=0.3, attempts=10,
                           plan_time=15.0, planner_id=''):
        req = MotionPlanRequest()
        req.group_name = self.PLANNING_GROUP
        req.num_planning_attempts = attempts
        req.allowed_planning_time = plan_time
        req.max_velocity_scaling_factor = vel
        req.max_acceleration_scaling_factor = acc
        if planner_id:
            req.planner_id = planner_id   # ex10: OMPL 플래너 명시
        return req

    # =========================================================
    # 계획만 받기 — plan_only=True (ex07)
    # =========================================================
    def _send_move_goal(self, req):
        goal = MoveGroup.Goal()
        goal.request = req
        goal.planning_options = PlanningOptions(plan_only=True)
        sf = self._move_client.send_goal_async(goal)
        handle = self._spin_future(sf, self.ACCEPT_TIMEOUT)
        if handle is None or not handle.accepted:
            return MoveItErrorCodes.PLANNING_FAILED, None
        rf = handle.get_result_async()
        result = self._spin_future(rf, self.RESULT_TIMEOUT)
        if result is None:
            return MoveItErrorCodes.TIMED_OUT, None
        res = result.result
        return res.error_code.val, res.planned_trajectory

    def plan_to_joint_goal(self, joint_values, vel=0.3):
        req = self._make_plan_request(vel=vel, acc=vel)
        req.goal_constraints.append(self._make_joint_constraints(joint_values))
        code_val, traj = self._send_move_goal(req)
        if code_val != MoveItErrorCodes.SUCCESS:
            self._log_failure(
                '관절 목표 계획',
                f'MoveIt 오류 {self.error_name(code_val)} ({code_val})',
                target=joint_values)
        return code_val == MoveItErrorCodes.SUCCESS, traj

    def plan_to_pose_goal(self, pose, vel=0.3, planner_id=''):
        req = self._make_plan_request(vel=vel, acc=vel, planner_id=planner_id)
        c = Constraints()
        c.position_constraints.append(self._make_position_constraint(pose))
        c.orientation_constraints.append(
            self._make_orientation_constraint(pose))
        req.goal_constraints.append(c)
        code_val, traj = self._send_move_goal(req)
        if code_val != MoveItErrorCodes.SUCCESS:
            self.get_logger().warn(
                f'계획 실패 원인: {self.error_name(code_val)} ({code_val})')
        return code_val == MoveItErrorCodes.SUCCESS, traj

    def compute_cartesian(self, waypoints, max_step=None, vel=0.3,
                          start_joints=None):
        """waypoints를 직선 보간. (trajectory, fraction) 반환.

        start_joints(관절 dict)를 주면 그 '가상 자세'에서 시작하는 것으로
        계획한다(실행 없음) — plan-only 롤아웃에서 '접근 자세에서 하강하면
        어떻게 되나'를 실제로 팔을 옮기지 않고 미리 계산할 때 쓴다.
        None 이면 현재 실측 자세.
        """
        if start_joints is None and self._arm_joint_positions() is None:
            self.get_logger().error(
                'Cartesian 시작 상태 구성 실패 — /joint_states에 팔 7관절 미도착')
            return None, 0.0
        req = GetCartesianPath.Request()
        req.header.frame_id = self.REFERENCE_FRAME
        req.start_state = (self._arm_state_from(start_joints)
                           if start_joints is not None
                           else self._current_arm_state())
        req.group_name = self.PLANNING_GROUP
        req.link_name = self.END_EFFECTOR_LINK
        req.waypoints = waypoints
        req.max_step = max_step if max_step is not None else self.CART_MAX_STEP
        # jump_threshold=0.0은 관절 점프 검출을 '비활성화'한다. 특이점/손목
        # 뒤집힘(wrist-flip) 궤적을 그대로 통과시키므로, revolute 기준 완만한
        # 값으로 급격한 관절 점프를 걸러낸다.
        # jump_threshold 는 평균 관절스텝 대비 '상대 배수'라 rad 가 아니다.
        # revolute 절대 임계(rad)를 쓰려면 아래 전용 필드를 써야 한다.
        req.jump_threshold = 0.0
        if hasattr(req, 'revolute_jump_threshold'):
            req.revolute_jump_threshold = 0.5
        # Cartesian 실행 속도도 일반 계획과 동일 스케일로 맞춤(파지 직전 하강이
        # 풀스피드로 나가지 않도록). 구버전 srv엔 해당 필드가 없어 hasattr로 방어.
        if hasattr(req, 'max_velocity_scaling_factor'):
            req.max_velocity_scaling_factor = vel
            req.max_acceleration_scaling_factor = vel
        req.avoid_collisions = True   # ex09: 충돌 객체를 알고 보간
        fut = self._cart_client.call_async(req)
        resp = self._spin_future(fut, self.SERVICE_TIMEOUT)
        if resp is None or resp.error_code.val != MoveItErrorCodes.SUCCESS:
            return None, 0.0
        return resp.solution, resp.fraction

    def make_vertical_waypoints(self, x, y, z_from, z_to, orientation):
        """수직 하강/상승 waypoint 열 생성 (DESCENT_STEP 간격, 자세 고정)"""
        waypoints = []
        distance = z_to - z_from
        n = max(1, int(round(abs(distance) / self.DESCENT_STEP)))
        for i in range(1, n + 1):
            wp = Pose()
            wp.position = Point(x=x, y=y, z=z_from + distance * i / n)
            wp.orientation = orientation
            waypoints.append(wp)
        return waypoints

    # =========================================================
    # FK 미리보기 (ex07의 다운샘플 버전)
    # =========================================================
    def trajectory_to_ee_path(self, trajectory, max_points=60):
        jt = trajectory.joint_trajectory
        total = len(jt.points)
        if total == 0:
            return []
        step = max(1, total // max_points)
        indices = list(range(0, total, step))
        if indices[-1] != total - 1:
            indices.append(total - 1)
        pts = []
        for idx in indices:
            req = GetPositionFK.Request()
            req.header.frame_id = self.REFERENCE_FRAME
            req.fk_link_names = [self.END_EFFECTOR_LINK]
            rs = RobotState()
            rs.is_diff = True
            rs.joint_state.name = list(jt.joint_names)
            rs.joint_state.position = list(jt.points[idx].positions)
            req.robot_state = rs
            fut = self._fk_client.call_async(req)
            resp = self._spin_future(fut, self.SERVICE_TIMEOUT)
            if (resp is not None
                    and resp.error_code.val == MoveItErrorCodes.SUCCESS
                    and resp.pose_stamped):
                p = resp.pose_stamped[0].pose.position
                pts.append((p.x, p.y, p.z))
        return pts

    def _ik_joint_goal(self, pose, seed=None):
        """[접근 자세 안정화] pose 의 IK 를 'ready 근처' 관절해로 푼다.

        Approach 를 pose 목표로 RRT 에 맡기면 매번 임의의 관절해가 나온다 —
        팔꿈치 뒤집힘, J1 이 ±100° 이상 돌아간 몸통 감기, J2/J7 한계 직전 등
        (20260721 15:44 로그: J7 +172.8° ⛔, J2 -102.2° ⛔). 그 뒤틀린 시작
        자세에서 수직 하강 직선을 풀면 IK 가 관절 한계/점프에 걸려 fraction
        44~97% 에서 잘린다 — 이번 실행 전 실패의 공통 원인.

        ready 자세를 시드로 IK 를 풀면 '자연스러운 팔 형태'에 가장 가까운 해가
        나오고, 접근을 그 관절 목표로 계획하면 하강 시작 형태가 매 시도 동일하고
        온건해진다. 반환: {관절: 값} / 실패 시 None(호출부가 pose 목표로 폴백).
        """
        req = GetPositionIK.Request()
        req.ik_request.group_name = self.PLANNING_GROUP
        req.ik_request.ik_link_name = self.END_EFFECTOR_LINK
        req.ik_request.avoid_collisions = True
        ps = PoseStamped()
        ps.header.frame_id = self.REFERENCE_FRAME
        ps.pose = pose
        req.ik_request.pose_stamped = ps
        rs = RobotState()
        js = JointState()
        seed = seed if seed is not None else self._ready_target
        js.name = list(seed.keys())
        js.position = [float(v) for v in seed.values()]
        rs.joint_state = js
        req.ik_request.robot_state = rs
        req.ik_request.timeout = Duration(sec=1)
        fut = self._ik_client.call_async(req)
        resp = self._spin_future(fut, self.SERVICE_TIMEOUT)
        if resp is None or resp.error_code.val != MoveItErrorCodes.SUCCESS:
            return None
        lookup = dict(zip(resp.solution.joint_state.name,
                          resp.solution.joint_state.position))
        if not all(j in lookup for j in self.ARM_JOINTS):
            return None
        return {j: float(lookup[j]) for j in self.ARM_JOINTS}

    def _current_tcp_xyz(self):
        """[Issue A] 현재 관절 상태를 FK 로 풀어 실제 TCP (x,y,z). 실패하면 None.

        '계획이 100% 였다'와 '실제로 그 높이까지 갔다'는 다른 문제다(컨트롤러가
        중간에 멈추거나 goal tolerance 안에서 일찍 끝날 수 있다). 파지 직전에는
        계획값이 아니라 이 실측값을 믿는다.
        """
        cur = self._arm_joint_positions()
        if cur is None:
            return None
        req = GetPositionFK.Request()
        req.header.frame_id = self.REFERENCE_FRAME
        req.fk_link_names = [self.END_EFFECTOR_LINK]
        rs = RobotState()
        rs.is_diff = True
        rs.joint_state.name = list(cur.keys())
        rs.joint_state.position = [float(v) for v in cur.values()]
        req.robot_state = rs
        fut = self._fk_client.call_async(req)
        resp = self._spin_future(fut, self.SERVICE_TIMEOUT)
        if (resp is None or resp.error_code.val != MoveItErrorCodes.SUCCESS
                or not resp.pose_stamped):
            return None
        p = resp.pose_stamped[0].pose.position
        return (p.x, p.y, p.z)

    def verify_descent_reached(self, target_z, label=''):
        """[Issue A] 하강 뒤 실측 TCP z 가 목표 파지 높이에 도달했는지 확인.

        여기서 걸러내지 못하면 볼트보다 한참 위에서 손가락을 닫아 '빈손'이 된다.
        도달/미달 여부와 수치를 항상 로그로 남긴다.
        """
        xyz = self._current_tcp_xyz()
        if xyz is None:
            self.get_logger().error(
                f'[{label}] 하강 검증 불가 — FK 실패. 안전하게 실패 처리합니다')
            return False
        achieved = xyz[2]
        gap = achieved - target_z
        ok = self._descent_reached(achieved, target_z)
        detail = (f'실측 TCP z={achieved:.4f} / 목표 {target_z:.4f} '
                  f'(초과 {gap * 1000:+.1f}mm, 허용 '
                  f'{self.GRASP_Z_TOL * 1000:.0f}mm)')
        if ok:
            self.get_logger().info(f'[{label}] 하강 완주 확인 — {detail}')
        else:
            self.get_logger().error(
                f'[{label}] 하강 미달 — {detail}. 이 높이에서 손가락을 닫으면 '
                f'빈손이므로 파지를 중단합니다')
        return ok

    # =========================================================
    # 실행 + 통합 함수들
    # =========================================================
    def execute_trajectory(self, trajectory):
        if trajectory is None or not trajectory.joint_trajectory.points:
            self._log_failure('궤적 실행', '빈 궤적 — 실행할 waypoint 없음')
            return False
        g = ExecuteTrajectory.Goal()
        g.trajectory = trajectory
        sf = self._execute_client.send_goal_async(g)
        handle = self._spin_future(sf, self.ACCEPT_TIMEOUT)
        if handle is None or not handle.accepted:
            self._log_failure('궤적 실행', 'ExecuteTrajectory goal 거부/타임아웃')
            return False
        rf = handle.get_result_async()
        result = self._spin_future(rf, self.RESULT_TIMEOUT)
        if result is None:
            self._log_failure('궤적 실행', '결과 타임아웃 — 컨트롤러 무응답')
            return False
        code = result.result.error_code.val
        if code != MoveItErrorCodes.SUCCESS:
            self._log_failure(
                '궤적 실행', f'컨트롤러 오류 {self.error_name(code)} ({code})')
            return False
        return True

    def plan_viz_execute(self, pose, vel=0.3, label='', planners=None):
        """일반 계획: 여러 OMPL 플래너를 순차 시도(ex10) →
        첫 성공 채택 → FK 미리보기(주황) → execute.
        planners=None이면 PLANNER_FALLBACK 목록을 순서대로 시도."""
        if planners is None:
            planners = self.PLANNER_FALLBACK
        ok, traj, used = False, None, ''
        for pid in planners:
            ok, traj = self.plan_to_pose_goal(pose, vel=vel, planner_id=pid)
            if ok and traj is not None:
                used = pid
                break
            self.get_logger().warn(f'{label}: {pid} 계획 실패 — 다음 플래너 시도')
        if not ok or traj is None:
            self._log_failure(
                f'{label} 자세 계획',
                f'모든 플래너 실패 ({", ".join(planners)}) — 목표 pos='
                f'({pose.position.x:.3f}, {pose.position.y:.3f}, '
                f'{pose.position.z:.3f})')
            return False
        pts = self.trajectory_to_ee_path(traj)
        if pts:
            self.get_logger().info(
                f'{label}: {used}로 계획, 경로 {len(pts)}점 미리보기(주황)')
            self.publish_ee_path(pts, self.COLOR_GENERAL)
        return self.execute_trajectory(traj)

    def plan_viz_execute_joint(self, joint_values, vel=0.3, label=''):
        ok, traj = self.plan_to_joint_goal(joint_values, vel=vel)
        if not ok or traj is None:
            self.get_logger().error(f'{label}: 계획 실패')
            return False
        pts = self.trajectory_to_ee_path(traj)
        if pts:
            self.publish_ee_path(pts, self.COLOR_GENERAL)
        return self.execute_trajectory(traj)

    def cartesian_viz_execute(self, waypoints, label='', vel=0.3,
                              allow_fallback=True, min_fraction=None,
                              log_fail=True):
        """Cartesian 직선: 보간 → fraction 게이트 → 미리보기(시안) → execute.
        달성률이 낮으면 직선을 포기하고 마지막 waypoint로 일반 계획(곡선) 폴백.

        min_fraction: 이 구간 전용 게이트. None 이면 MIN_FRACTION(0.9).
          ⚠ 0.9 는 '이동' 구간 기준이다. 파지 하강처럼 끝점에 도달하는 것 자체가
            목적인 구간에서는 90% 가 곧 '볼트를 한참 위에서 놓침'을 뜻하므로
            반드시 GRASP_MIN_FRACTION 같은 엄격한 값을 넘겨야 한다.
        """
        gate = self.MIN_FRACTION if min_fraction is None else min_fraction
        traj, fraction = self.compute_cartesian(waypoints, vel=vel)
        z_from = waypoints[0].position.z if waypoints else 0.0
        z_to = waypoints[-1].position.z if waypoints else 0.0
        self.get_logger().info(
            f'{label}: 달성률 {fraction * 100:.1f}% '
            f'(게이트 {gate * 100:.1f}%, 이 달성률의 TCP z ≈ '
            f'{self._fraction_to_z(z_from, z_to, fraction):.4f} / 목표 {z_to:.4f})')
        if traj is None or fraction < gate:
            # log_fail=False: '직선 시도 → 안 되면 다른 방법' 흐름의 1차 시도라
            # 실패가 예정된 분기일 수 있다 → 큰 에러 박스로 로그를 오염시키지 않음
            if log_fail:
                reached = int(round(fraction * len(waypoints)))
                self._log_failure(
                    f'{label} Cartesian',
                    f'달성률 {fraction * 100:.1f}% < {gate * 100:.1f}% '
                    f'(waypoint {reached}/{len(waypoints)}까지만 직선 보간). '
                    f'직선을 포기하고 일반 계획(곡선 허용)으로 폴백 — 경로가 시안 대신 '
                    f'주황으로 표시됩니다')
            if not allow_fallback:
                # 무더기 속 하강 등에서는 곡선 폴백이 통 안을 쓸어버리므로 금지
                if log_fail:
                    self.get_logger().warn(
                        f'{label}: 곡선 폴백 금지 구간 — 실패 처리')
                return False
            return self.plan_viz_execute(
                waypoints[-1], vel=min(vel, 0.15), label=f'{label}(곡선폴백)')
        pts = self.trajectory_to_ee_path(traj)
        if pts:
            self.get_logger().info(f'{label}: 직선 경로 미리보기(시안)')
            self.publish_ee_path(pts, self.COLOR_CART)
        return self.execute_trajectory(traj)
