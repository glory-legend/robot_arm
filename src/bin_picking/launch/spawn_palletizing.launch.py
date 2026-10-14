"""실행 중인 Gazebo에 PDF 1단계 오프라인 배치 장면을 스폰하고 MoveIt에 등록."""
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, EmitEvent, OpaqueFunction, RegisterEventHandler
from launch.event_handlers import OnProcessExit
from launch.events import Shutdown
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node

from bin_picking.palletizing_layout import body_sdf, make_layout


def _setup(context):
    seed = int(LaunchConfiguration('seed').perform(context))
    count = int(LaunchConfiguration('box_count').perform(context))
    strategy = LaunchConfiguration('strategy').perform(context)
    model = LaunchConfiguration('robot_model').perform(context)
    world = LaunchConfiguration('world').perform(context)
    bodies = make_layout(seed, count, strategy)
    bridge = Node(
        package='ros_gz_bridge', executable='parameter_bridge',
        name='palletizing_pose_bridge', output='screen',
        arguments=[f'/model/{b.name}/pose@tf2_msgs/msg/TFMessage[gz.msgs.Pose_V'
                   for b in bodies if not b.static])
    scene = Node(
        package='bin_picking', executable='palletizing_scene', output='screen',
        parameters=[{'robot_model': model, 'seed': seed, 'box_count': count,
                     'strategy': strategy}])
    spawns = [Node(
        package='ros_gz_sim', executable='create', output='screen',
        arguments=['-world', world, '-name', body.name,
                   '-allow_renaming', 'false', '-string', body_sdf(body),
                   # create의 기본 pose가 SDF model/pose를 덮어쓰므로 명시한다.
                   '-x', str(body.position[0]), '-y', str(body.position[1]),
                   '-z', str(body.position[2])])
        for body in bodies]

    def after_spawn(next_actions):
        def handler(event, context):
            if event.returncode != 0:
                return [EmitEvent(event=Shutdown(reason='Palletizing model spawn failed'))]
            return next_actions
        return handler

    handlers = [RegisterEventHandler(OnProcessExit(
        target_action=spawn,
        on_exit=after_spawn([spawns[i + 1]] if i + 1 < len(spawns) else [scene])))
        for i, spawn in enumerate(spawns)]
    return [bridge, *handlers, spawns[0]]


def generate_launch_description():
    return LaunchDescription([
        DeclareLaunchArgument('robot_model', default_value='fr3'),
        DeclareLaunchArgument('world', default_value='empty'),
        DeclareLaunchArgument('seed', default_value='20260909'),
        DeclareLaunchArgument('strategy', default_value='compact', choices=['greedy', 'compact', 'dense']),
        DeclareLaunchArgument('box_count', default_value='12', description='Offline boxes: 1..60'),
        OpaqueFunction(function=_setup),
    ])
