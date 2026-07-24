# 데스크톱앱 ↔ 로봇 데이터 계약 (기획)

> **이 문서의 목적 = "무엇을 주고받는가"(데이터 계약)를 먼저 확정한다.**
> 통신 방식(전송 프로토콜)은 **다음 단계**에서 정하고, 그 다음 데스크톱앱 연동에 들어간다.
> 그래서 이 문서는 **§2 데이터 카탈로그가 본론**이고, §4~§7(통신·안전·트윈·실물전환)은 보조다.
>
> 상태: 기획(설계) — 구현 아님.

---

## 0. 아키텍처와 역할

```
컴퓨터비전 ──(포인트클라우드)──▶ 데스크톱앱 ──(1순위 볼트 6D 좌표)──▶ 로봇암
                                    │  [랭킹→1순위 선택]              │ [계획·실행]
                                    │                                 │
                                    ◀──────(관절/상태 텔레메트리)──────┘
                                   [실시간 디지털 섀도우 + 감시·개입 콘솔]
```

| 주체 | 역할 |
|---|---|
| **컴퓨터비전** | 카메라 → 포인트클라우드 생성 |
| **데스크톱앱** | ① 포인트클라우드로 볼트 **랭킹→1순위 선택** ② 로봇에 좌표 지시 ③ 로봇을 **디지털 섀도우**로 실시간 감시 ④ 운영자 개입 |
| **로봇암(ROS2)** | 받은 좌표로 **계획·실행**, 그리고 **도달성 최종 판정**(IK·충돌·관절한계) |

**핵심 분담:** "**집기 좋은지** 랭킹 = 데스크톱 / **실제 도달 가능한지** 판정 = 로봇." 로봇만 자기 기구학을 안다. 데스크톱이 1순위를 줘도 로봇이 도달 불가면 거부하고, 데스크톱은 2순위를 보낸다(§2D).

**설계 원칙:** 지금은 Gazebo/RViz2로 만들지만, **Gazebo가 아니라 "메시지 계약"에 붙인다.** 관절 스트림·URDF·프레임·명령이 시뮬↔실물에서 동일하므로, 실물 전환은 데이터 소스 스왑으로 끝난다(§7).

---

## 1. 세 갈래 데이터 흐름 (한눈에)

| 흐름 | 방향 | 데이터 | 대역/성격 |
|---|---|---|---|
| **F1 인식 입력** | 비전 → 데스크톱 | 포인트클라우드(PointCloud2) | 고대역, **전용 채널** |
| **F2 명령** | 데스크톱 → 로봇 | 1순위 좌표 + 제어명령 | 경량, 신뢰전송 |
| **F3 텔레메트리** | 로봇 → 데스크톱 | 관절/상태/결과/지표 | 스트림 + 이벤트 |

> ⚠ **F1(포인트클라우드)을 F2 명령 채널에 절대 싣지 않는다.** 무거운 데이터가 좌표 명령을 뒤에 줄 세우는 head-of-line 블로킹을 부른다. 물리적으로 다른 채널.

---

# 2. ★ 주고받는 데이터 카탈로그 (본론)

모든 메시지 **공통 봉투(envelope):**

```
{
  "v": 1,                 // 스키마 major 버전
  "type": "PICK_BOLT",    // 메시지 종류
  "id": "s12-0043",       // correlation id (송신측 생성, 유일)
  "corr": null,           // 응답일 때 원 명령의 id 를 echo
  "prio": "NORMAL",       // SAFETY | HIGH | NORMAL | LOW
  "t_wall": 1753305600123000000,  // 호스트 벽시계 (ns) — 연결감시용
  "t_sim":  1753305599980000000,  // ROS/sim clock (ns) — 사이클타임 계산용
  "use_sim_time": true,
  "args": { ... }         // 종류별 페이로드
}
```

## 2A. 데스크톱 → 로봇 (F2: 명령/좌표)

**주 명령은 `PICK_BOLT`** — 매 사이클, 데스크톱이 고른 1순위 볼트 좌표를 준다. 나머지는 운영자 개입·제어용.

