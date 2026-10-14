"""기본: 진공 툴 FR3가 컨베이어 박스를 물리적으로 운반. mode:=preview는 기존 정적 장면."""
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription, TimerAction
from launch.actions import OpaqueFunction
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration, PathJoinSubstitution
from launch_ros.substitutions import FindPackageShare


def generate_launch_description():
    share = FindPackageShare('bin_picking')

    def include(name, arguments):
        return IncludeLaunchDescription(
            PythonLaunchDescriptionSource(PathJoinSubstitution([share, 'launch', name])),
            launch_arguments=arguments.items())

    def setup(context):
        motion = LaunchConfiguration('mode').perform(context) == 'motion'
        robot_args = {key: LaunchConfiguration(key) for key in ('robot_model', 'rviz', 'gz_args')}
        if motion:
            robot_args.update(tool='vacuum', vacuum_box_count=LaunchConfiguration('box_count'))
        args = {key: LaunchConfiguration(key) for key in ('seed', 'box_count', 'strategy')}
        if motion:
            args['velocity'] = LaunchConfiguration('velocity')
        else:
            args['robot_model'] = LaunchConfiguration('robot_model')
        return [include('franka_gazebo_moveit.launch.py', robot_args),
                TimerAction(period=LaunchConfiguration('scene_delay'), actions=[
                    include('palletizing_execution.launch.py' if motion else 'spawn_palletizing.launch.py', args)])]

    return LaunchDescription([
        DeclareLaunchArgument('mode', default_value='motion', choices=['motion', 'preview']),
        DeclareLaunchArgument('robot_model', default_value='fr3'),
        DeclareLaunchArgument('rviz', default_value='true'),
        DeclareLaunchArgument('seed', default_value='20260909'),
        DeclareLaunchArgument('strategy', default_value='dense', choices=['greedy', 'compact', 'dense']),
        DeclareLaunchArgument('box_count', default_value='36'),
        DeclareLaunchArgument('velocity', default_value='0.35'),
        DeclareLaunchArgument('scene_delay', default_value='15.0'),
        DeclareLaunchArgument('gz_args', default_value=[
            '-r --render-engine ogre --gui-config ',
            PathJoinSubstitution([share, 'config', 'palletizing_gui.config']), ' ',
            PathJoinSubstitution([share, 'worlds', 'palletizing_cell.sdf'])]),
        OpaqueFunction(function=setup),
    ])
