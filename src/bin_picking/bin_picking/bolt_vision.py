#!/usr/bin/env python3
"""
빈피킹 비전 인식 노드 — 가상 RGB-D 카메라 → 볼트 6D 자세 → /next_bolt_pose
=====================================================================
Gazebo 정답 pose(/model/bolt_i/pose) 대신 '카메라가 본 것'으로 볼트를 찾는다.
franka_integrated_pick_place.py 가 이미 /next_bolt_pose(PoseStamped, fr3_link0
프레임)를 소비하므로, 이 노드가 그 토픽만 채우면 로봇/MoveIt 코드는 무변경으로
비전 기반이 된다. (하이브리드 검증 단계: 로봇은 비전이 고른 볼트를 집고, 씬/이웃
관리는 아직 Gazebo 센싱을 쓴다 — 추정 vs 정답을 나란히 검증하기 위함.)

파이프라인 (PCL 없이 numpy + sklearn):
  1) /bin_camera/points (PointCloud2, camera_optical_link 프레임) 수신
  2) tf2 로 fr3_link0(base) 프레임으로 변환
  3) 통 영역 crop (바닥/벽/로봇 제거) — z 로 바닥 컷, xy 로 통 밖 컷
  4) DBSCAN 유클리드 클러스터링 → 개별 볼트 분리
  5) 클러스터별: 중심(위치) + PCA 주축(볼트 축) → 6D 자세(로봇 규약: 볼트축=local +X)
  6) '가장 위 + 가장 안 가려진' 볼트를 골라 PoseStamped(fr3_link0)로 발행

⚠ 알려진 원통 강체(M8 볼트)라 딥러닝 불필요 — 클러스터 PCA 로 축·중심이면 충분.
  겹친 무더기에선 클러스터가 붙어 부정확해질 수 있다(그땐 실린더 RANSAC/학습 필요).
  현재 낱개분리 배치엔 이 방식으로 충분하다.

실행: (Gazebo + 카메라 스폰된 상태에서)
  ros2 launch franka_tutorials vision_pipeline.launch.py
  또는 python3 bolt_vision.py
"""
import math

import numpy as np
import rclpy
import tf_transformations
from rclpy.node import Node
from rclpy.qos import QoSProfile, ReliabilityPolicy

from geometry_msgs.msg import Point, PoseStamped, Quaternion
from sensor_msgs.msg import PointCloud2
from sensor_msgs_py import point_cloud2
from visualization_msgs.msg import Marker, MarkerArray

import tf2_ros

try:
    from sklearn.cluster import DBSCAN
    _HAVE_SKLEARN = True
except ImportError:                                   # 방어: 없으면 노드는 뜨되 경고
    _HAVE_SKLEARN = False