| type | 목적 | args (핵심 필드) | 응답 | 우선순위 |
|---|---|---|---|---|
| **`PICK_BOLT`** ★ | **1순위 볼트를 집어라** | `pose{position[3], orientation[4]}`, `frame="fr3_link0"`, `bolt_id`, `rank`, `stamp` | **ACK + RESULT** | NORMAL |
| `START` / `STOP` | 운전 시작 / 우아한 정지 | `mode`, `after(CYCLE\|IMMEDIATE_SAFE)` | ACK(+RESULT) | HIGH |
| `PAUSE` / `RESUME` | 일시정지 / 재개 | — | ACK | HIGH |
| `SET_MODE` | 자동/수동/단계 전환 | `mode(AUTO\|MANUAL\|STEP)` | ACK | NORMAL |
| `STEP` | 1사이클 진행(수동) | `count` | ACK(+RESULT) | NORMAL |
| `SKIP_CURRENT` | 현재 대상 건너뛰기 | `reason` | ACK | HIGH |
| `BLACKLIST_ADD/REMOVE` | 볼트 영구 제외/해제 | `bolt_id` 또는 `region` | ACK+RESULT | NORMAL |
| `HOLD_BOLT / UNHOLD_BOLT` | 이번 무더기서만 보류 | `bolt_id` | ACK | NORMAL |
| `SET_SELECTOR` | 로봇 자체선택 방식 | `LEARNED\|HEURISTIC` | ACK | NORMAL |
| `SET_PLACE_SLOT` | 놓기 슬롯 지정 | `slot \| "AUTO"` | ACK | NORMAL |
| `SET_SPEED` | 속도 스케일 | `scale(0.0–1.0)` | ACK | HIGH |
| `GO_HOME` | 홈 복귀 | `speed` | ACK+RESULT | HIGH |
| **`ESTOP`** | 소프트 비상정지 | `reason` | **즉시 ACK** | **SAFETY** |
| `RESET` | fault/세이프스톱 해제 | `confirm=true` | ACK+상태 | HIGH |
| `ACK_ALARM` | 알람 확인 | `alarm_id` | ACK | NORMAL |
| `GET_STATUS` | 전체 상태 스냅샷 요청 | — | 스냅샷 | LOW |
| `PING` | keepalive | `seq` | `PONG` | LOW |

> **랭킹 전달 방식 (선택):**
> - (기본) **1순위만** `PICK_BOLT`로 보냄 → 로봇이 거부하면 데스크톱이 2순위 전송. (사용자 결정)
> - (대안) 상위 K개를 한 번에 보내 로봇이 "도달 가능한 첫 번째"를 고름 → 왕복 감소. 필요 시 `PICK_RANKED{candidates[K]}`로 확장.
>
> **환경 변경 명령은 없음**(의도된 제약): 빈/통 모델은 이 채널로 바꾸지 않는다. 문제는 SKIP/BLACKLIST/재시도 같은 로봇 로직으로 해결.

## 2B. 로봇 → 데스크톱 (F3: 텔레메트리)

**디지털 섀도우의 연료는 `arm_state`** 스트림. 나머지는 상태/사이클/결과 이벤트.

| type | 목적 | 핵심 필드 | 방식 | 빈도 |
|---|---|---|---|---|
| **`arm_state`** ★ | **트윈용 관절/TCP** | `q[7](rad)`, `tcp[3](m)`, `tcp_quat[4]`, `gripper_width(m)`, `moving(bool)` | 스트림 | **10–30 Hz** |
| `heartbeat` | 생존/연결감시 | `state`, `cycle_id`, `moveit_ok` | 주기 | 1 Hz |
| `state_event` | 상태 전이 | `from`, `to`, `event`, `cycle_id` | 이벤트 | 전이 시 |
| `cycle_event` | 사이클 시작/성공/실패 | `phase`, `bolt_id`, `duration_s`, `fail_reason`, `retries` | 이벤트 | 사이클당 |
| `grasp_plan` | 선택된 파지 계획 | `bolt_id`, `grasp_pos[3]`, `axis_angle`, `aperture_m`, `tilt_deg`, `approach_frac`, `descend_frac`, `source(vision\|selector)` | 이벤트 | 선택 시 |
| `grasp_result` | 파지 판정(지상진실) | `bolt_id`, `success`, `bolt_rise_m`, `gripper_width_m` | 이벤트 | 판정 시 |
| `alert` | 에러/경고 | `severity`, `code`, `msg`, `context` | 이벤트 | 산발 |
| `cycle_metrics` | 집계 지표 | `success_rate`, `avg_cycle_s`, `last_cycle_s`, `bin_remaining`, `blacklisted`, `deferred` | 주기 | 0.2–1 Hz |
| `sensed_bolts` | 로봇이 센싱한 볼트(옵션) | `bolts[{id, pos[3], axis[3], status}]`, `remaining` | on-change | ≤1 Hz |

