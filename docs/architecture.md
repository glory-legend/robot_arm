# 아키텍처

## 왜 이렇게 나눴나

원래 `franka_integrated_pick_place.py` 는 **3350줄 단일 클래스**에 메서드 ~107개가
뭉쳐 있었습니다(God Class). 한 곳을 고치면 어디가 영향받는지 알기 어려웠습니다.

리팩토링 원칙:
- **책임 축으로 자른다.** 기하 계산 / 파지 계획 / 선택 / MoveIt I/O / 씬 관리는
  서로 다른 이유로 바뀝니다 → 각각 별도 파일.
- **동작은 한 글자도 바꾸지 않는다.** 메서드 본문·`self.`/`cls.` 참조를 그대로
  두고 파일만 나눴습니다. 검증: 리팩토링 전후 클래스의 메서드 107개·상수 82개가
  값까지 완전히 일치함을 자동 대조했습니다.

## 분해 기법: Mixin + 설정 베이스클래스

```python
class IntegratedPickPlace(
        Node,              # rclpy 노드
        PickPlaceConfig,   # config.py — 모든 상수(self.X 로 참조)
        GeometryMixin,     # geometry.py
        GraspPlanningMixin,# grasp_planning.py
        RobotStateMixin,   # robot_state.py
        MoveItIOMixin,     # moveit_io.py
        GripperMixin,      # gripper.py
        SceneMixin,        # scene.py
        MarkersMixin,      # markers.py
        SensingMixin,      # sensing.py
        SelectionMixin):   # selection.py
    ...
```

각 Mixin 은 상태를 갖지 않는 "책임 묶음"이고, 실제 상태(구독자·클라이언트·
`_bolt_sensed` 등)는 런타임에 하나의 노드 인스턴스가 소유합니다. 그래서
`self.compute_cartesian(...)`, `self._all_bolt_poses()` 같은 호출이 파일 경계를
넘어도 그대로 동작합니다.

> **왜 컴포지션(협력객체 주입)이 아니라 Mixin인가?**
> 컴포지션이 아키텍처적으로 더 깔끔하지만, `self.X` 참조를 전부 재배선해야 해
> "동작 보존"을 기계적으로 보장하기 어렵습니다. 이 프로젝트는 시뮬레이션에서
> 이미 안정 동작 중이므로, **회귀 위험이 가장 낮은 Mixin 분리**를 택했습니다.
> 추후 협력객체로 더 나누는 것은 파일 단위로 점진 가능합니다.

## 의존 방향 (단방향, 순환 없음)

```mermaid
flowchart TD
    bolt_scene --> config
    config --> geometry
    geometry --> grasp_planning
    config --> grasp_planning
    grasp_planning --> node[pick_place_node]
    geometry --> node
    subgraph ROS 협력(mixin)
      sensing --> node
      robot_state --> node
      moveit_io --> node
      gripper --> node
      scene --> node
      markers --> node
      selection --> node
    end
    grasp_selector -.학습.-> selection
```

- `config` 는 아무것도 import 하지 않는다(상수만; `bolt_scene` 값에서 파생).
- 순수 계층(`geometry`, `grasp_planning`)은 ROS 를 모른다 → 단위 테스트 가능.
- `selection` 이 여러 책임을 조율하지만, 전부 같은 노드 인스턴스의 메서드라
  import 순환이 없다.

## 회귀 주의 지점 (수정 시)

- **`_all_bolt_poses()` 단일 입구**: 이웃 판정·개구 계산은 반드시 이 메서드를
  경유해야 한다. `_bolt_sensed` 를 직접 돌면 폴백 모드에서 이웃이 0개로 보여
  하강이 잘린다.
- **파생 상수 순서**(`config.py`): `GRASP_FLOOR_Z`, `GRASP_DETECT_MIN` 등은 다른
  상수에서 계산된다. 값을 중복 하드코딩하지 말 것.
- **기능 스위치 기본값**: `USE_PICK_BIN=True`, `PICK_BIN_FLOOR=False`,
  `REQUIRE_SENSING=True` 등은 현재 100% 동작을 만든 값이다.
