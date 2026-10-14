# ROS 빈피킹 Supervisor 설계 · 구현 계획 (Claude 실행용)

> 작성: 2026-08-25  
> 적용 범위: PLC가 없는 단일 로봇 빈피킹 셀의 작업 오케스트레이션  
> 대상 코드: `pick_place_node.py`, `desktop_bridge.py`, `protocol.py`, 향후
> `bin_picking_interfaces` 및 Supervisor 노드  
> 상태: **목표 설계/실행 백로그** — 아직 런타임에 구현되지 않음

---

## 1. 한 줄 정의

ROS Supervisor는 **외부에서 받은 고수준 명령을 검증하고, 로봇 준비 상태를 확인한 뒤,
빈피킹 단계들을 순서대로 실행·취소·복구하고 최종 결과를 보존하는 셀 작업 관리자**다.

PLC가 없는 구성에서는 PLC의 순차 제어 일부를 소프트웨어로 대신하지만 다음 기능을
대체하지 않는다.

- 하드웨어 E-STOP, 보호문, 라이트커튼 같은 기능 안전
- FCI/`ros2_control`의 실시간 관절·토크 제어
- MoveIt의 motion planning
- 비전의 pose 추정
- REST/WebSocket 인증과 외부 API 종단점

즉 Supervisor는 “어떻게 관절을 움직일까?”가 아니라 **“지금 이 작업을 시작해도
되는가, 어느 단계인가, 실패·취소 시 다음 행동은 무엇인가?”**를 결정한다.

---

## 2. 권장 전체 구조

```text
Desktop application
  │  HTTPS REST command / WSS events
  ▼
desktop_bridge
  │  RunPickCycle Action client
  ▼
bin_picking_supervisor
  │  명령 승인, 상태기계, 소유권, timeout, 취소, 복구, 결과 보존
  │
  ├─ perception/selection input
  │    └─ pose candidate + confidence + timestamp
  │
  └─ ExecutePickPlace Action client
       ▼
motion_executor
  │  MoveIt 계획, 접근, 하강, 파지, 검증, 리프트, 배치, 후퇴
  ▼
MoveIt / ros2_control / FCI
  ▼
FR3

E-STOP / 보호장치 ── safety relay/controller ── FR3 safety-rated input
```

### 각 계층의 책임

| 계층 | 소유 책임 | 소유하면 안 되는 책임 |
|---|---|---|
| `desktop_bridge` | 인증, HTTP/WS, schema, idempotency, API command store | 작업 순서, MoveIt 직접 실행 |
| Supervisor | admission, 셀/명령 상태, 단계 조정, cancel/recovery 정책 | trajectory 계산, 안전 정지 인증 |
| Motion Executor | 하나의 pick/place goal을 물리적으로 수행 | 외부 사용자 권한, 자동 반복 정책 |
| MoveIt/FCI | 계획 및 controller 실행 | 셀 업무 규칙 |
| 안전회로 | 실제 E-STOP/보호장치 | 일반 작업 상태 표시 |

Supervisor와 API command store의 상태는 연결되지만 동일하지 않다. API store는 네트워크
재시도와 조회를 책임지고, Supervisor는 로봇의 실제 실행 상태를 책임진다. 둘 사이에는
반드시 같은 `command_id`가 보존되어야 한다.

---

## 3. 현재 코드에서 확인한 문제와 이동 경계

현재 `IntegratedPickPlace.run()`은 다음 책임을 한 루프에서 수행한다.

1. MoveIt·그리퍼 준비 대기
2. PlanningScene 초기화
3. Ready 복귀
4. 센싱 readiness 확인
5. 외부 pose 대기 또는 자체 후보 선택
6. `_pick()` 실행
7. `_drop()` 실행
8. 자동 재시도와 다음 사이클 판단
9. ESTOP/GO_HOME/PAUSE 플래그 확인
10. 종료 시 selector 재학습과 Ready 복귀

`_command_cb()`도 `std_msgs/String` 명령을 받아 로컬 bool을 변경하고, `_log_attempt()`는
파지 시도 종료 직후 결과 topic을 발행한다. 이 구조의 한계는 다음과 같다.