> **주기 vs 이벤트:** `arm_state`(관절)만 고빈도 스트림, **나머지는 전부 이벤트/저빈도.** 총 대역폭 목표 **~5 KB/s**. 이걸 크게 넘으면 뭔가 잘못 스트리밍 중.
> **모든 메시지에 `cycle_id`**를 심어 "계획–결과–실패"를 한 사이클로 묶는다.

## 2C. 비전 → 데스크톱 (F1: 인식 입력)

| 데이터 | 타입 | 프레임 | 채널 |
|---|---|---|---|
| 포인트클라우드 | `sensor_msgs/PointCloud2` (gz `PointCloudPacked`) | 카메라 광학프레임 → fr3_link0 변환 | **전용(제어 채널 아님)** |
| (옵션) 카메라 정보 | `CameraInfo` | — | 전용 |

데스크톱이 이 포인트클라우드를 받아 **크롭 → 클러스터링 → 볼트별 중심·축 추정 → 랭킹 → 1순위 선택** 후, 그 좌표를 §2A `PICK_BOLT`로 로봇에 보낸다. (지금 로봇의 `bolt_vision.py`가 하던 일이 데스크톱으로 이동.)

## 2D. 명령↔결과 짝짓기 (correlation)

`PICK_BOLT` 같은 시간 걸리는 명령은 **2단계 응답**:

```
데스크톱 → PICK_BOLT {id:"s12-0043", pose:...}
로봇     → ACK       {corr:"s12-0043", accepted:true}
로봇     → RESULT    {corr:"s12-0043", success:false, fail_reason:"UNREACHABLE"}
데스크톱 → PICK_BOLT {id:"s12-0044", pose: <2순위>}      # 거부 시 다음 순위
```

- **응답 3클래스:** ① ACK만(설정성: SET_MODE/SPEED…) ② ACK+RESULT(동작: PICK_BOLT/GO_HOME…) ③ fire-and-forget(PING/스트림)
- `fail_reason` 예: `UNREACHABLE`(도달불가) / `GRASP_MISS`(빈손) / `COLLISION_ABORT` / `IK_FAIL` / `DESCEND_SHORT`
- 부작용 명령(PICK_BOLT)은 **자동 재전송 금지**(중복 픽 방지). 멱등 명령(SET_MODE 등)만 재전송 허용.

---

## 3. 데이터 규약 (프레임 / 단위 / 시간)

- **프레임: `fr3_link0` 고정.** 모든 pose(볼트·grasp·TCP)를 이 프레임으로 통일, 메시지에 `frame` 명시.
- **단위: 길이 m, 각도 rad, 시간 s/ns(타임스탬프).** mm/deg 변환은 **데스크톱 책임.** 필드명에 단위 박기(`tilt_deg`, `aperture_m`).
- **자세 표현: 쿼터니언 `[x,y,z,w]`로 통일.** 오일러 혼용 금지. 스칼라 각(볼트축 정렬각·기울기)만 별도 rad.
- **축: 볼트 축은 정규화 방향벡터 `axis[3]`.**
- **시간 이중 표기(중요):** `use_sim_time=true`면 sim 시계가 벽시계와 다르게 흐른다. → **`t_sim`(사이클타임 계산) + `t_wall`(연결감시) 둘 다** + `use_sim_time` 플래그. sim이 일시정지면 `t_sim`은 멈추고 `t_wall`은 흐르므로 "죽음"과 "sim 정지"를 구분 가능.
- **`seq` 단조증가**로 순서/유실 검출.

---

# 보조 설계 (다음 단계 예고)

> 아래는 데이터 계약이 정해진 뒤 진행할 항목들. 지금은 방향성만 기록.

## 4. (보조) 통신 방식 — 다음 단계에서 결정

- **채널 3분리:** 안전 / 제어명령 / 텔레메트리 를 섞지 않는다. 포인트클라우드는 또 별도.
- **전송 후보:** ① ROS2 네이티브 노드(같은 LAN, QoS 공짜) ② **rosbridge(JSON over WebSocket/TCP)** — 데스크톱이 별개 앱이면 유력 ③ Foxglove(감시·트윈 시각화) ④ raw TCP(마지막 수단).
- **권고:** "TCP/IP"를 원하면 **raw 소켓 손코딩보다 rosbridge(JSON)**. 위 데이터 카탈로그는 어느 방식이든 그대로 쓰는 논리 계약.
- **와이어:** JSON Lines(`compact-json\n`) 기본, 필요 시 length-prefixed로 승격. 모르는 필드 무시(forward-compatible). 재연결 시 **스냅샷+델타+seq 갭감지.**

