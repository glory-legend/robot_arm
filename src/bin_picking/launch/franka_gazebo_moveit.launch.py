"""등록된 로봇 모델을 Gazebo Sim + MoveIt + RViz 로 띄운다.

    ros2 launch bin_picking franka_gazebo_moveit.launch.py                 # 활성 모델
    ros2 launch bin_picking franka_gazebo_moveit.launch.py robot_model:=fr3

`robot_model:=` **인자 하나**로 스택 전체가 따라온다 — URDF, SRDF, MoveIt 설정
(kinematics/joint_limits/ompl/controllers/rviz), 컨트롤러 스포너 이름, Gazebo 엔티티
이름, 메시 탐색 경로, 그리고 이 런치가 띄우는 노드들이 읽을 활성 모델까지.
그 모든 값은 등록된 프로파일(`bin_picking/robot_profiles/data/<모델>.yaml`)에서
나오고, 이 파일에는 어느 로봇의 이름도 하드코딩돼 있지 않다.

⚠ 파일 이름에 'franka' 가 남아 있는 것은 기존 문서/명령과의 호환 때문이다.
  내용은 벤더 중립이다.

흐름:
  1) 프로파일 조회 + 정적 검증(참조하는 패키지/파일이 실제로 있는가)
  2) xacro -> URDF / SRDF
  3) robot_state_publisher
  4) Gazebo Sim (커스텀 월드)
  5) /clock 브리지 (Gz -> ROS)
  6) /robot_description 으로 엔티티 스폰
  7) 스폰 후: joint_state_broadcaster + 팔 컨트롤러 + 그리퍼 컨트롤러
  8) move_group + RViz
"""

import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import (
    DeclareLaunchArgument,
    OpaqueFunction,
    RegisterEventHandler,
    SetEnvironmentVariable,
)
from launch.conditions import IfCondition
from launch.event_handlers import OnProcessExit
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.actions import IncludeLaunchDescription
from launch.substitutions import (
    Command,
    FindExecutable,
    LaunchConfiguration,
    PathJoinSubstitution,
)
from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterValue
from launch_ros.substitutions import FindPackageShare

import yaml

from bin_picking import robot_profiles
from bin_picking.robot_profiles import validator as profile_validator
from bin_picking.robot_profiles import vendor_yaml


def _load_yaml(package_name, file_path):
    """벤더 설정 YAML 하나를 읽는다.

    순정 `yaml.safe_load` 가 아니라 관용 로더를 쓴다 — 일부 벤더 설정은 xacro 가
    정의한 단위 태그(`!degrees` 등)를 쓰는데, safe_load 로는 그걸 못 읽고
    기동 도중 ConstructorError 로 넘어진다(ur_description 의 joint_limits 가 그렇다).
    """
    pkg_share = get_package_share_directory(package_name)
    abs_path = os.path.join(pkg_share, file_path)
    try:
        return vendor_yaml.load(abs_path)
    except EnvironmentError:
        return None


def _xacro_command(package, rel_path, args):
    """xacro 실행 substitution. 인자는 프로파일이 준 대로 `k:=v` 로 펼친다."""
    parts = [FindExecutable(name='xacro'), ' ',
             PathJoinSubstitution([FindPackageShare(package), rel_path])]
    for key in sorted(args):
        parts.extend([' ', f'{key}:={args[key]}'])
    return Command(parts)


def _resolve_profile(model_name):
    """프로파일을 읽고 정적 검증까지 마친다. 오류가 있으면 여기서 멈춘다.

    로봇이 이미 절반쯤 뜬 뒤에 "그런 파일이 없다"로 죽는 것보다, 아무것도 띄우기
    전에 무엇이 틀렸는지 한 번에 보여 주는 편이 훨씬 낫다.
    """
    profile = robot_profiles.get(model_name)      # 미등록이면 ProfileNotFound
    report = profile_validator.validate_static(
        profile,
        package_share=get_package_share_directory,
        path_exists=os.path.exists)
    if not report.ok:
        raise RuntimeError(
            f'로봇 모델 {model_name!r} 프로파일 검증 실패 — 기동을 중단합니다.\n'
            + report.format()
            + f'\n프로파일 파일: {profile.source_path}')
    return profile, report