- HTTP 접수와 실제 robot acceptance를 구분할 수 없다.
- `PoseStamped`에 command ID와 origin이 없어 correlation이 손실된다.
- `_pick()` 성공은 lift 성공이고 `_drop()` 실패는 최종 RESULT에 반영되지 않는다.
- active MoveIt/gripper goal handle을 셀 수준에서 일관되게 cancel하기 어렵다.
- 프로세스가 재시작되면 실행 중 명령이 무엇이었는지 복구할 수 없다.
- 자동 반복, motion primitive, 외부 명령 처리의 변경 이유가 한 파일에 섞인다.

### 권장 책임 이동

| 현재 코드 | 목표 위치 | 이유 |
|---|---|---|
| `run()`의 while/다음 사이클 판단 | Supervisor | 셀 순차 제어 |
| `_estop_requested`, `_paused`, `_go_home_requested` | Supervisor state/event | bool 조합 대신 유효 전이 사용 |
| 외부 command admission | Supervisor | readiness·owner·busy gate 통합 |
| `_pick()` + `_drop()` | Motion Executor Action | 하나의 물리 작업 단위 |
| `get_next_optimal_bolt_pose()`의 정책 판단 | Supervisor/selection 계층 | 외부 goal과 자체선택 구분 |
| MoveIt/TF/gripper/scene 세부 함수 | 기존 Mixin/Executor | Supervisor가 세부 모션을 몰라야 함 |
| `_log_attempt()` 학습 기록 | selection 계층에 유지 | grasp label의 단일 입구 유지 |
| cycle 최종 결과 발행 | Supervisor | place까지 포함한 terminal result |

대형 일괄 이동은 금지한다. 기존 `_pick()`/`_drop()`을 먼저 Action으로 감싼 후,
`run()`의 orchestration을 단계별로 Supervisor에 옮긴다.

---

## 4. 세 개의 독립 상태기계

모든 상태를 enum 하나에 넣으면 `PAUSED + GRASPING + CANCEL_REQUESTED` 같은 조합을
표현하지 못하거나 상태 수가 폭발한다. 셀, 명령, 실행 단계는 분리한다.

### 4.1 셀 운전 상태 `CellMode`

```text
BOOTING
  → INITIALIZING
  → READY
      → AUTO_RUNNING
      → MANUAL_RUNNING
      → PAUSED
      → STOPPING
  → FAULT
      → RECOVERING
      → READY
  → MAINTENANCE
  → SHUTTING_DOWN
```

정의:

| 상태 | 의미 | 신규 motion goal |
|---|---|---|
| `BOOTING` | process 시작, dependency 미확인 | 거부 |
| `INITIALIZING` | profile/scene/action server 준비 중 | 거부 |
| `READY` | 명령을 안전하게 검증·접수 가능 | 허용 |
| `AUTO_RUNNING` | 자동 cycle 실행 중 | 정책에 따라 queue 또는 busy 거부 |
| `MANUAL_RUNNING` | 단일 operator 명령 실행 중 | 추가 동작 거부 |
| `PAUSED` | 다음 안전 지점에서 진행 보류 | 신규 동작 거부 |
| `STOPPING` | active goal cancel/후퇴 처리 중 | 거부 |
| `FAULT` | 자동 진행 불가, 원인 유지 | 거부 |
| `RECOVERING` | scene/robot/gripper 상태 재동기화 | 거부 |
| `MAINTENANCE` | 수동 점검 모드 | 자동 명령 거부 |

### 4.2 외부 명령 상태 `CommandState`

```text
RECEIVED
  → VALIDATING
      ├─ REJECTED
      └─ QUEUED
           ├─ EXPIRED
           └─ DISPATCHING
                ├─ REJECTED
                └─ ROBOT_ACCEPTED
                     → EXECUTING
                         ├─ CANCEL_REQUESTED
                         │    ├─ CANCELED
                         │    └─ CANCEL_FAILED
                         ├─ SUCCEEDED
                         ├─ FAILED
                         └─ INTERRUPTED
```

핵심 규칙:

- `RECEIVED/QUEUED`는 robot acceptance가 아니다.
- `ROBOT_ACCEPTED`는 ROS Action server가 goal을 수락한 뒤에만 기록한다.
- `SUCCEEDED`는 기본적으로 place/release/retreat까지 완료한 전체 cycle 성공이다.
- bridge/Supervisor 재시작 전 `EXECUTING`이던 명령은 자동 재실행하지 않는다.
- terminal state에서 다른 state로 되돌아가는 전이는 금지한다.
- 같은 `command_id`의 중복 goal은 새 motion을 만들지 않는다.

