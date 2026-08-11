#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""등록한 로봇 모델의 **실제 도달 범위**를 측정한다 (프로파일 workspace 값 유도용).

프로파일의 `workspace.*` 는 카탈로그 스펙이 아니라 **이 설치 상태에서의 실측값**
이어야 한다(docs/robot_profiles.md §3). 그런데 사람이 눈대중으로 채우면 낙관적으로
적기 쉽고, 그러면 파이프라인이 "닿는다"고 판단해 볼트당 수십 초를 낭비한다.

이 도구는 통 영역을 격자로 훑으며 **파이프라인이 실제로 쓰는 파지 자세 그대로**
`compute_ik` 를 걸어, 어디까지 닿는지 재 준다.

사용 (시뮬 또는 실기가 떠 있어야 한다 — move_group 의 compute_ik 를 쓴다):

    ros2 launch bin_picking franka_gazebo_moveit.launch.py robot_model:=<모델> rviz:=false
    ros2 run bin_picking measure_workspace --model <모델>

⚠ 여기서 나오는 값은 **IK 해가 있는가**만 본다. 실제 파지에는 하강 Cartesian
  달성률·충돌·개구까지 걸리므로, 측정값은 상한이다. 프로파일에는 이 값에서
  약간 보수적으로(안쪽으로) 잡아 넣는 것이 안전하다.