class BoltVision(Node):
    # ---- 프레임 ----
    BASE_FRAME = 'fr3_link0'
    CLOUD_TOPIC = '/bin_camera/points'
    OUT_TOPIC = '/next_bolt_pose'
    MARKER_TOPIC = '/bolt_vision_markers'

    # ---- 통 영역 crop (base 프레임, m). bolt_scene 과 일치시켜야 함 ----
    BIN_X = (0.26, 0.54)         # 집는 통 x 범위(통 0.40 ± 0.14, 여유)
    BIN_Y = (-0.12, 0.12)
    Z_MIN = 0.0065               # 바닥 상면(0.005) 위 — 바닥/지면 컷
    Z_MAX = 0.060                # 통 벽 위 로봇/손 등 컷

    # ---- 클러스터링 ----
    VOXEL = 0.003                # 다운샘플 격자(3mm) — DBSCAN 속도
    DBSCAN_EPS = 0.010           # 이웃 반경(10mm) — 볼트 하나로 뭉치되 옆 볼트와 분리
    DBSCAN_MIN = 12              # 최소 점수(노이즈 클러스터 제거)
    MIN_CLUSTER_PTS = 25         # 볼트로 인정할 최소 점수
    MIN_AXIS_LEN = 0.020         # 주축 길이 하한(볼트 길이 45mm 의 일부라도 보여야)

    def __init__(self):
        super().__init__('bolt_vision')
        self.get_logger().info('=== 빈피킹 비전 인식 노드 ===')
        if not _HAVE_SKLEARN:
            self.get_logger().error(
                'sklearn 미설치 — DBSCAN 불가. pip3 install --user scikit-learn')

        self._tf_buf = tf2_ros.Buffer()
        self._tf_listener = tf2_ros.TransformListener(self._tf_buf, self)
        self._T_cam2base = None          # 4x4 (camera_optical_link → base), 정적이라 1회 캐시

        # 카메라는 BEST_EFFORT 로 발행되므로 구독도 맞춘다
        qos = QoSProfile(depth=5)
        qos.reliability = ReliabilityPolicy.BEST_EFFORT
        self.create_subscription(PointCloud2, self.CLOUD_TOPIC, self._cloud_cb, qos)

        self._pose_pub = self.create_publisher(PoseStamped, self.OUT_TOPIC, 10)
        self._marker_pub = self.create_publisher(MarkerArray, self.MARKER_TOPIC, 10)
        self._n = 0
        self.get_logger().info(
            f'구독 {self.CLOUD_TOPIC} → 발행 {self.OUT_TOPIC} '
            f'(fr3_link0). Gazebo+카메라가 떠 있어야 포인트클라우드가 옵니다.')

    # -------------------------------------------------------------
    def _lookup_cam2base(self, cloud_frame):
        """camera_optical_link → base 4x4 변환(정적). 최초 1회 tf2 로 얻어 캐시."""
        if self._T_cam2base is not None:
            return self._T_cam2base
        try:
            tr = self._tf_buf.lookup_transform(
                self.BASE_FRAME, cloud_frame, rclpy.time.Time())
        except Exception as exc:                      # TF 아직 없음 → 다음 프레임 재시도
            self.get_logger().warn(
                f'TF {self.BASE_FRAME}←{cloud_frame} 대기 중: {exc}', throttle_duration_sec=2.0)
            return None
        t = tr.transform.translation
        q = tr.transform.rotation
        T = tf_transformations.quaternion_matrix([q.x, q.y, q.z, q.w])
        T[0:3, 3] = [t.x, t.y, t.z]
        self._T_cam2base = T
        self.get_logger().info(f'카메라→base TF 획득(정적 캐시): frame={cloud_frame}')
        return T

    @staticmethod
    def _voxel_downsample(pts, leaf):
        """격자 다운샘플 — 각 복셀에서 한 점만. 속도용(정밀도 손실 미미)."""
        if len(pts) == 0:
            return pts
        keys = np.floor(pts / leaf).astype(np.int64)
        _, idx = np.unique(keys, axis=0, return_index=True)
        return pts[idx]

    def _cloud_cb(self, msg):
        T = self._lookup_cam2base(msg.header.frame_id)
        if T is None:
            return
        # 1) PointCloud2 → Nx3 numpy (NaN 제거)
        pts = point_cloud2.read_points_numpy(
            msg, field_names=('x', 'y', 'z'), skip_nans=True)
        if pts is None or len(pts) == 0:
            return
        pts = np.asarray(pts, dtype=np.float64).reshape(-1, 3)
        # skip_nans 로도 inf(무한거리 반환) 는 남을 수 있어 matmul 이 깨진다 →
        # 유한값 행만 남긴다.
        pts = pts[np.isfinite(pts).all(axis=1)]
        if len(pts) == 0:
            return

        # 2) base 프레임으로 변환
        base = pts @ T[0:3, 0:3].T + T[0:3, 3]

        # 3) 통 영역 crop (바닥/벽/로봇 제거)
        m = ((base[:, 0] >= self.BIN_X[0]) & (base[:, 0] <= self.BIN_X[1]) &
             (base[:, 1] >= self.BIN_Y[0]) & (base[:, 1] <= self.BIN_Y[1]) &
             (base[:, 2] >= self.Z_MIN) & (base[:, 2] <= self.Z_MAX))
        roi = base[m]
        if len(roi) < self.MIN_CLUSTER_PTS or not _HAVE_SKLEARN:
            return

        # 4) 다운샘플 + DBSCAN 클러스터링
        roi = self._voxel_downsample(roi, self.VOXEL)
        labels = DBSCAN(eps=self.DBSCAN_EPS,
                        min_samples=self.DBSCAN_MIN).fit_predict(roi)

        # 5) 클러스터별 6D 자세 추정
        bolts = []
        for lab in set(labels):
            if lab == -1:                             # 노이즈
                continue
            c = roi[labels == lab]
            if len(c) < self.MIN_CLUSTER_PTS:
                continue
            center = c.mean(axis=0)
            axis, axis_len = self._pca_axis(c)
            if axis is None or axis_len < self.MIN_AXIS_LEN:
                continue                              # 축이 안 보임(위에서 본 원 등) → 스킵
            bolts.append((center, axis, len(c)))

        if not bolts:
            self._n += 1
            if self._n % 20 == 1:
                self.get_logger().info(
                    f'ROI {len(roi)}점에서 볼트 클러스터 0개 — 카메라/crop/조명 확인')
            return

        # 6) '가장 위(z 큰) + 점 많은' 볼트 채택 → 발행
        bolts.sort(key=lambda b: (round(b[0][2], 3), b[2]), reverse=True)
        center, axis, npts = bolts[0]
        self._publish(center, axis, msg.header.stamp)
        self._publish_markers(bolts, msg.header.stamp)
        self._n += 1
        if self._n % 10 == 1:
            yaw = math.degrees(math.atan2(axis[1], axis[0]))
            self.get_logger().info(
                f'[비전] 볼트 {len(bolts)}개 검출 → 채택 '
                f'({center[0]:.3f},{center[1]:.3f},{center[2]:.3f}) '
                f'축 {yaw:+.0f}° ({npts}점) → /next_bolt_pose 발행')

    @staticmethod
    def _pca_axis(cluster):
        """클러스터 주축(볼트 길이축) 단위벡터 + 축방향 길이(점 분포 범위)."""
        c = cluster - cluster.mean(axis=0)
        try:
            _, s, vt = np.linalg.svd(c, full_matrices=False)
        except np.linalg.LinAlgError:
            return None, 0.0
        axis = vt[0]
        axis = axis / (np.linalg.norm(axis) + 1e-12)
        # 축을 항상 xy 평면 위로(부호 임의성 제거 — 파지엔 무의미하지만 로그 일관성)
        if axis[0] < 0:
            axis = -axis
        proj = c @ axis
        return axis, float(proj.max() - proj.min())

    def _quat_from_axis(self, axis):
        """볼트 축(local +X) → 자세 쿼터니언. 로봇 규약(bolt_axis_from_quat)과 일치:
        회전행렬 첫 열 = 축. 나머지 두 열은 임의 직교정규(축 회전은 파지에 무의미)."""
        x = np.asarray(axis, dtype=float)
        x = x / (np.linalg.norm(x) + 1e-12)
        up = np.array([0.0, 0.0, 1.0])
        if abs(float(np.dot(x, up))) > 0.95:          # 축이 수직에 가까우면 다른 기준
            up = np.array([1.0, 0.0, 0.0])
        y = np.cross(up, x); y /= (np.linalg.norm(y) + 1e-12)
        z = np.cross(x, y)
        m = np.identity(4)
        m[0:3, 0] = x
        m[0:3, 1] = y
        m[0:3, 2] = z
        q = tf_transformations.quaternion_from_matrix(m)
        return Quaternion(x=q[0], y=q[1], z=q[2], w=q[3])

    def _publish(self, center, axis, stamp):
        ps = PoseStamped()
        ps.header.stamp = stamp
        ps.header.frame_id = self.BASE_FRAME
        ps.pose.position = Point(x=float(center[0]), y=float(center[1]),
                                 z=float(center[2]))
        ps.pose.orientation = self._quat_from_axis(axis)
        self._pose_pub.publish(ps)

    def _publish_markers(self, bolts, stamp):
        """검출 볼트들을 RViz 마커로(초록=채택, 노랑=나머지)."""
        ma = MarkerArray()
        for i, (center, axis, _n) in enumerate(bolts):
            mk = Marker()
            mk.header.frame_id = self.BASE_FRAME
            mk.header.stamp = stamp
            mk.ns = 'bolt_vision'
            mk.id = i
            mk.type = Marker.ARROW
            mk.action = Marker.ADD
            half = 0.0225 * axis
            mk.points = [Point(x=float(center[0] - half[0]),
                               y=float(center[1] - half[1]),
                               z=float(center[2] - half[2])),
                         Point(x=float(center[0] + half[0]),
                               y=float(center[1] + half[1]),
                               z=float(center[2] + half[2]))]
            mk.scale.x = 0.004
            mk.scale.y = 0.008
            g = (i == 0)
            mk.color.r = 0.0 if g else 1.0
            mk.color.g = 1.0
            mk.color.b = 0.0
            mk.color.a = 0.9
            ma.markers.append(mk)
        self._marker_pub.publish(ma)


def main(args=None):
    rclpy.init(args=args)
    node = BoltVision()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