### 4.3 물리 실행 단계 `CyclePhase`

```text
PRECHECK
TARGET_VALIDATION
SCENE_SYNC
PLAN_APPROACH
MOVE_APPROACH
DESCEND
CLOSE_GRIPPER
VERIFY_GRASP
ATTACH
LIFT
TRANSFER
PLAN_PLACE
PLACE
RELEASE
DETACH
RETREAT
COMPLETE
```

각 단계는 시작/완료 timestamp, retry 수, failure code를 가진다. 현재
`protocol.ROBOT_PHASES`는 이 목표 단계와 동기화하거나 호환 매핑을 명시해야 한다.

---

## 5. READY와 명령 admission

### 5.1 `READY` 진입 조건

다음 조건을 모두 만족해야 한다.

- 활성 robot profile validation 통과
- motion executor Action server 발견
- MoveGroup/Cartesian/FK/IK/PlanningScene dependency 준비
- arm/gripper controller action server 준비
- `/joint_states`가 설정된 freshness 이내
- reference frame→TCP TF가 freshness 이내
- PlanningScene 초기 동기화 성공
- gripper가 known state
- 하드웨어 안전 상태가 운전 허용임을 읽을 수 있음(실물 모드)
- 미해결 `FAULT`와 interrupted command가 없음

`moveit_ok = joint_state is not None` 같은 단일 bool로 READY를 판정하지 않는다. 각
dependency와 최근 성공 시각을 readiness detail로 제공한다.

### 5.2 명령별 admission gate

`PICK_BOLT` 예시:

```text
cell mode가 READY인가?
operate scope와 active operator lease가 유효한가?
다른 exclusive motion command가 없는가?
command TTL이 남아 있는가?
pose clock domain을 비교할 수 있는가?
pose가 stale하지 않은가?
frame과 robot profile이 일치하는가?
position/quaternion/axis/rank가 schema를 만족하는가?
workspace와 작업셀 경계 안인가?
motion executor가 ready인가?
```

거부할 때는 로봇 topic에 publish하지 않고 stable code를 반환한다.

```text
CELL_NOT_READY
COMMAND_BUSY
LEASE_REQUIRED
COMMAND_EXPIRED
CLOCK_DOMAIN_MISMATCH
STALE_TARGET
FRAME_MISMATCH
TARGET_OUT_OF_WORKSPACE
MOTION_EXECUTOR_UNAVAILABLE
```

---

## 6. ROS 인터페이스 설계

현재 `bin_picking`은 `ament_python` 패키지다. ROS custom `.action/.msg/.srv` 생성을 같은
패키지에 억지로 넣지 말고 별도의 `ament_cmake` interface package를 만든다.

```text
src/
├─ bin_picking_interfaces/
│  ├─ CMakeLists.txt
│  ├─ package.xml
│  ├─ action/
│  │  ├─ RunPickCycle.action
│  │  └─ ExecutePickPlace.action
│  ├─ msg/
│  │  ├─ CellState.msg
│  │  ├─ CycleEvent.msg
│  │  └─ DependencyState.msg
│  └─ srv/
│     ├─ SetOperatingMode.srv
│     └─ ResetFault.srv
└─ bin_picking/
```

### 6.1 외부 작업 Action: `RunPickCycle.action`

```text
# Goal
string command_id
string bolt_id
uint32 rank
geometry_msgs/PoseStamped target_pose
geometry_msgs/Vector3 bolt_axis
uint32 ttl_ms
string source_clock
uint64 observed_at_ns
---
# Result
bool success
string terminal_state
string terminal_phase
string fail_reason
bool retry_suggested
uint64 cycle_id
float64 duration_s
---
# Feedback
string phase
float32 progress
uint32 retry_count
string detail
```

`desktop_bridge`는 이 Action의 client다. Goal response를 받아야
`ROBOT_ACCEPTED/REJECTED`를 확정한다.

### 6.2 내부 실행 Action: `ExecutePickPlace.action`

외부 계약과 모션 실행 계약을 분리한다. 내부 goal에는 이미 검증된 target, profile,
policy snapshot을 전달하고 executor가 필요한 세부 feedback/metric을 반환한다.