## 5. (보조) 안전 — E-STOP

- **네트워크 `ESTOP`은 소프트 정지일 뿐, 진짜 안전정지 아님.** 1차 안전 = **물리 E-STOP + 로봇 안전 컨트롤러(STO)**.
- **Deadman(negative logic):** 정상 하트비트가 계속 와야 움직임 → 끊기면 **로봇이 스스로 정지.** 정지 판단 주체는 로봇.
- **RESET 게이팅:** 세이프스톱/알람 상태에선 START/PICK 거부, 명시적 RESET 후에만 재개.
- 지금 시뮬 단계에서 **deadman/RESET의 자리를 프로토콜에 비워두면** 실물에서 하드웨어 안전회로에 물리기만 하면 된다.

## 6. (보조) 디지털 섀도우 (실시간 로봇 뷰)

- 정확히는 **디지털 섀도우**(실물 상태를 실시간 반영하는 거울), 예측형 트윈 아님.
- **필요 데이터 = §2B `arm_state`**(관절 q[7] + TCP) + FR3 URDF. 데스크톱이 FK로 렌더.
- **만들지 말고 얻어라:** **Foxglove 3D 패널**이 URDF+`/joint_states`+`/tf`로 이걸 즉시 그린다. three.js 자작 전에 검토.
- **주의:** 네트워크 지연만큼 과거임 → **감시·확인용**이지 충돌/안전 판정용 아님.

## 7. (보조) 시뮬 → 실물 전환 체크리스트

**그대로 넘어가는 것 (데스크톱 변경 0):**

| 항목 | 시뮬 | 실물 |
|---|---|---|
| 관절 스트림 | Gazebo `/joint_states` | franka_ros2 `/joint_states` |
| URDF / 프레임 / 단위 | FR3 / fr3_link0 / SI | 동일 |
| 명령·텔레메트리 카탈로그 | §2 | 동일 |

**미리 자리를 비워둘 것 (나중에 끼우기 어려움):**

1. **시간:** `use_sim_time` → 벽시계. `t_sim`/`t_wall` 이중 표기로 이미 흡수.
2. **안전:** 실물은 하드웨어 E-STOP+STO 필수. deadman/RESET 게이팅을 지금 넣어둠.
3. **인식:** 실물은 **hand-eye 캘리브레이션** 필요. 데스크톱은 실물 PointCloud2를 같은 규격으로 받도록 설계.
4. **도달성 판정은 로봇에:** 실물은 진짜 충돌·관절한계. 로봇의 `RESULT{UNREACHABLE}` 거부 루프가 안전판.
5. **지연·노이즈:** 실물에서 커짐 → 섀도우는 감시용 원칙 유지.

---

## 부록 A. 메시지 예시

```json
// 데스크톱 → 로봇: 1순위 볼트 지정
{"v":1,"type":"PICK_BOLT","id":"s12-0043","prio":"NORMAL","t_wall":1753305600123000000,"t_sim":1753305599980000000,"use_sim_time":true,
 "args":{"bolt_id":"b_88","rank":1,"frame":"fr3_link0","stamp":1753305599980000000,
         "pose":{"position":[0.412,-0.023,0.187],"orientation":[0.0,0.707,0.0,0.707]}}}

// 로봇 → 데스크톱: 접수 → 결과(도달불가로 거부)
{"v":1,"type":"ACK","corr":"s12-0043","args":{"accepted":true}}
{"v":1,"type":"RESULT","corr":"s12-0043","args":{"success":false,"fail_reason":"UNREACHABLE","retry_suggested":true}}

// 로봇 → 데스크톱: 디지털 섀도우 연료 (10–30Hz 스트림)
{"v":1,"type":"arm_state","t_sim":1753305600010000000,"t_wall":1753305600155000000,
 "args":{"q":[0.0,-0.78,0.0,-2.36,0.0,1.57,0.78],"tcp":[0.40,-0.02,0.25],"gripper_width":0.04,"moving":true}}

// 로봇 → 데스크톱: 파지 성공 판정
{"v":1,"type":"grasp_result","args":{"bolt_id":"b_88","success":true,"bolt_rise_m":0.235,"gripper_width_m":0.004}}
```

