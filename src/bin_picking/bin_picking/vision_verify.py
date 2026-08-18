#!/usr/bin/env python3
"""비전 정확도 검증 노드 — bolt_vision 추정 vs Gazebo 정답 비교.

§5c 비전 엔드투엔드 검증용. bolt_vision 이 /next_bolt_pose 로 발행하는 추정
자세를, Gazebo ground-truth(/model/bolt_i/pose)와 대조해 위치/방위 오차를 측정한다.

사용:
  터미널1: ros2 launch bin_picking franka_gazebo_moveit.launch.py
  터미널2: ros2 launch bin_picking spawn_bolts.launch.py
  터미널3: ros2 launch bin_picking vision_pipeline.launch.py
  터미널4: ros2 run bin_picking bolt_vision
  터미널5: ros2 run bin_picking vision_verify [--duration 30]

  --duration: 측정 시간(초). 기본 30. 끝나면 요약 통계를 출력하고 종료한다.

출력:
  매 비전 발행마다 가장 가까운 ground-truth 볼트와 매칭해 위치 오차(mm)·
  축 각도 오차(°)를 로그로 남기고, 종료 시 전체 통계(평균/중앙/최대/표준편차)를
  콘솔에 출력한다.
"""
import math
import re
import sys
import threading
import time

import numpy as np
import rclpy
import tf_transformations
from rclpy.node import Node
from rclpy.parameter import Parameter
from rclpy.qos import QoSProfile, ReliabilityPolicy

from geometry_msgs.msg import PoseStamped
from tf2_msgs.msg import TFMessage

from bin_picking import robot_profiles
from bin_picking.bolt_scene import BOLT_LAYOUT

_BOLT_ID_RE = re.compile(r'(?:^|::|/)(bolt_\d+)(?=::|/|$)')