```text
# Goal
string command_id
uint64 cycle_id
string bolt_id
geometry_msgs/PoseStamped target_pose
geometry_msgs/Vector3 bolt_axis
float32 speed_scale
uint32 max_grasp_retries
---
# Result
bool grasp_success
bool place_success
string terminal_phase
string fail_reason
float64 bolt_rise_m
float64 gripper_width_m
---
# Feedback
string phase
float32 progress
string active_planner
uint32 grasp_retry
```

Action을 두 층으로 분리하면 Supervisor 정책을 바꾸지 않고 executor를 MTC 또는 다른
planner 구현으로 교체할 수 있다.

### 6.3 상태/이벤트

- `/bin_picking/cell_state`: 현재 snapshot, `TRANSIENT_LOCAL` 고려
- `/bin_picking/cycle_events`: 상태 전이 event, reliable
- `/bin_picking/dependency_state`: readiness 진단
- 외부 최종 진실은 v4 command resource와 WS critical event로도 보존

Topic만으로 command를 전달하지 않는다. Topic은 snapshot/event 관측용이다.

---

## 7. 구현 파일 구조

```text
src/bin_picking/bin_picking/
├─ supervisor_core.py          # ROS-free 상태/전이/정책
├─ bin_picking_supervisor.py   # rclpy Action server/client adapter
├─ command_store.py            # command/cycle 상태 영속화
├─ motion_executor.py          # 기존 _pick/_drop Action adapter
└─ supervisor_policies.py      # retry/cancel/recovery table
```

### `supervisor_core.py`

순수 Python이어야 한다.

- enum과 dataclass
- 상태 전이 허용표
- admission decision
- retry/recovery decision
- timeout/TTL 계산 입력 모델
- terminal result 조합
- restart reconciliation decision

`rclpy`, TF, MoveIt import를 금지하면 Gazebo 없이 모든 상태 조합을 pytest로 시험할 수
있다. 시간은 `time.time()`을 직접 읽지 않고 호출자가 `now`를 주입한다.

### `bin_picking_supervisor.py`

- ROS Action server/client
- dependency health 구독/조회
- timer/watchdog
- operator command를 core event로 변환
- core가 결정한 side effect 실행
- transition/event 발행
- command store 기록

상태를 callback 여러 곳에서 직접 변경하지 않는다. 모든 입력은 event queue에 넣고 한
transition dispatcher가 순서대로 처리한다. 동시에 들어온 cancel/result/timeout의
결정 순서를 테스트 가능하게 해야 한다.

### ROS Lifecycle 사용 범위

Lifecycle은 다음에 사용한다.

- `unconfigured`: profile/store 미로드
- `inactive`: dependency 준비 중, command 거부
- `active`: Supervisor event 처리 가능
- `finalized`: 종료

`LifecycleNode`가 `CellMode`나 `CyclePhase`를 대신하지는 않는다. 노드 lifecycle과 업무
상태는 별도 축이다.

---

## 8. 명령 동시성·우선순위·소유권

로봇 motion은 기본적으로 한 번에 하나만 허용한다.

```text
우선순위 0: hardware safety input — ROS 밖에서 즉시 동작
우선순위 1: cancel / soft_stop
우선순위 2: recovery / reset_fault / safe_retreat
우선순위 3: manual go_home
우선순위 4: normal pick cycle
우선순위 5: configuration/background task
```

- normal command가 실행 중일 때 두 번째 pick은 busy 거부하거나 bounded queue 1개만
  허용한다. 초기 구현은 **busy 거부**가 더 안전하다.
- desktop observer는 여러 명 가능하지만 active operator lease는 한 명만 가진다.
- 자동운전 중 desktop manual motion은 거부한다.
- lease 만료나 desktop disconnect만으로 active trajectory를 즉시 끊지 않는다.
- 현재 atomic phase를 안전하게 끝낸 뒤 다음 motion 진입을 막는 정책을 기본으로 한다.
- 사용자가 명시적으로 cancel/soft-stop을 보낸 경우에만 cancel policy를 실행한다.

---

## 9. 취소와 soft-stop

취소는 bool 하나가 아니라 요청과 완료가 있는 비동기 절차다.