## 부록 B. 상태(state) 열거

`IDLE · HOMING · WAITING_TARGET · PLANNING · APPROACHING · DESCENDING · GRASPING · LIFTING · PLACING · RECOVERING · SAFE_STOP · ERROR`

- `SAFE_STOP`/`ERROR`는 latched(RESET 전까지 유지), 나머지는 자동 진행.
- 세부단계(축정렬·개구·기울기)는 서브페이즈로만, 상태로 승격 금지(UI 깜빡임 방지).

---

## 부록 C. 열거형(enum) 사전

| enum | 값 | 쓰이는 곳 |
|---|---|---|
| `state` | IDLE, HOMING, WAITING_TARGET, PLANNING, APPROACHING, DESCENDING, GRASPING, LIFTING, PLACING, RECOVERING, SAFE_STOP, ERROR | heartbeat, state_event |
| `event` | cycle_start, home_done, target_acquired, target_timeout, bin_empty, plan_ok, plan_fail, approach_reached, approach_fail, descend_reached, descend_short, grasp_closed, attach_ok, attach_fail, lift_bolt_rose, empty_grip, place_released, cycle_success, retry_ok, blacklisted, deferred, fatal, estop, link_down, driver_fault | state_event |
| `mode` | AUTO, MANUAL, STEP | SET_MODE, START |
| `selector` | LEARNED, HEURISTIC | SET_SELECTOR, grasp_plan.source(≈) |
| `source` | vision, selector | grasp_plan (외부지정 vs 로봇 자체선택) |
| `bolt_status` | candidate, deferred, blacklist, picked | sensed_bolts[].status |
| `prio` | SAFETY, HIGH, NORMAL, LOW | 모든 명령 봉투 |
| `phase` | start, success, fail | cycle_event |
| `severity` | info, warn, error | alert |
| `stop_after` | CYCLE, IMMEDIATE_SAFE | STOP |
| `recalib_kind` | HAND_EYE, TOOL, BIN | REQUEST_RECALIB |

## 부록 D. `RESULT.fail_reason` 코드 (파지 실패 분류)

로봇이 `PICK_BOLT`/`STEP`/`GO_HOME` 결과로 돌려주는 실패 사유. **데스크톱의 다음 행동(재시도 vs 다음 순위 vs 포기)을 이 코드로 결정한다.**

| code | 발생 단계 | 의미 | 데스크톱 권고 행동 |
|---|---|---|---|
| `REACH_FILTERED` | 사전필터 | 도달범위 밖 (‖y−통중심‖>0.063m 또는 x>0.45m) | **다음 순위** |
| `UNREACHABLE` | PLANNING/IK | IK 해 없음 / 워크스페이스 밖 | **다음 순위** |
| `APERTURE_BLOCKED` | 파지계획 | 벽·이웃으로 개구 확보 불가 | **다음 순위** |
| `PLAN_FAIL` | PLANNING | 모든 OMPL 플래너 계획 실패 | 다음 순위 |
| `APPROACH_FAIL` | APPROACHING | 접근 자세 달성률 게이트 미달 | 재시도 → 다음 |
| `DESCEND_SHORT` | DESCENDING | 하강 달성률<0.995, 볼트 위에서 멈춤 | **재시도** |
| `COLLISION_ABORT` | APPROACH/DESCEND | 충돌 예측/감지로 중단 | 다음 순위 |
| `JOINT_LIMIT` | any | 관절 한계 근접/초과(J7 등) | 다음 순위 |
| `ATTACH_FAIL` | GRASPING | attach 실패 | 재시도 |
| `GRASP_MISS` | LIFTING | 리프트 후 볼트 안 올라옴(빈손) | 재시도 → N회 후 blacklist |
| `TIMEOUT` | any | 동작 타임아웃(ACCEPT/RESULT) | 재시도 |
| `ABORTED` | any | 상위 중단(STOP/ESTOP/모드전환) | — |

> `retry_suggested`(bool)와 `retries`(u8, 이번 무더기 epoch 내 연속 실패수)를 함께 실어, 데스크톱이 "N회 넘으면 blacklist" 정책을 스스로 적용할 수 있게 한다. (로봇도 자체 `MAX_NO_PROGRESS`로 판단하지만, 데스크톱이 랭킹 주체이므로 정책 공유.)

