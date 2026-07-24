"""빈피킹 비전 파이프라인 — gz 카메라 토픽을 ROS2로 브릿지.
=====================================================================
fr3_gazebo.urdf.xacro 에 추가한 rgbd_camera(<topic>bin_camera</topic>)가
gz 측에 /bin_camera/points, /image, /depth_image, /camera_info 를 낸다.
이 런치가 그걸 ROS2 토픽으로 중계한다.

⚠ PointCloud2 의 gz 메시지 타입은 gz.msgs.PointCloudPacked (PointCloud 아님 —
  흔한 실수). CameraInfo 도 함께 브릿지해야 광학 파라미터가 맞는다.

실행 순서:
  터미널1: ros2 launch bin_picking franka_gazebo_moveit.launch.py  # 로봇+카메라
  터미널2: ros2 launch bin_picking spawn_bolts.launch.py            # 볼트
  터미널3: ros2 launch bin_picking vision_pipeline.launch.py        # 카메라 브릿지
  터미널4: cd <데모 폴더> && python3 bolt_vision.py                       # 인식 노드
  터미널5: cd <데모 폴더> && python3 franka_integrated_pick_place.py --auto

RViz 확인: PointCloud2 Display → /bin_camera/points, Fixed Frame fr3_link0.
  통 위 볼트들이 3D 점으로 보이고, /bolt_vision_markers 로 검출 화살표가 뜬다.
"""
from launch import LaunchDescription
from launch_ros.actions import Node


def generate_launch_description():
    # gz → ROS2 카메라 브릿지 (포인트클라우드 + 카메라정보 + 컬러/깊이 영상)
    camera_bridge = Node(
        package='ros_gz_bridge', executable='parameter_bridge',
        name='bin_camera_bridge', output='screen',
        arguments=[
            '/bin_camera/points@sensor_msgs/msg/PointCloud2[gz.msgs.PointCloudPacked',
            '/bin_camera/camera_info@sensor_msgs/msg/CameraInfo[gz.msgs.CameraInfo',
            '/bin_camera/image@sensor_msgs/msg/Image[gz.msgs.Image',
            '/bin_camera/depth_image@sensor_msgs/msg/Image[gz.msgs.Image',
        ],
    )
    return LaunchDescription([camera_bridge])