```text
EXECUTING
  → CANCEL_REQUESTED
  → 하위 MoveIt/gripper goal cancel 요청
  → cancel response 대기
  → 필요하면 phase별 safe recovery
  → CANCELED 또는 CANCEL_FAILED
```

### 단계별 기본 정책

| phase | cancel 후 기본 동작 |
|---|---|
| `PLAN_APPROACH` | planning goal 취소, motion 없음 |
| `MOVE_APPROACH` | trajectory cancel, 정지 확인 |
| `DESCEND` | cancel 후 가능하면 수직 후퇴 |
| `CLOSE_GRIPPER` | 폐쇄 결과와 접촉 상태 확인 후 후퇴 |
| `LIFT` | object attach/실제 파지 상태 확인 후 안전 높이 판단 |
| `TRANSFER` | 물체를 임의로 놓지 않고 safe hold/place로 이동 |
| `PLACE/RELEASE` | 현재 release 상태 확인 후 detach/scene 동기화 |

`soft_stop`은 다음 안전 지점에서 멈추는 application 기능이다. FR3 하드웨어 E-STOP/STO를
대체하지 않으며 UI와 API에서도 `ESTOP`이라는 이름을 사용하지 않는다.

---

## 10. 실패 복구 정책

| failure | 기본 처리 | 자동 재시도 |
|---|---|---:|
| `STALE_TARGET` | motion 없이 새 perception 요청 | 같은 pose 금지 |
| `CLOCK_DOMAIN_MISMATCH` | 계약 오류로 거부 | 금지 |
| `UNREACHABLE` | 후보 제외, 다음 후보 요청 | 정책상 가능 |
| `PLAN_FAIL` | planner/grasp 후보 변경 | 제한 횟수 |
| `DESCEND_FAIL` | 후퇴, scene/TF 재동기화 | 제한 횟수 |
| `GRIP_FAIL` | open, retreat, attempt 기록 | 제한 횟수 |
| `EMPTY_AFTER_LIFT` | detach 상태 정리, 후보 재평가 | 제한 횟수 |
| `TRANSFER_FAIL` | held-object 상태 확인, 안전 위치 | 자동 재시도 신중 |
| `PLACE_FAIL` | 임의 release 금지, safe place/manual recovery | 기본 금지 |
| `TF_STALE` | 신규 goal 차단, dependency 회복 대기 | motion 재실행 금지 |
| `CONTROLLER_LOST` | active command `INTERRUPTED`, cell `FAULT` | 금지 |
| `SAFETY_STOP_ACTIVE` | 하드웨어 상태 해제·승인 전 `FAULT` 유지 | 금지 |

복구 정책은 `fail_reason` 문자열 곳곳에 if문으로 흩뜨리지 않고 table/data로 관리한다.
선택 학습의 grasp label과 place/시스템 failure를 분리한다.

---

## 11. 재시작·연결 단절 정책

### Supervisor 재시작

command store에서 마지막 상태를 읽는다.

- terminal command: 그대로 유지
- `QUEUED`: TTL/owner/readiness 재검증 후 사용자 확인 또는 재개
- `ROBOT_ACCEPTED/EXECUTING/CANCEL_REQUESTED`: 자동 재실행 금지
- 로봇/gripper/PlanningScene 실제 상태 조회 후 `INTERRUPTED` 또는 recovery task 생성
- attach 여부를 추측하지 말고 scene와 실제 gripper/object 상태를 대조

### desktop 연결 단절

- 이미 수락된 cycle은 기본적으로 안전한 종료 지점까지 계속한다.
- 신규 외부 명령은 받지 않는다.
- 결과는 local command store에 기록한다.
- 재접속 시 REST GET/event replay로 복구한다.
- operator lease 만료는 다음 cycle 진입을 막는다.

단순 네트워크 단절을 즉시 trajectory cancel로 연결하면 물체를 든 채 통 위에서 멈추는
등 더 나쁜 상태가 될 수 있다.

---

## 12. 관측성과 불변조건

모든 transition event에 다음을 기록한다.

```text
command_id
cycle_id
trace_id
previous_state
new_state
phase
reason_code
wall timestamp
ROS timestamp + clock domain
retry count
robot profile revision
```

### 반드시 지켜야 할 불변조건