## 부록 E. `alert.code` (경고/에러 스트림)

| code | severity | 의미 | UI 처리 |
|---|---|---|---|
| `SELECTOR_UNAVAILABLE` | info | 학습 선택기 로드 실패 → 휴리스틱 폴백 | 배너 |
| `BIN_EMPTY` | info | 집는 통 비었음 | 상태 표시 |
| `NO_REACHABLE_BOLT` | warn | 도달 가능한 후보 없음(전부 필터/거부) | 경고 |
| `MOVEIT_PLAN_FAIL` | warn | 계획 실패(폴백 진행 중) | 로그 |
| `JOINT_NEAR_LIMIT` | warn | 관절이 한계 근접(<0.10 rad) | 경고 + 관절 하이라이트 |
| `LINK_STALE` | warn | 데스크톱 하트비트 지연(임계 근접) | 연결 상태 STALE |
| `SENSING_LOST` | error | 볼트 센싱 끊김(REQUIRE_SENSING=True) | 정지 유도 |
| `LINK_DOWN` | error | 제어 링크 다운 → 로봇 자동 SAFE_STOP | 큰 경고 + 재연결 |
| `DRIVER_FAULT` | error | 컨트롤러/드라이버 이상 | ERROR 상태 |

`alert.context`(obj, opt)에 근거 데이터 동봉: `{moveit_err_code, joint_id, frac, bolt_id}` 등.

## 부록 F. 정밀 필드 스펙 (핵심 3종)

타입 표기: `f64/f32`=부동소수, `[n]`=고정길이 배열, `u8/u16/u32/u64`=부호없는 정수, `str`, `bool`, `enum`. 단위는 필드명/설명에 명시. `?`=선택(opt).

### `PICK_BOLT.args` (데스크톱 → 로봇, 주 명령)
| 필드 | 타입 | 단위 | 필수 | 설명 |
|---|---|---|---|---|
| `pose.position` | f64[3] | m | ✔ | fr3_link0 기준 파지점 xyz |
| `pose.orientation` | f64[4] | — | ✔ | 쿼터니언 [x,y,z,w] |
| `frame` | str | — | ✔ | `"fr3_link0"` 고정 |
| `bolt_id` | str | — | ✔ | 데스크톱이 부여한 볼트 식별자 |
| `rank` | u8 | — | ✔ | 랭킹 순위(1=최우선) |
| `axis` | f32[3] | — | ? | 볼트 축 단위벡터(로봇 정렬 참고용) |
| `stamp` | u64 | ns | ✔ | 이 좌표가 유효한 인식 시각(t_sim) |
| `deadline` | u64 | ns | ? | 이 시각 넘으면 stale로 폐기 |

### `arm_state.args` (로봇 → 데스크톱, 섀도우 연료, 10–30 Hz)
| 필드 | 타입 | 단위 | 필수 | 설명 |
|---|---|---|---|---|
| `q` | f32[7] | rad | ✔ | fr3_joint1..7 위치 |
| `tcp` | f32[3] | m | ✔ | fr3_hand_tcp xyz |
| `tcp_quat` | f32[4] | — | ? | TCP 자세 쿼터니언 |
| `gripper_width` | f32 | m | ✔ | 손가락 개구 폭 |
| `joint_margin` | f32[7] | rad | ? | 각 관절 한계까지 여유 |
| `moving` | bool | — | ✔ | 이동 중 여부 |

> **유실 허용:** 한 프레임 빠져도 섀도우는 다음 프레임으로 복구된다(최신값 우선). 이벤트 메시지(grasp_result 등)와 달리 무손실 보장 불필요.

### `grasp_plan.args` (로봇 → 데스크톱, 선택된 파지계획, 사이클당 1)
| 필드 | 타입 | 단위 | 설명 |
|---|---|---|---|
| `bolt_id` | str | — | 대상 볼트 |
| `grasp_pos` | f32[3] | m | 최종 파지점 |
| `axis_angle` | f32 | rad | 볼트축 정렬각 |
| `aperture_m` | f32 | m | pre-grasp 개구 |
| `tilt_deg` | f32 | deg | 접근 기울기(0/±15/±30) |
| `approach_frac` | f32 | 0–1 | 접근 직선 달성률 |
| `descend_frac` | f32 | 0–1 | 하강 직선 달성률 |
| `source` | enum | — | vision \| selector |