"""
import argparse
import math
import os
import sys

import numpy as np


def main(argv=None):
    ap = argparse.ArgumentParser(prog='measure_workspace')
    ap.add_argument('--model', default=None,
                    help='측정할 등록 모델 이름 (기본: 활성 모델)')
    ap.add_argument('--grasp-z', type=float, default=None,
                    help='파지 높이 TCP z (기본: 프로파일 유도 GRASP_FLOOR_Z)')
    ap.add_argument('--step', type=float, default=0.010,
                    help='격자 간격 m (기본 %(default)s)')
    ap.add_argument('--timeout', type=float, default=90.0,
                    help='전체 측정 제한 시간(초)')
    args = ap.parse_args(argv)

    # config 임포트 **전에** 활성 모델을 고정해야 한다 — apply_profile 이
    # 임포트 시점에 돌기 때문이다.
    if args.model:
        os.environ['BIN_PICKING_ROBOT_MODEL'] = args.model

    import rclpy
    from rclpy.node import Node
    from geometry_msgs.msg import Pose, Point
    from moveit_msgs.srv import GetPositionIK
    from moveit_msgs.msg import PositionIKRequest, RobotState
    from sensor_msgs.msg import JointState

    from bin_picking.config import PickPlaceConfig
    from bin_picking.geometry import GeometryMixin
    from bin_picking.bolt_scene import BIN_XYZ, BIN_OUTER, BIN_THICK

    class _Geom(PickPlaceConfig, GeometryMixin):
        pass

    C = _Geom
    grasp_z = args.grasp_z if args.grasp_z is not None else C.GRASP_FLOOR_Z

    # 파이프라인이 실제로 쓰는 자세: 수직 접근 + 볼트축이 x 방향인 경우.
    # (도달성은 볼트축 방향에 크게 좌우되지 않으므로 대표 자세 하나로 훑는다.)
    quat = C().grasp_quat_for_axis(np.array([1.0, 0.0, 0.0]))
    if quat is None:
        print('⛔ 파지 자세를 만들 수 없습니다 — 프로파일을 확인하세요', file=sys.stderr)
        return 2

    inner_hx = BIN_OUTER[0] / 2.0 - BIN_THICK
    inner_hy = BIN_OUTER[1] / 2.0 - BIN_THICK

    rclpy.init(args=None)
    node = Node('measure_workspace')
    cli = node.create_client(GetPositionIK, 'compute_ik')
    if not cli.wait_for_service(timeout_sec=15.0):
        print('⛔ compute_ik 서비스가 없습니다 — move_group 이 떠 있는지 확인하세요',
              file=sys.stderr)
        node.destroy_node()
        rclpy.shutdown()
        return 2

    print(f'모델        : {C.ROBOT_MODEL}')
    print(f'planning grp: {C.PLANNING_GROUP}   TCP: {C.END_EFFECTOR_LINK}')
    print(f'파지 높이   : z = {grasp_z:.4f} m')
    print(f'통 안쪽     : x {BIN_XYZ[0]-inner_hx:.3f}~{BIN_XYZ[0]+inner_hx:.3f}, '
          f'y {-inner_hy:+.3f}~{+inner_hy:+.3f}')
    print()

    def ik_ok(x, y, z):
        req = GetPositionIK.Request()
        r = PositionIKRequest()
        r.group_name = C.PLANNING_GROUP
        r.ik_link_name = C.END_EFFECTOR_LINK
        r.avoid_collisions = False       # 순수 기구학 도달성만 본다
        r.pose_stamped.header.frame_id = C.REFERENCE_FRAME
        r.pose_stamped.pose = Pose(position=Point(x=float(x), y=float(y),
                                                  z=float(z)),
                                   orientation=quat)
        r.robot_state = RobotState()
        r.robot_state.is_diff = True
        r.robot_state.joint_state = JointState()
        r.timeout.sec = 0
        r.timeout.nanosec = 30_000_000
        req.ik_request = r
        fut = cli.call_async(req)
        rclpy.spin_until_future_complete(node, fut, timeout_sec=3.0)
        res = fut.result()
        return bool(res and res.error_code.val == 1)

    # --- 파지 높이에서의 도달 격자 ---
    xs = np.arange(BIN_XYZ[0] - inner_hx, BIN_XYZ[0] + inner_hx + 1e-9, args.step)
    ys = np.arange(-inner_hy, inner_hy + 1e-9, args.step)
    reach = []
    print('파지 높이 도달 격자 (o=도달, .=불가)  ※ 세로 y, 가로 x')
    for y in ys[::-1]:
        row = ''
        for x in xs:
            ok = ik_ok(x, y, grasp_z)
            row += 'o' if ok else '.'
            if ok:
                reach.append((x, y))
        print(f'  y={y:+.3f} |{row}')
    print(f'          ' + ' ' * 0 + ''.join('' for _ in xs))
    print(f'  x = {xs[0]:.2f} … {xs[-1]:.2f}')
    print()

    if not reach:
        print('⛔ 파지 높이에서 도달 가능한 지점이 하나도 없습니다.')
        print('   팔 설치 위치(통과의 거리)나 파지 높이를 먼저 확인하세요.')
        node.destroy_node(); rclpy.shutdown()
        return 1

    ry = max(abs(y - BIN_XYZ[1]) for _x, y in reach)
    rx = max(x for x, _y in reach)
    print('=== 프로파일 workspace 에 넣을 값 (측정 상한) ===')
    print(f'  reach_y_max: {ry:.3f}      # |y − 통중심| 최대 도달')
    print(f'  reach_x_far: {rx:.3f}      # 도달한 가장 먼 x')

    # --- 접근 높이 후보 ---
    print()
    print('접근 높이별 통 중심 상공 도달 여부:')
    best = None
    for z in (0.15, 0.20, 0.25, 0.30, 0.35, 0.40):
        ok = ik_ok(BIN_XYZ[0], BIN_XYZ[1], z)
        print(f'   z={z:.2f} → {"도달" if ok else "불가"}')
        if ok and best is None:
            best = z
    if best is not None:
        print(f'\n  approach_height 후보: {best:.2f} (도달하는 가장 낮은 높이 — '
              f'하강 직선이 짧을수록 IK 실패 구간이 준다)')

    node.destroy_node()
    rclpy.shutdown()
    return 0


if __name__ == '__main__':
    sys.exit(main())