1. 한 로봇에 active exclusive motion command는 최대 1개다.
2. terminal command는 다시 non-terminal이 되지 않는다.
3. `SUCCEEDED`는 place/release/retreat 완료 전 발생하지 않는다.
4. `ROBOT_ACCEPTED`는 Action goal response 이전에 발생하지 않는다.
5. command ID는 bridge→Supervisor→Executor→result에서 바뀌지 않는다.
6. 취소 요청은 terminal result를 얻거나 timeout/failure로 명시 종료한다.
7. 중요 result를 일반 telemetry queue full 때문에 버리지 않는다.
8. 프로세스 재시작은 실행 중 side effect를 자동 반복하지 않는다.
9. Supervisor 상태는 하드웨어 안전 상태를 대체하지 않는다.

---

## 13. 테스트 전략

### 13.1 ROS-free 상태기계 단위 테스트

- 모든 허용/금지 transition
- cancel/result/timeout 동시 입력 순서
- duplicate command ID
- terminal state 불변성
- retry budget
- TTL과 clock mismatch
- startup reconciliation
- owner lease 만료

table-driven test와 property test를 사용한다.

### 13.2 fake Action 통합 테스트

- goal accepted/rejected
- feedback phase 순서
- action server 미발견/늦은 discovery
- cancel accepted/rejected/timeout
- executor가 result 전에 죽는 경우
- duplicate result와 늦게 도착한 result
- Supervisor restart 후 store 복구

### 13.3 Gazebo fault injection

- 정상 pick/place
- grasp 성공 후 place 실패
- DESCEND 중 cancel
- held-object TRANSFER 중 soft-stop
- TF/joint-state/controller 유실
- desktop 단절 중 완료와 재접속
- vision publisher와 desktop command 동시 입력

### 공통 회귀

```bash
cd src/bin_picking
python3 -m pytest test/

# interface package 추가 후
cd /home/yg1/robotarm_main
colcon build --symlink-install --packages-up-to bin_picking
```

---

## 14. Claude용 단계별 구현 백로그

### SUP-01 — ROS-free Supervisor core

**변경**

- `supervisor_core.py`, 상태 enum/dataclass/event/transition table 추가.
- 시간과 side effect를 dependency injection.
- 불변조건 및 transition test 추가.

**수용 기준**

- ROS가 없어도 전체 테스트 실행 가능.
- 금지 전이마다 명시적 error code.
- terminal state 역전이 0건.

### SUP-02 — interface package

**변경**

- `bin_picking_interfaces` `ament_cmake` 패키지 추가.
- `RunPickCycle.action`, `ExecutePickPlace.action`, 상태/event msg 정의.
- 기존 protocol v4 schema와 field 이름/correlation 의미 대조.

**수용 기준**

- clean colcon build 성공.
- Python에서 생성 interface import 성공.
- action goal/result round-trip test.

### SUP-03 — 기존 motion의 Executor Action adapter

**변경**

- 기존 `_pick()`/`_drop()`을 삭제하거나 복사하지 않고 adapter로 감싼다.
- phase feedback 추가.
- grasp result와 place result 분리.
- active MoveIt/gripper goal handle과 cancel 경로 노출.

**수용 기준**

- 기존 L0 시나리오 결과가 adapter 전후 동일.
- place 실패가 최종 success로 보고되지 않음.
- command/cycle ID가 result까지 보존.

### SUP-04 — Supervisor ROS node

**변경**

- `bin_picking_supervisor.py` Action server/client와 event dispatcher 구현.
- readiness detail, admission, exclusive command, transition event 구현.
- launch에 dependency readiness 기반 기동 추가.

**수용 기준**

- executor가 없으면 goal 명시 거부.
- READY 전 motion 0건.
- 동시 pick 두 개 중 하나만 수락.

### SUP-05 — cancel/soft-stop/recovery

**변경**

- phase별 cancel policy 구현.
- active action cancel 결과 추적.
- `soft_stop`과 hardware safety state 분리.
- recovery table 적용.

**수용 기준**

- cancel 요청마다 terminal 결과 존재.
- held-object cancel에서 무조건 gripper open하지 않음.
- controller/safety fault 후 자동 motion 재실행 0건.

### SUP-06 — desktop bridge 연결

**변경**

- `/next_bolt_pose` command 경로를 `RunPickCycle` Action으로 교체.
- API command state와 Supervisor state 매핑.
- bridge의 `_pending_pick` 단일 슬롯 제거.
- v4 command store/idempotency/replay와 연결.