def _launch_setup(context, *_args, **_kwargs):
    model_name = LaunchConfiguration('robot_model').perform(context)
    rviz = LaunchConfiguration('rviz')
    gz_args = LaunchConfiguration('gz_args')
    vacuum = LaunchConfiguration('tool').perform(context) == 'vacuum'

    profile, report = _resolve_profile(model_name)
    desc = profile.description

    print(f'[bin_picking] 로봇 모델: {profile.name} ({profile.display_name}, '
          f'{profile.vendor}) — status={profile.status}')
    if report.warnings:
        for f in report.warnings:
            print(f'[bin_picking] {f.format()}')

    # --- URDF / SRDF (프로파일이 가리키는 xacro + 인자) ---
    robot_description = {
        'robot_description': ParameterValue(
            _xacro_command(desc.urdf_package, desc.urdf_path, desc.urdf_args),
            value_type=str)
    }
    robot_description_semantic = {
        'robot_description_semantic': ParameterValue(
            _xacro_command(desc.srdf_package, desc.srdf_path, desc.srdf_args),
            value_type=str)
    }
    if vacuum:
        from bin_picking.palletizing_robot import vacuum_descriptions
        urdf, srdf = vacuum_descriptions(
            profile, int(LaunchConfiguration('vacuum_box_count').perform(context)))
        robot_description = {'robot_description': ParameterValue(urdf, value_type=str)}
        robot_description_semantic = {'robot_description_semantic': ParameterValue(srdf, value_type=str)}

    # --- MoveIt 설정 (프로파일이 가리키는 패키지/파일) ---
    mp = desc.moveit_package
    kinematics_config = {
        'robot_description_kinematics':
            _load_yaml(mp, desc.moveit_files['kinematics'])
    }
    joint_limits_config = {
        'robot_description_planning':
            _load_yaml(mp, desc.moveit_files['joint_limits'])
    }
    ompl_config = {
        'move_group': {
            'planning_plugins': ['ompl_interface/OMPLPlanner'],
            'request_adapters': [
                'default_planning_request_adapters/ResolveConstraintFrames',
                'default_planning_request_adapters/ValidateWorkspaceBounds',
                'default_planning_request_adapters/CheckStartStateBounds',
                'default_planning_request_adapters/CheckStartStateCollision',
            ],
            'response_adapters': [
                'default_planning_response_adapters/AddTimeOptimalParameterization',
                'default_planning_response_adapters/ValidateSolution',
                'default_planning_response_adapters/DisplayMotionPath',
            ],
            'start_state_max_bounds_error': 0.1,
        }
    }
    ompl_config['move_group'].update(_load_yaml(mp, desc.moveit_files['ompl']))
    # 벤더 파일이 planner_configs 를 안 주는 경우 프로파일의 오버레이로 채운다.
    # (얕은 병합이면 충분하다 — ompl 설정은 최상위 키 단위로 독립적이다.)
    if desc.ompl_overlay:
        ompl_config['move_group'].update(desc.ompl_overlay)

    moveit_controllers = {
        'moveit_simple_controller_manager':
            _load_yaml(mp, desc.moveit_files['controllers']),
        'moveit_controller_manager':
            'moveit_simple_controller_manager/MoveItSimpleControllerManager',
    }
    if vacuum:
        controllers = moveit_controllers['moveit_simple_controller_manager']
        controllers['controller_names'] = [profile.arm.controller]
        for key in list(controllers):
            if key not in ('controller_names', profile.arm.controller):
                del controllers[key]

    trajectory_execution = {
        'moveit_manage_controllers': True,
        'trajectory_execution.allowed_execution_duration_scaling': 1.2,
        'trajectory_execution.allowed_goal_duration_margin': 0.5,
        'trajectory_execution.allowed_start_tolerance': 0.01,
    }
    psm_params = {
        'publish_planning_scene': True,
        'publish_geometry_updates': True,
        'publish_state_updates': True,
        'publish_transforms_updates': True,
    }
    sim_time = {'use_sim_time': True}

    # --- Nodes ---
    rsp = Node(
        package='robot_state_publisher', executable='robot_state_publisher',
        output='both', parameters=[robot_description, sim_time],
    )

    move_group_node = Node(
        package='moveit_ros_move_group', executable='move_group',
        output='screen',
        parameters=[
            robot_description, robot_description_semantic, kinematics_config,
            joint_limits_config, ompl_config, trajectory_execution,
            moveit_controllers, psm_params, sim_time,
        ],
    )

    rviz_config = os.path.join(get_package_share_directory(mp),
                               desc.moveit_files['rviz'])
    if vacuum:
        rviz_config = os.path.join(get_package_share_directory('bin_picking'),
                                   'config', 'palletizing.rviz')
    rviz_node = Node(
        package='rviz2', executable='rviz2', name='rviz2',
        arguments=['-d', rviz_config], output='log',
        parameters=[
            robot_description, robot_description_semantic,
            ompl_config, kinematics_config, sim_time,
        ],
        condition=IfCondition(rviz),
    )

    # --- Gazebo Sim ---
    # gz 가 메시를 찾을 수 있게 description 패키지의 '상위' 디렉터리를 잡는다.
    os.environ['GZ_SIM_RESOURCE_PATH'] = os.path.dirname(
        get_package_share_directory(desc.gazebo_resource_package))

    gz_sim = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            PathJoinSubstitution([
                FindPackageShare('ros_gz_sim'), 'launch', 'gz_sim.launch.py',
            ])
        ),
        launch_arguments={'gz_args': gz_args}.items(),
    )

    spawn_entity = Node(
        package='ros_gz_sim', executable='create',
        arguments=['-topic', '/robot_description',
                   '-name', desc.gazebo_entity],
        output='screen',
    )

    bridge_clock = Node(
        package='ros_gz_bridge', executable='parameter_bridge',
        arguments=['/clock@rosgraph_msgs/msg/Clock[gz.msgs.Clock'],
        output='screen',
    )

    # --- Controller spawners (after Gazebo entity spawn) ---
    def spawner(controller_name):
        return Node(
            package='controller_manager', executable='spawner',
            arguments=[controller_name, '--controller-manager-timeout', '60'],
            output='screen',
        )

    spawn_jsb = spawner('joint_state_broadcaster')
    spawn_arm = spawner(profile.arm.controller)
    # 그리퍼 컨트롤러를 따로 띄우는 이유: Gazebo Sim 은 URDF <mimic> 을 강제하지
    # 않아 종동 손가락이 떨린다. 구동 관절을 컨트롤러로 잡아 두면 흔들림이 없다.
    spawn_gripper = spawner(profile.gripper.controller)

    # spawn_entity exits cleanly once the robot is in Gazebo; controllers come up after.
    after_spawn = RegisterEventHandler(
        event_handler=OnProcessExit(
            target_action=spawn_entity,
            on_exit=[spawn_jsb, spawn_arm] + ([] if vacuum else [spawn_gripper]),
        )
    )

    return [
        # 이 런치가 띄우는(그리고 뒤이어 사람이 띄우는) 노드들이 **같은** 모델을
        # 읽도록 환경에 못 박는다. 이게 없으면 시뮬은 새 모델인데 파지 노드는
        # 저장된 옛 모델로 도는, 겉보기엔 멀쩡한 사고가 난다.
        SetEnvironmentVariable(robot_profiles.ENV_MODEL, profile.name),
        rsp,
        gz_sim,
        bridge_clock,
        spawn_entity,
        after_spawn,
        move_group_node,
        rviz_node,
    ]


def generate_launch_description():
    # 전체화면 + 로봇암 근접 카메라 뷰가 담긴 커스텀 월드(worlds/robot_view.sdf).
    # 통/볼트는 spawn_bolts 가 따로 올리므로 환경 자체는 불변 — GUI 초기 뷰만 바뀐다.
    world_path = PathJoinSubstitution([
        FindPackageShare('bin_picking'), 'worlds', 'robot_view.sdf'])

    return LaunchDescription([
        DeclareLaunchArgument('tool', default_value='profile', choices=['profile', 'vacuum']),
        DeclareLaunchArgument('vacuum_box_count', default_value='12'),
        DeclareLaunchArgument(
            'robot_model',
            default_value=robot_profiles.active_model_name(),
            description=(
                '띄울 로봇 모델(등록된 프로파일 이름). '
                f'현재 등록됨: {robot_profiles.names()}. '
                '`binpick_model list` 로 확인.')),
        DeclareLaunchArgument(
            'gz_args', default_value=['-r ', world_path],
            description='Args forwarded to ros_gz_sim/gz_sim.launch.py'),
        DeclareLaunchArgument(
            'rviz', default_value='true',
            description='Run RViz with the MoveIt config'),
        OpaqueFunction(function=_launch_setup),
    ])
