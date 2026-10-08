# -*- coding: utf-8 -*-
"""그리퍼 액션 인터페이스 어댑터 — 업체마다 다른 '지령 보내는 법'을 흡수한다.

MoveIt/ros2_control 세계에서 그리퍼를 움직이는 방법은 크게 둘이다
(MoveIt "Low Level Controllers" 문서의 두 갈래와 같다):

  - `FollowJointTrajectory` — 그리퍼를 그냥 1축 관절로 보고 궤적을 보낸다.
    프랑카 핸드가 이 방식이다(Gazebo 에서 joint_trajectory_controller 로 구동).
  - `GripperCommand` — 병렬 그리퍼 전용. 목표 위치와 최대 힘을 보내고,
    결과로 `stalled`(물체에 막혀 멈춤) / `reached_goal` 을 받는다.
    Robotiq 2F 계열을 비롯한 대부분의 상용 그리퍼가 이쪽이다.

파이프라인 본체(`gripper.py` 의 `GripperMixin`)는 이 차이를 몰라야 한다. 그래서
"위치를 지령하고 완료를 기다린다"는 한 가지 동작만 여기서 어댑터로 노출한다.

⚠ 파지 성공 판정은 여기 없다. 어느 액션을 쓰든 `error_code`/`reached_goal` 로는
  '물체를 물어서 멈춤'과 '허공에서 끝까지 닫힘'을 구분할 수 없기 때문이다
  (FollowJointTrajectory 의 GOAL_TOLERANCE_VIOLATED 는 양쪽 모두에서 난다).
  판정은 `/joint_states` 실측 개구로만 한다 — `geometry.py::_finger_width_is_grasp`.
"""
from builtin_interfaces.msg import Duration
from control_msgs.action import FollowJointTrajectory, GripperCommand
from rclpy.action import ActionClient
from trajectory_msgs.msg import JointTrajectory, JointTrajectoryPoint


class GripperActionAdapter:
    """공통 뼈대. 하위 클래스는 goal 을 만들고 결과를 해석하기만 한다."""

    #: control_msgs 액션 타입 (하위 클래스가 지정)
    action_type = None

    def __init__(self, node, spec):
        self.node = node
        self.spec = spec           # robot_profiles.schema.GripperSpec
        self.client = ActionClient(node, self.action_type, spec.action_name)

    def wait_for_server(self, timeout_sec):
        return self.client.wait_for_server(timeout_sec=timeout_sec)

    def build_goal(self, position, duration_sec):
        raise NotImplementedError

    def interpret(self, result):
        """액션 결과 → (성공여부, 로그에 남길 짧은 설명).

        여기서 말하는 '성공'은 **지령이 정상 처리됐는가**일 뿐, 물체를 물었는지가
        아니다(위 ⚠ 참조).
        """
        raise NotImplementedError


class FollowJointTrajectoryGripper(GripperActionAdapter):
    """1축 관절 궤적으로 지령 — 프랑카 핸드(Gazebo joint_trajectory_controller)."""

    action_type = FollowJointTrajectory

    def build_goal(self, position, duration_sec):
        g = FollowJointTrajectory.Goal()
        g.trajectory = JointTrajectory()
        g.trajectory.joint_names = [self.spec.command_joint]
        pt = JointTrajectoryPoint()
        pt.positions = [position]
        pt.time_from_start = Duration(
            sec=int(duration_sec),
            nanosec=int((duration_sec - int(duration_sec)) * 1e9),
        )
        g.trajectory.points.append(pt)
        return g

    def interpret(self, result):
        code_val = result.result.error_code
        # 주의: 실물/실제 물체 파지 시에는 GOAL_TOLERANCE_VIOLATED가
        # "물체 두께에서 멈춤 = 파지 성공"일 수 있으므로 판정을 뒤집어야 함.
        return code_val == 0, f'code={code_val}'


class GripperCommandGripper(GripperActionAdapter):
    """병렬 그리퍼 표준 액션 — 목표 위치 + 최대 힘.

    `max_effort=0.0` 은 대부분의 드라이버에서 '제한 없음/기본값'으로 해석된다.
    힘을 조여야 하는 그리퍼를 등록하게 되면 프로파일에 필드를 추가할 것 —
    지금 임의의 기본값을 넣으면 그 값이 어디서 왔는지 아무도 모르게 된다.
    """

    action_type = GripperCommand

    def build_goal(self, position, duration_sec):
        # GripperCommand 에는 시간 개념이 없다(위치+힘만). duration_sec 은
        # 호출자가 완료를 기다리는 데만 쓰이므로 여기서는 무시한다.
        g = GripperCommand.Goal()
        g.command.position = float(position)
        g.command.max_effort = 0.0
        return g

    def interpret(self, result):
        r = result.result
        # reached_goal: 목표 폭에 도달 / stalled: 무언가에 막혀 멈춤.
        # 둘 다 '지령은 정상 처리됨'이다 — 물체를 물었는지는 실측 개구로 따로 본다.
        ok = bool(getattr(r, 'reached_goal', False)
                  or getattr(r, 'stalled', False))
        return ok, (f'reached_goal={getattr(r, "reached_goal", None)} '
                    f'stalled={getattr(r, "stalled", None)} '
                    f'pos={getattr(r, "position", None)}')


_ADAPTERS = {
    'FollowJointTrajectory': FollowJointTrajectoryGripper,
    'GripperCommand': GripperCommandGripper,
}


def make_gripper_adapter(node, spec):
    """프로파일의 `gripper.action_type` 에 맞는 어댑터를 만든다.

    스키마가 이미 알 수 없는 타입을 막지만, 등록 스키마와 여기 구현이 어긋나는
    경우(새 타입을 스키마에만 추가한 경우)를 조용히 넘기지 않는다.
    """
    try:
        adapter_cls = _ADAPTERS[spec.action_type]
    except KeyError:
        raise ValueError(
            f'그리퍼 액션 타입 {spec.action_type!r} 에 대한 어댑터가 없다 — '
            f'구현된 타입: {sorted(_ADAPTERS)}. '
            f'gripper_adapters.py 에 어댑터를 추가하세요.')
    return adapter_cls(node, spec)