class VisionVerify(Node):

    POSE_TOPIC_FMT = '/model/{}/pose'
    VISION_TOPIC = '/next_bolt_pose'
    BASE_FRAME = robot_profiles.active_profile().arm.base_frame

    def __init__(self, duration_sec=30.0):
        super().__init__(
            'vision_verify',
            parameter_overrides=[Parameter('use_sim_time', value=True)],
        )
        self._duration = duration_sec
        self._gt = {}
        self._samples = []
        self._lock = threading.Lock()
        self._start_time = None

        bolt_ids = [f'bolt_{i}' for i in range(len(BOLT_LAYOUT))]
        qos_tf = QoSProfile(depth=10)
        qos_tf.reliability = ReliabilityPolicy.BEST_EFFORT
        for bid in bolt_ids:
            topic = self.POSE_TOPIC_FMT.format(bid)
            self.create_subscription(
                TFMessage, topic,
                lambda msg, b=bid: self._gt_cb(msg, b),
                qos_tf)

        self.create_subscription(
            PoseStamped, self.VISION_TOPIC, self._vision_cb, 10)

        self.get_logger().info(
            f'=== 비전 정확도 검증 === 볼트 {len(bolt_ids)}개 GT 구독 + '
            f'{self.VISION_TOPIC} 비전 구독. {self._duration}초간 측정.')

    @staticmethod
    def _bolt_id(name):
        if not name:
            return None
        m = _BOLT_ID_RE.search(name.lstrip('/'))
        return m.group(1) if m else None

    def _gt_cb(self, msg, bolt_id):
        for t in msg.transforms:
            child_bid = self._bolt_id(t.child_frame_id)
            if child_bid is not None and child_bid != bolt_id:
                continue
            if self._bolt_id(t.header.frame_id) is not None:
                continue
            tr = t.transform.translation
            q = t.transform.rotation
            with self._lock:
                self._gt[bolt_id] = (
                    np.array([tr.x, tr.y, tr.z]),
                    np.array([q.x, q.y, q.z, q.w]),
                )

    @staticmethod
    def _bolt_axis(quat):
        m = tf_transformations.quaternion_matrix(quat)
        return m[0:3, 0]

    def _vision_cb(self, msg):
        if self._start_time is None:
            self._start_time = time.monotonic()

        p = msg.pose.position
        q = msg.pose.orientation
        est_pos = np.array([p.x, p.y, p.z])
        est_quat = np.array([q.x, q.y, q.z, q.w])
        est_axis = self._bolt_axis(est_quat)

        with self._lock:
            if not self._gt:
                return
            best_id, best_dist = None, float('inf')
            for bid, (gt_pos, _) in self._gt.items():
                d = float(np.linalg.norm(est_pos - gt_pos))
                if d < best_dist:
                    best_id, best_dist = bid, d

            if best_id is None:
                return
            gt_pos, gt_quat = self._gt[best_id]

        gt_axis = self._bolt_axis(gt_quat)
        pos_err_mm = best_dist * 1000.0
        cos_ang = float(np.clip(np.abs(np.dot(est_axis, gt_axis)), -1.0, 1.0))
        axis_err_deg = math.degrees(math.acos(cos_ang))

        sample = {
            'bolt': best_id,
            'pos_err_mm': pos_err_mm,
            'axis_err_deg': axis_err_deg,
            'est_pos': est_pos.tolist(),
            'gt_pos': gt_pos.tolist(),
        }
        self._samples.append(sample)

        if len(self._samples) % 5 == 1:
            self.get_logger().info(
                f'[{best_id}] 위치 {pos_err_mm:.1f}mm  축 {axis_err_deg:.1f}°  '
                f'(추정 {est_pos[0]:.3f},{est_pos[1]:.3f},{est_pos[2]:.3f}  '
                f'정답 {gt_pos[0]:.3f},{gt_pos[1]:.3f},{gt_pos[2]:.3f})')

    def elapsed(self):
        if self._start_time is None:
            return 0.0
        return time.monotonic() - self._start_time

    def print_summary(self):
        n = len(self._samples)
        if n == 0:
            self.get_logger().warn('비전 발행 수신 0건 — 요약 없음.')
            return

        pos_errs = [s['pos_err_mm'] for s in self._samples]
        axis_errs = [s['axis_err_deg'] for s in self._samples]
        pa, aa = np.array(pos_errs), np.array(axis_errs)

        bolts_seen = sorted(set(s['bolt'] for s in self._samples))

        self.get_logger().info(
            '\n'
            '╔══════════════════════════════════════════════════╗\n'
            '║        비전 정확도 검증 결과 요약               ║\n'
            '╠══════════════════════════════════════════════════╣\n'
            f'║  샘플 수       : {n:>6}\n'
            f'║  검출 볼트     : {", ".join(bolts_seen)}\n'
            '║──────────────────────────────────────────────────║\n'
            f'║  위치 오차(mm) : 평균 {pa.mean():.1f} / '
            f'중앙 {float(np.median(pa)):.1f} / '
            f'최대 {pa.max():.1f} / 표준편차 {pa.std():.1f}\n'
            f'║  축 오차(°)    : 평균 {aa.mean():.1f} / '
            f'중앙 {float(np.median(aa)):.1f} / '
            f'최대 {aa.max():.1f} / 표준편차 {aa.std():.1f}\n'
            '╚══════════════════════════════════════════════════╝')

        for bid in bolts_seen:
            bp = [s['pos_err_mm'] for s in self._samples if s['bolt'] == bid]
            ba = [s['axis_err_deg'] for s in self._samples if s['bolt'] == bid]
            bpa, baa = np.array(bp), np.array(ba)
            self.get_logger().info(
                f'  {bid}: {len(bp)}건  위치 {bpa.mean():.1f}±{bpa.std():.1f}mm  '
                f'축 {baa.mean():.1f}±{baa.std():.1f}°')


def main(args=None):
    rclpy.init(args=args)

    duration = 30.0
    argv = sys.argv[1:]
    for i, a in enumerate(argv):
        if a == '--duration' and i + 1 < len(argv):
            try:
                duration = float(argv[i + 1])
            except ValueError:
                pass

    node = VisionVerify(duration_sec=duration)
    try:
        while rclpy.ok():
            rclpy.spin_once(node, timeout_sec=0.5)
            if node.elapsed() >= duration and node._samples:
                break
    except KeyboardInterrupt:
        pass
    finally:
        node.print_summary()
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