**수용 기준**

- HTTP 접수/Action goal acceptance/execution/result가 구분됨.
- vision pose와 desktop command 동시 실행 시 오상관 0건.
- WS 단절 후 GET으로 terminal result 복구.

### SUP-07 — orchestration 이관 및 기존 루프 축소

**변경**

- `run()`의 while, auto retry, command bool을 Supervisor로 이관.
- `IntegratedPickPlace`는 executor bootstrap 또는 호환 demo wrapper로 축소.
- 기존 fallback selector/step-by-step 동작을 명시적 policy/mode로 보존.

**수용 기준**

- `pick_place_node.py`가 외부 REST/command ownership을 알지 않음.
- auto/manual 양 모드 회귀 통과.
- `_log_attempt()` 단일 학습 기록 경계 유지.

### SUP-08 — persistence와 restart reconciliation

**변경**

- atomic command/cycle transition store.
- startup reconciliation과 `INTERRUPTED` 처리.
- PlanningScene/gripper/held-object 상태 확인 절차.

**수용 기준**

- EXECUTING 중 process kill/restart가 같은 pick을 자동 재실행하지 않음.
- terminal command는 재시작 후 조회 가능.
- 불명확한 held-object 상태는 `FAULT`와 수동 복구 지침으로 드러남.

---

## 15. 권장 실행 순서

| 순서 | 작업 | 선행 |
|---:|---|---|
| 1 | SUP-01 core | 없음 |
| 2 | SUP-02 interfaces | 프로토콜 v4 command/phase naming 초안 |
| 3 | SUP-03 executor adapter | SUP-02 |
| 4 | SUP-04 Supervisor node | SUP-01~03 |
| 5 | SUP-05 cancel/recovery | SUP-04 |
| 6 | SUP-06 bridge 연결 | CP-P01~P03, SUP-04 |
| 7 | SUP-07 기존 루프 이관 | SUP-03~06 |
| 8 | SUP-08 persistence/restart | SUP-04~07 |

프로토콜 작업과의 대응:

- `CP-P01` clock contract → Supervisor TTL/pose freshness
- `CP-P02` ROS Action/correlation → SUP-02~06
- `CP-P03` command store/idempotency → SUP-06/08
- `CP-P04` event replay → transition event 전달
- `CP-P05` operator lease → admission gate
- `BP-C03` pose correlation → SUP-02/06
- `BP-C04` stop semantics → SUP-05
- `BP-C05` place-complete 결과 → SUP-03

---

## 16. 구현 전에 소유자가 결정할 정책

다음은 Claude가 임의로 결정하면 안 된다.

1. desktop 연결/lease 단절 시 현재 cycle을 끝낼지 safe hold에서 멈출지.
2. normal pick command를 busy 거부할지 queue 1개를 허용할지.
3. place 실패 시 사용할 safe drop/holding 위치.
4. 자동 retry 횟수와 후보 교체 권한을 Supervisor가 가질지 desktop이 가질지.
5. `GO_HOME`을 manual 전용으로 할지 자동 recovery에서도 허용할지.
6. interrupted held-object 상태를 확인할 센서/운영자 절차.
7. command store 방식과 보존 기간.

기본 권장은 **busy 거부, active cycle 안전 종료, place 실패 자동 release 금지,
interrupted command 자동 재실행 금지**다.

---

## 17. 완료 정의

Supervisor 도입은 새 노드를 띄우는 것만으로 완료되지 않는다. 다음 조건을 모두 만족해야
한다.

- command acceptance와 실제 robot goal acceptance가 분리된다.
- 한 로봇에는 하나의 exclusive motion command만 실행된다.
- command ID가 API부터 최종 executor result까지 보존된다.
- pick success와 place-complete success가 구분된다.
- phase별 feedback/cancel/recovery가 실제 Action 결과로 관측된다.
- READY가 모든 핵심 dependency freshness를 반영한다.
- 네트워크 단절이나 process restart가 중복 pick을 만들지 않는다.
- 상태기계 핵심은 ROS/Gazebo 없이 단위 테스트된다.
- Supervisor soft-stop과 하드웨어 E-STOP의 경계가 UI·코드·문서에 명확하다.
- 기존 L0 시뮬레이션 파지 성능과 selector 학습 기록에 회귀가 없다.

