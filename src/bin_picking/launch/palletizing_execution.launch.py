"""실행 중인 vacuum FR3에 물리 박스 운반 실행자를 연결한다."""
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, OpaqueFunction
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def _setup(context):
    count = int(LaunchConfiguration('box_count').perform(context))
    if not 1 <= count <= 60:
        raise ValueError('box_count must be 1..60')
    arguments = ['/world/empty/create@ros_gz_interfaces/srv/SpawnEntity']
    for i in range(count):
        name = f'pallet_box_{i}'
        arguments += [
            f'/model/{name}/pose@tf2_msgs/msg/TFMessage[gz.msgs.Pose_V',
            f'/vacuum/{name}/attach@std_msgs/msg/Empty]gz.msgs.Empty',
            f'/vacuum/{name}/detach@std_msgs/msg/Empty]gz.msgs.Empty',
            f'/vacuum/{name}/state@std_msgs/msg/String[gz.msgs.StringMsg',
        ]
    return [
        Node(package='ros_gz_bridge', executable='parameter_bridge',
             name='palletizing_physics_bridge', arguments=arguments, output='screen'),
        Node(package='bin_picking', executable='palletizing_motion', output='screen',
             parameters=[{'box_count': count, 'use_sim_time': True,
                          'seed': int(LaunchConfiguration('seed').perform(context)),
                          'strategy': LaunchConfiguration('strategy').perform(context),
                          'velocity': float(LaunchConfiguration('velocity').perform(context))}]),
    ]


def generate_launch_description():
    return LaunchDescription([
        DeclareLaunchArgument('box_count', default_value='36'),
        DeclareLaunchArgument('seed', default_value='20260909'),
        DeclareLaunchArgument('strategy', default_value='dense'),
        DeclareLaunchArgument('velocity', default_value='0.35'),
        OpaqueFunction(function=_setup),
    ])
