"""로봇팔 ↔ 데스크톱 통신 데모를 **명령 한 줄**로 띄운다.

범위(의도적 축소): 비전(카메라→포인트클라우드→볼트 인식)은 데스크톱 앱과 직접
통신하는 별개 파이프라인이라 여기 안 넣는다(`vision_pipeline.launch.py`,
`bolt_vision` 노드는 다른 팀이 데스크톱 쪽에서 붙일 몫). 이 launch 는 딱
"로봇팔 ↔ 데스크톱 통신이 실제 3D 환경에서 제대로 도는지"만 검증하는 데 필요한
4가지만 순서대로 띄운다:

  1) franka_gazebo_moveit.launch.py  — Gazebo 시뮬레이션 + MoveIt(경로계획)
  2) spawn_bolts.launch.py           — 통 + 볼트 스폰 (로봇이 실제로 집을 대상)
  3) desktop_bridge                  — 데스크톱앱 통신 브릿지(WebSocket+JSON)
  4) integrated_pick_place           — 실제 집기 로직(파지 성공/실패 발생시켜야
                                        desktop_bridge 가 진짜 RESULT/grasp_result
                                        데이터를 만들어낼 수 있다)

Gazebo/MoveIt 는 뜨는 데 수 초~수십 초 걸리고, 그 전에 볼트를 스폰하거나
브릿지·pick_place 를 띄우면 실패한다(서비스/월드 준비 안 됨). 그래서 2)~4)는
TimerAction 으로 지연 기동한다 — 정교한 이벤트 훅 대신 넉넉한 지연시간을 쓰는
쪽을 택했다(이 launch 의 목적은 데모/테스트 편의이지 프로덕션 기동 순서 보장이
아니다). 이 컴퓨터에서 실측한 "You can start planning now!" 도달 시간(약
17~19초)에 여유를 더해 기본값을 잡았다 — 느린 컴퓨터에서 타이밍이 안 맞으면
`bolts_delay`/`apps_delay` 인자를 늘리면 된다.

사용법:
  ros2 launch bin_picking desktop_integration_demo.launch.py
  ros2 launch bin_picking desktop_integration_demo.launch.py rviz:=true auto:=false
  ros2 launch bin_picking desktop_integration_demo.launch.py bolts_delay:=25.0 apps_delay:=30.0
"""
from launch import LaunchDescription
from launch.actions import (
    DeclareLaunchArgument,
    IncludeLaunchDescription,
    TimerAction,
)
from launch.conditions import IfCondition, UnlessCondition
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration, PathJoinSubstitution
from launch_ros.actions import Node
from launch_ros.substitutions import FindPackageShare


def generate_launch_description():
    rviz = LaunchConfiguration('rviz')
    auto = LaunchConfiguration('auto')
    bolts_delay = LaunchConfiguration('bolts_delay')
    apps_delay = LaunchConfiguration('apps_delay')
    bridge_host = LaunchConfiguration('bridge_host')
    bridge_port = LaunchConfiguration('bridge_port')

    declare_rviz = DeclareLaunchArgument(
        'rviz', default_value='false',
        description='MoveIt/RViz 뷰어 표시 여부 (통신 검증만 할 땐 기본 false 로 가볍게)')
    declare_auto = DeclareLaunchArgument(
        'auto', default_value='true',
        description='true 면 integrated_pick_place 가 트리거 없이 연속 자동 운전')
    declare_bolts_delay = DeclareLaunchArgument(
        'bolts_delay', default_value='18.0',
        description='Gazebo/MoveIt 기동 후 볼트 스폰까지 대기 시간(초)')
    declare_apps_delay = DeclareLaunchArgument(
        'apps_delay', default_value='23.0',
        description='Gazebo/MoveIt 기동 후 desktop_bridge+integrated_pick_place 시작까지 대기 시간(초)')
    declare_bridge_host = DeclareLaunchArgument(
        'bridge_host', default_value='0.0.0.0',
        description='desktop_bridge WebSocket 바인드 주소')
    declare_bridge_port = DeclareLaunchArgument(
        'bridge_port', default_value='8765',
        description='desktop_bridge WebSocket 포트')

    # 1) Gazebo + MoveIt — 기존 launch 그대로 재사용(중복 정의 없음)
    gazebo_moveit = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            PathJoinSubstitution([
                FindPackageShare('bin_picking'), 'launch',
                'franka_gazebo_moveit.launch.py',
            ])
        ),
        launch_arguments={'rviz': rviz}.items(),
    )

    # 2) 통 + 볼트 스폰 — Gazebo 월드가 뜬 뒤에만 성공하므로 지연 기동
    spawn_bolts = TimerAction(
        period=bolts_delay,
        actions=[
            IncludeLaunchDescription(
                PythonLaunchDescriptionSource(
                    PathJoinSubstitution([
                        FindPackageShare('bin_picking'), 'launch',
                        'spawn_bolts.launch.py',
                    ])
                ),
            ),
        ],
    )

    # 3) 데스크톱 통신 브릿지 — Gazebo 의 /clock 에 시계를 맞춘다(use_sim_time)
    desktop_bridge = Node(
        package='bin_picking', executable='desktop_bridge', output='screen',
        parameters=[{
            'use_sim_time': True,
            'host': bridge_host,
            'port': bridge_port,
        }],
    )

    # 4) 실제 집기 로직 — auto 값에 따라 --auto 인자 유무만 다른 두 정의를
    #    조건부(IfCondition/UnlessCondition)로 두고 하나만 실제 기동되게 한다.
    pick_place_auto = Node(
        package='bin_picking', executable='integrated_pick_place', output='screen',
        arguments=['--auto'], parameters=[{'use_sim_time': True}],
        condition=IfCondition(auto),
    )
    pick_place_manual = Node(
        package='bin_picking', executable='integrated_pick_place', output='screen',
        parameters=[{'use_sim_time': True}],
        condition=UnlessCondition(auto),
    )

    apps = TimerAction(
        period=apps_delay,
        actions=[desktop_bridge, pick_place_auto, pick_place_manual],
    )

    return LaunchDescription([
        declare_rviz, declare_auto, declare_bolts_delay, declare_apps_delay,
        declare_bridge_host, declare_bridge_port,
        gazebo_moveit, spawn_bolts, apps,
    ])
