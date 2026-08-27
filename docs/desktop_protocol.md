# 데스크톱앱 ↔ 로봇 데이터 계약 (기획)

> **이 문서의 목적 = "무엇을 주고받는가"(데이터 계약)를 먼저 확정한다.**
> 통신 방식(전송 프로토콜)은 **다음 단계**에서 정하고, 그 다음 데스크톱앱 연동에 들어간다.
> 그래서 이 문서는 **§2 데이터 카탈로그가 본론**이고, §4~§7(통신·안전·트윈·실물전환)은 보조다.
>
> 상태: §2(데이터 카탈로그) 기획 확정 + **데이터 정합성 감사·보완 완료**
> (2026-08-03, `PROTOCOL_VERSION` 1→2). §4(통신 방식)는 **구현 완료**
> (`desktop_bridge` 노드) — 단, PICK_BOLT 를 뺀 나머지 명령은 아직 ACK
> 골격만(§4 표 참고). 데스크톱앱 본체는 별도 팀 구현 예정 — 그 전까지
> 로봇쪽 통신 종단점만 준비해 둔다.
>
> **2026-08-04, `PROTOCOL_VERSION` 2→3:** 전송 방식을 단일 WebSocket
> 봉투에서 **REST(명령) + WebSocket(텔레메트리 전용) 하이브리드**로 전환하고
> **Bearer 토큰 인증 + 선택적 TLS** 를 도입했다(§4). v1→v2 때처럼 호환 shim
> 없이 클린 브레이크 — 데스크톱 앱 본체가 아직 없어 안전하다. §2 데이터
> 카탈로그(필드 스펙) 자체는 안 바뀌었다, 어느 채널로 오가는지만 바뀌었다.
>
> **2026-08-25 정밀 감사:** v3의 현재 계약은 이 문서가 계속 설명한다. 다만
> clock domain, HTTP 접수/robot ACK 분리, 중요 이벤트 유실·재접속, WS query token,
> scope/제어권에서 실물 운용 전 수정할 문제가 확인됐다. 목표 v4 계약과 Claude용
> 작업 ID·수용 기준은 [`desktop_protocol_upgrade_plan.md`](./desktop_protocol_upgrade_plan.md)를
> 따른다. 해당 작업이 구현되기 전까지 계획서의 v4 예시를 현재 API로 사용하면 안 된다.
>
> **"어떻게 접속하는가"는 이 문서가 아니라 [`desktop_connection_guide.md`](./desktop_connection_guide.md)
> 참고** — 접속 주소(WSL2 네트워크 유의사항 포함)·실행 방법·빠른 검증·
> 트러블슈팅·실측 검증 내역을 담았다(2026-08-04).

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
| `RESET` | fault/세이프스톱 해제 | `confirm=true` | ACK+상태 | HIGH |¹
| `ACK_ALARM` | 알람 확인 | `alarm_id` | ACK | NORMAL |
| `GET_STATUS` | 전체 상태 스냅샷 요청 | — | 스냅샷 | LOW |

¹ **RESET `confirm` 시행됨(2026-08-27, BP-C04a):** `args.confirm` 이 불리언 `true`
가 아니면(누락·`false`·문자열 `"true"`·`1` 포함) `ACK{accepted:false,
errors:["RESET requires confirm=true"]}` 로 거부되고 로봇에 발행되지 않으며 세이프
스톱도 풀리지 않는다. 검증 로직은 `protocol.validate_command()`(순수)가 단일 소스다.
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
| **`arm_state`** ★ | **트윈용 관절/TCP** | `q[7](rad)`, `tcp[3](m)`, `tcp_quat[4]`, `gripper_width(m)`, `joint_margin[7](rad)`, `moving(bool)`, `last_cycle_id` | 스트림 | **10–30 Hz** |
| `heartbeat` | 생존/연결감시 | `state`, `last_cycle_id`, `moveit_ok` | 주기 | 1 Hz |
| `state_event` | 상태 전이(**예약 — 현재 미발행**) | `from`, `to`, `event`, `cycle_id` | 이벤트 | 전이 시 |
| `cycle_event` | 사이클 시작/성공/실패(**예약 — 현재 미발행**) | `phase`, `bolt_id`, `duration_s`, `fail_reason`, `retries` | 이벤트 | 사이클당 |
| `grasp_plan` | 선택된 파지 계획(**예약 — 현재 미발행**) | `bolt_id`, `grasp_pos[3]`, `axis_angle`, `aperture_m`, `tilt_deg`, `approach_frac`, `descend_frac`, `source(vision\|selector)` | 이벤트 | 선택 시 |
| `grasp_result` | 파지 판정(지상진실, 로봇 자체선택 사이클만 — 데스크톱 명령 사이클은 `RESULT`로 대신 나감) | `bolt_id`, `success`, `fail_reason`, `bolt_rise_m`, `gripper_width_m` | 이벤트 | 판정 시 |
| `alert` | 에러/경고 | `severity`, `code`, `msg`, `context` | 이벤트 | 산발 |
| `cycle_metrics` | 집계 지표(**예약 — 현재 미발행**) | `success_rate`, `avg_cycle_s`, `last_cycle_s`, `bin_remaining`, `blacklisted`, `deferred` | 주기 | 0.2–1 Hz |
| `sensed_bolts` | 로봇이 센싱한 볼트(**예약 — 현재 미발행**) | `bolts[{id, pos[3], axis[3], status}]`, `remaining` | on-change | ≤1 Hz |

> **주기 vs 이벤트:** `arm_state`(관절)만 고빈도 스트림, **나머지는 전부 이벤트/저빈도.** 총 대역폭 목표 **~5 KB/s**. 이걸 크게 넘으면 뭔가 잘못 스트리밍 중.
> **`cycle_id` vs `last_cycle_id`(중요, 2026-08-03 수정):** `cycle_id`는 **사이클에 종속된 메시지**(`RESULT`, `grasp_result`)에만 실린다 — 발급 주체는 로봇 파이프라인(`selection.py`의 단일 카운터) 하나뿐이고, 브릿지는 절대 스스로 지어내지 않는다. `heartbeat`/`arm_state`처럼 **타이머로 도는, 특정 사이클에 종속되지 않는 메시지**는 대신 `last_cycle_id`(nullable — "가장 최근에 관측된 사이클, 진행 중이란 뜻 아님")를 쓴다. (예전 초안은 "모든 메시지에 cycle_id를"이라고 했으나, 브릿지가 이를 만족시키려면 다음 사이클의 id를 추측해야 해 근거 없는 값을 보내게 되므로 폐기했다.)

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

- **응답 3클래스:** ① ACK만(설정성: SET_MODE/SPEED…, 스키마 위반 시 `ACK{accepted:false, errors:[...]}`도 이 클래스) ② ACK+RESULT(동작: PICK_BOLT/GO_HOME…) ③ fire-and-forget(PING/스트림)
- `fail_reason` 예: `UNREACHABLE`(도달불가) / `GRASP_MISS`(빈손) / `COLLISION_ABORT` / `DESCEND_SHORT` — 전체 고정 어휘와 실제 매핑은 부록D 참고(2026-08-03: 로봇 파이프라인이 실제로 발행하는 코드와 정확히 맞춰 재작성됨).
- `RESULT.bolt_id`는 **데스크톱이 `PICK_BOLT`에 실어 보낸 원래 id**를 그대로 echo(성공적으로 상관관계가 맞은 경우에만 존재). 로봇이 내부적으로 다시 매칭한 id는 `matched_bolt_id`(nullable, 항상 존재)로 따로 실린다 — 로봇은 desktop_bridge 가 받은 pose 에서 가장 가까운 센싱 볼트를 자체적으로 다시 찾으므로, 데스크톱의 `bolt_id`와 다를 수 있다.
- 부작용 명령(PICK_BOLT)은 **자동 재전송 금지**(중복 픽 방지). 멱등 명령(SET_MODE 등)만 재전송 허용.
- **오상관 방지:** 로봇이 데스크톱 명령과 무관하게 자체선택으로 돈 사이클의 결과는 `origin:'ROBOT'`으로 표시되어 `grasp_result`로만 나가며, 대기 중인 `PICK_BOLT`의 `corr`/`bolt_id`가 잘못 실리는 일이 없다.

---

## 3. 데이터 규약 (프레임 / 단위 / 시간)

- **프레임: `fr3_link0` 고정.** 모든 pose(볼트·grasp·TCP)를 이 프레임으로 통일, 메시지에 `frame` 명시.
- **단위: 길이 m, 각도 rad, 시간 s/ns(타임스탬프).** mm/deg 변환은 **데스크톱 책임.** 필드명에 단위 박기(`tilt_deg`, `aperture_m`).
- **자세 표현: 쿼터니언 `[x,y,z,w]`로 통일.** 오일러 혼용 금지. 스칼라 각(볼트축 정렬각·기울기)만 별도 rad.
- **축: 볼트 축은 정규화 방향벡터 `axis[3]`.**
- **시간 이중 표기(중요):** `use_sim_time=true`면 sim 시계가 벽시계와 다르게 흐른다. → **`t_sim`(사이클타임 계산) + `t_wall`(연결감시) 둘 다** + `use_sim_time` 플래그. sim이 일시정지면 `t_sim`은 멈추고 `t_wall`은 흐르므로 "죽음"과 "sim 정지"를 구분 가능.
- **`seq` 단조증가**로 순서/유실 검출.

---

# 보조 설계

> §4 는 이제 확정·구현 완료(2026-08-03). §5~§7 은 여전히 다음 단계 방향성만 기록.

## 4. 통신 방식 — 확정: REST(명령) + WebSocket(텔레메트리) 하이브리드 + 토큰 인증

**결정: rosbridge 가 아니라, 로봇쪽에 직접 구현한 경량 서버(aiohttp).** 명령은
REST API, 텔레메트리(스트림)는 WebSocket — 같은 포트(기본 8765) 안에서 경로로만
구분한다. 구현: `src/bin_picking/bin_picking/desktop_bridge.py`
(`ros2 run bin_picking desktop_bridge`).

> v2 까지는 명령도 텔레메트리와 같은 WebSocket 연결 하나에 봉투(envelope) JSON을
> 얹어 주고받았다. v3(2026-08-04)에서 **명령은 REST로, 텔레메트리는 WS 전용**으로
> 분리하고 **Bearer 토큰 인증**을 추가했다 — 아래 "왜 하이브리드로 바꿨나" 참고.

### 왜 rosbridge 가 아닌가

기획 당시(§4 원안) rosbridge(JSON over WebSocket)를 유력 후보로 뒀지만, 실제
구현 단계에서 재검토했다:

| 기준 | rosbridge_server | 자체 서버(채택) |
|---|---|---|
| 데스크톱 쪽 요구사항 | roslibjs/roslibpy 같은 rosbridge 클라이언트 라이브러리 필요 | **아무 언어의 흔한 HTTP/WebSocket 클라이언트**(curl 포함) 하나면 됨 |
| 와이어 포맷 | `{op:"publish", topic, msg:{...}}` 로 한 겹 더 감쌈 | 명령은 **§2A 필드를 그대로 JSON body 로**, 텔레메트리는 **§2 봉투(envelope) JSON 을 그대로** — 이 문서가 곧 API |
| 설치 | `sudo apt install ros-jazzy-rosbridge-suite` (시스템 패키지, 관리자 권한) | `pip install aiohttp` (사용자 권한) |
| 로봇 프로세스 결합도 | 별도 서버 프로세스 | pick_place_node 와 **분리된 독립 ROS2 노드** — 서로 안 죽는다 |

데스크톱앱을 **다른 팀이 별도로 개발**한다는 전제에서, "ROS 없이도 이 문서
그대로 붙을 수 있다"는 게 rosbridge 대비 결정적 이점이었다. §2 의 데이터
카탈로그(필드 스펙)는 그대로 유지 — 바뀐 건 전송 방식뿐.

### 왜 REST+WS 하이브리드로 바꿨나 (v2→v3)

v2 는 명령도 텔레메트리와 같은 WS 연결 하나로 받았다. 실사용을 앞두고 두 가지
문제가 보였다:

- **보안 공백**: 인증이 전혀 없었다 — 누구든 그 포트에 연결하면 바로 `PICK_BOLT`
  같은 로봇 동작 명령을 보낼 수 있었다.
- **데스크톱팀 진입장벽**: 명령 하나 보내려고 항상 WS 연결을 먼저 맺고 상태
  머신(연결→인증→명령→응답 매칭)을 관리해야 했다 — curl 한 줄로 테스트가 안 됐다.

REST(명령)+WS(스트림)로 나누면 두 문제가 자연스럽게 풀린다: 명령은 표준 HTTP
요청/응답이라 `Authorization` 헤더로 인증을 걸기 쉽고, curl/Postman/각 언어의
흔한 HTTP 클라이언트로 바로 테스트 가능하다. 텔레메트리(20Hz `arm_state` 등)는
REST 로 흉내내기 어려운 고빈도 스트림이라 WS 로 남긴다(순수 서버→클라이언트,
클라이언트가 보내는 메시지는 더 이상 명령으로 처리하지 않는다).

### 아키텍처: 왜 별도 노드인가

`desktop_bridge` 는 `integrated_pick_place`(1000줄+, Gazebo/MoveIt 의존)와
**같은 프로세스에 넣지 않았다**:

- 통신 프로토콜과 파지 로직은 서로 다른 이유로 바뀐다 → 파일이 아니라 **프로세스**를 분리해, 브릿지를 고치다 실수해도 실행 중인 파지 사이클이 안 죽는다.
- **Gazebo/MoveIt 없이 브릿지 혼자 켜서 통신 자체만 검증**할 수 있다 — `/joint_states` 가 없으면 `arm_state` 만 안 나갈 뿐, REST 명령/GET_STATUS/heartbeat 는 그대로 동작한다.
- 로봇 파이프라인과의 결합점은 딱 둘, 전부 **기존 ROS 토픽**이라 프로세스가 갈라져도 그대로 동작한다:
  - `PICK_BOLT` 수신 → 이미 있던 "외부 비전 입력" 토픽(`/next_bolt_pose`, config.py `EXT_POSE_TOPIC`)에 그대로 재발행. `get_next_optimal_bolt_pose()`(pick_place_node.py) 가 원래 비전 노드를 위해 열어 둔 경로를 그대로 재사용 — 파지 로직 코드는 한 줄도 안 바꿨다.
  - 파지 결과 → `selection.py` 의 `_log_attempt()`(모든 `_pick()` 종결 지점이 지나는 **단일 입구**, architecture.md 참고)에 발행 훅 1개 추가 → `/bin_picking/cycle_result` → 브릿지가 구독해 `RESULT` 로 변환. 이 콜백은 전송 방식과 무관하다 — PICK_BOLT 가 REST 로 들어왔다는 사실을 모른 채, `_pending_pick['id']`(=REST 응답의 `id`)로만 상관관계를 맞춘다.

### 채널 / 경로

| 경로 | 메서드 | 내용 |
|---|---|---|
| `/api/v1/pick_bolt` | POST | §2A `PICK_BOLT` — body 는 args 그대로. 응답: `{id, accepted, errors?}`(HTTP 200) |
| `/api/v1/estop` | POST | §2A `ESTOP`(소프트) — 응답: `{accepted:true}` |
| `/api/v1/command` | POST | 나머지 ACK-only 명령(§2A, `START`/`SET_SPEED`/...) 범용 엔드포인트 — body `{"type":"...", "args":{...}}` |
| `/api/v1/status` | GET | §2A `GET_STATUS` 스냅샷을 그대로 반환 |
| `/ws/telemetry` | GET(업그레이드) | §2B 텔레메트리 전용 스트림 — 접속 즉시 STATUS 스냅샷 1회 + 이후 arm_state(20Hz)/heartbeat(1Hz)/RESULT/grasp_result/ALERT |
| F1(포인트클라우드) | — | 그대로 별도 — 이 브릿지를 안 거친다(§2C 원안 유지) |

**PICK_BOLT 2단계 응답**: REST POST 는 §2D 의 1단계(ACK)만 동기로 즉시 반환한다.
2단계(`RESULT`, 최대 20~25초 걸림)는 REST 로 붙들고 있지 않고 WS 텔레메트리
스트림에 `corr`=REST 응답의 `id` 로 실려 나간다 — 데스크톱은 POST 응답의 `id` 를
저장해 뒀다가 WS 스트림에서 같은 `corr` 를 찾으면 된다.

**인증**: 모든 `/api/*` 는 `Authorization: Bearer <token>` 헤더 필수(없거나
틀리면 401). `/ws/telemetry` 는 핸드셰이크에 커스텀 헤더를 못 붙이는 클라이언트도
있어 쿼리스트링 `?token=<token>` 도 허용한다(핸드셰이크 자체가 401 로 거부됨 —
연결 후 별도 인증 메시지 없음). 토큰은 ROS 파라미터 `api_token` — 안 주면 기동 시
임의 생성 후 로그에 크게 출력한다(로컬 테스트는 설정 없이 바로 됨).

**TLS(선택)**: `tls_cert`/`tls_key` 파라미터(인증서/키 파일 경로)를 주면
HTTPS/WSS 로 뜬다. 안 주면 평문 HTTP/WS + 경고 로그 — 신뢰된 사설망 밖에
노출하지 말 것(§5). 자체서명 인증서 생성법은 `desktop_connection_guide.md` 참고.

**포트:** 기본 `0.0.0.0:8765` (ROS 파라미터 `host`/`port` 로 변경 가능, REST/WS 공용).
**재연결:** WS 클라이언트가 붙는 즉시 `STATUS` 스냅샷을 먼저 보낸다. 이후
`seq`(봉투 최상위 필드, 단조증가)로 유실 감지.
**시계:** 브릿지는 `use_sim_time` 을 기본 `false`(벽시계)로 둔다 — Gazebo 없이
혼자 켜졌을 때 `/clock` 이 없으면 sim 시계가 절대 안 흘러 타이머가 전부
멈추는 버그를 실제로 겪었다. Gazebo 스택과 같이 띄울 때만 launch 인자로
`use_sim_time:=true` 를 넘겨 나머지 노드와 시계를 맞춘다.

### 검증 방법

**전체 스택 실기동 검증 — 명령 한 줄 (2026-08-03 추가):**
```bash
ros2 launch bin_picking desktop_integration_demo.launch.py
```
Gazebo+MoveIt → 볼트 스폰 → `desktop_bridge` → `integrated_pick_place` 를
지연 기동으로 순서대로 다 띄운다. 의도적으로 비전(`vision_pipeline.launch.py`/
`bolt_vision`)은 포함하지 않는다 — 비전은 데스크톱 앱과 직접 통신하는 별개
파이프라인이라(다른 팀 담당), 이 launch 의 범위는 **로봇팔 ↔ 데스크톱 통신
검증**으로 의도적으로 한정했다. `rviz`/`auto`/`bolts_delay`/`apps_delay`
인자로 조정 가능.

**통신 프로토콜만 (데스크톱앱 없이, Gazebo도 불필요):**
```bash
ros2 run bin_picking desktop_bridge --ros-args -p api_token:=<토큰>   # 브릿지만 (Gazebo 불필요)
python3 src/bin_picking/tools/mock_desktop_client.py --token <토큰>    # 데스크톱 대역 목 클라이언트 (ROS 무의존)
python3 src/bin_picking/tools/mock_desktop_client.py --token <토큰> --assert   # 자동 검증
```
목 클라이언트는 REST 로 `GET_STATUS`/`PICK_BOLT` 를 보내고 WS 로 heartbeat/
arm_state 스트림을 그대로 출력한다 — 이 왕복이 곧 "통신 기능 검증"이다. 실제
파지 사이클(Gazebo+MoveIt+`integrated_pick_place` 까지 전부 기동)이 끝나면 WS
연결로 `RESULT` 가 도착한다. `--assert` 모드는 인증(401)·필수필드 검증·seq
락(REST 스레드↔rclpy 타이머 스레드 동시성) 등을 자동 확인한다(2026-08-04 실측
통과 — desktop_connection_guide.md §4 참고).

### 현재 단계에서 "진짜로" 동작하는 것 vs 골격만인 것

| 명령 | 이번 단계 | 다음 단계 |
|---|---|---|
| `GET_STATUS`(REST) | 완전 실동작 | — |
| `PICK_BOLT`(REST) | **완전 실동작** — 실제로 `/next_bolt_pose` 를 거쳐 파지 시도, `RESULT`(WS)도 실제 결과(`fail_reason`/`retry_suggested`/`retries`/`cycle_id`/`matched_bolt_id` 전부 부록D/F 대로 매핑, 2026-08-03), 필수필드 검증·deadline 시행도 실동작 | 부록D `REACH_FILTERED`/`COLLISION_ABORT`/`JOINT_LIMIT`/`TIMEOUT`(현재 로봇이 구분 안 하는 실패 종류) |
| `ESTOP`(REST) | ACK + 로컬 플래그(heartbeat.state 반영)만 | 실제 정지 연동(§5 deadman) |
| 나머지(`START`/`SET_SPEED`/`BLACKLIST_ADD`/..., `/api/v1/command`) | **ACK 골격만** — 프로토콜 형태 확인용, 로봇 동작 미반영 | 로봇측 연동 인터페이스(PROGRESS.md) |

이 구분을 정직하게 유지하는 이유: 이번 작업의 목표는 "통신 기능 자체 검증"이지
전체 명령의 로봇 동작 연동이 아니다(그건 별도 팀의 데스크톱앱 완성 이후, 로드맵상
다음 단계).

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

> **2026-08-03 갱신:** 이전 표는 "언젠가 이런 코드를 발행하겠다"는 기획이었는데,
> 실제 로봇 파이프라인(`pick_place_node.py`)이 발행하는 내부 실패 사유
> 문자열과 맞춰 보니 절반 가까이 실제로는 한 번도 발행되지 않았다. 아래
> 표는 **로봇이 지금 실제로 만들어내는 값 기준**으로 다시 썼다 —
> 매핑 구현은 `src/bin_picking/bin_picking/protocol.py`의
> `FAIL_REASON_MAP`/`map_fail_reason()`가 유일한 소스다.

| code | 예약 상태 | 발생 단계 | 의미 | 데스크톱 권고 행동 |
|---|---|---|---|---|
| `UNREACHABLE` | **발행됨**(내부 `axis_unreachable`) | 파지계획 | 볼트가 거의 수직 — 옆에서 감쌀 수 없음(영구 포기) | **다음 순위** |
| `APERTURE_BLOCKED` | **발행됨**(내부 `no_aperture_exhausted`/`no_aperture`) | 파지계획 | 벽·이웃으로 개구 확보 불가(전자는 영구 포기, 후자는 이번 무더기만 보류 — `retry_suggested`로 구분) | 후자만 재시도, 전자는 **다음 순위** |
| `PLAN_FAIL` | **발행됨**(내부 `orientation_fail`/`descend_fail`/`lift_fail`) | PLANNING | 파지 자세 생성 실패 / 하강·리프트 경로 계획 실패 | 다음 순위(자세생성 실패) 또는 재시도(하강·리프트) |
| `APPROACH_FAIL` | **발행됨** | APPROACHING | 접근 자세 달성률 게이트 미달 | 재시도 → 다음 |
| `DESCEND_SHORT` | **발행됨** | DESCENDING | 하강 달성률<0.995, 볼트 위에서 멈춤 | **재시도** |
| `ATTACH_FAIL` | **발행됨** | GRASPING | 씬 부착 실패 | 재시도 |
| `GRASP_MISS` | **발행됨**(내부 `empty_after_lift`) | LIFTING | 리프트 후 볼트 안 올라옴(빈손) — `grasp_result.bolt_rise_m`/`gripper_width_m`가 실측 근거 | 재시도 → N회 후 blacklist |
| `ABORTED` | **발행됨** | any | 하강 직전 볼트 위치가 허용치 이상 이동해 시도 취소(재계획하면 재시도 가능) | 재시도 |
| `UNKNOWN` | **확장 코드**(신규) | any | `protocol.FAIL_REASON_MAP`에 없는 내부 사유 — 매핑 누락을 정직하게 드러낸다(발생 시 로봇 로그에 경고 남음) | 보수적으로 다음 순위 |
| `REACH_FILTERED` | 예약 — 현재 미발행 | 사전필터 | 도달범위 밖 (‖y−통중심‖>0.063m 또는 x>0.45m) — 지금은 이 필터를 통과 못 한 볼트가 애초에 후보에 안 오른다 | **다음 순위** |
| `COLLISION_ABORT` | 예약 — 현재 미발행 | APPROACH/DESCEND | 충돌 예측/감지로 중단 | 다음 순위 |
| `JOINT_LIMIT` | 예약 — 현재 미발행 | any | 관절 한계 근접/초과(J7 등) | 다음 순위 |
| `TIMEOUT` | 예약 — 현재 미발행 | any | 동작 타임아웃(ACCEPT/RESULT) | 재시도 |

> `retry_suggested`(bool)와 `retries`(u8)를 함께 실어, 데스크톱이 "N회 넘으면
> blacklist" 정책을 스스로 적용할 수 있게 한다(로봇도 자체 `MAX_NO_PROGRESS`로
> 판단하지만, 데스크톱이 랭킹 주체이므로 정책 공유). **`retries`는 "이번 결과
> 직전까지의 연속 실패수"** — 영구 포기(블랙리스트) 경로(`UNREACHABLE`,
> `APERTURE_BLOCKED`/`retry_suggested:false`)는 애초에 연속실패 스트릭 집계를
> 거치지 않으므로 이 카운트가 다른 코드보다 낮게 보일 수 있다(의도된 차이).

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
| `deadline` | u64 | ns | ? | 이 시각 넘으면 stale로 폐기 — **시행됨**(2026-08-03): 초과 시 로봇에 아예 전달되지 않고 `ACK{accepted:false, errors:["stale: deadline exceeded"]}` + `alert{code:"STALE_COMMAND"}`로 거부된다 |

> **필수 필드 검증(2026-08-03 추가):** `bolt_id`/`rank`/`stamp`/`frame`/`pose.position`/`pose.orientation` 중 하나라도 누락·모양이 틀리면 로봇은 아예 시도하지 않고 `ACK{accepted:false, errors:["missing required field: ..."]}`로 응답한다(2단계 `RESULT` 없이 여기서 끝) — 데스크톱 개발 중 스키마 실수를 바로 알 수 있게 하기 위함.

### `arm_state.args` (로봇 → 데스크톱, 섀도우 연료, 10–30 Hz)
| 필드 | 타입 | 단위 | 필수 | 설명 |
|---|---|---|---|---|
| `q` | f32[7] | rad | ✔ | fr3_joint1..7 위치 |
| `tcp` | f32[3] | m | ✔ | fr3_hand_tcp xyz |
| `tcp_quat` | f32[4] | — | ? | TCP 자세 쿼터니언 |
| `gripper_width` | f32 | m | ✔ | 손가락 개구 폭 |
| `joint_margin` | f32[7] | rad | ? | 각 관절 한계까지 여유(2026-08-03: 구현 완료 — `protocol.joint_margins()`) |
| `moving` | bool | — | ✔ | 이동 중 여부 |
| `last_cycle_id` | u32 | — | ? | 가장 최근에 관측된 사이클 id(nullable, §2B 참고 — `cycle_id`가 아니다) |

> **유실 허용:** 한 프레임 빠져도 섀도우는 다음 프레임으로 복구된다(최신값 우선). 이벤트 메시지(grasp_result 등)와 달리 무손실 보장 불필요.
> **스톨 알림(2026-08-03 추가):** `/joint_states` 미수신 또는 TF 조회 실패가 3틱 연속되면 `alert{code:"NO_JOINT_STATE"|"TF_STALE"}`을 1회 발행한다 — 이전엔 완전히 무음이라 "로봇 유휴"와 "링크 고장"이 구분되지 않았다.

### `RESULT.args` (로봇 → 데스크톱, `PICK_BOLT` 등 2단계 응답의 2번째 단계)
| 필드 | 타입 | 단위 | 필수 | 설명 |
|---|---|---|---|---|
| `success` | bool | — | ✔ | 파지 성공 여부 |
| `fail_reason` | enum | — | ? | 부록D 코드, 성공 시 `null` |
| `retry_suggested` | bool | — | ? | 부록D 참고, 성공 시 `null` |
| `retries` | u8 | — | ✔ | 이번 결과 직전까지의 연속 실패수(부록D 참고) |
| `cycle_id` | u32 | — | ✔ | 이 결과를 만든 사이클의 id(로봇이 발급, 절대 브릿지가 추측 안 함) |
| `bolt_id` | str | — | ✔ | 데스크톱이 원래 `PICK_BOLT`에 실어 보낸 id 그대로 echo |
| `matched_bolt_id` | str | — | ? | 로봇이 내부적으로 재매칭한 id(데스크톱의 `bolt_id`와 다를 수 있음, nullable) |
| `dur_s` | f32 | s | ? | 이번 시도 소요시간 |

### `grasp_result.args` (로봇 → 데스크톱, 로봇 자체선택 사이클의 지상진실 — `origin:'ROBOT'`)
| 필드 | 타입 | 단위 | 필수 | 설명 |
|---|---|---|---|---|
| `bolt_id` | str | — | ? | 로봇이 자체 선택·매칭한 볼트 id(데스크톱 id 없음 — 이 사이클은 데스크톱이 지시한 게 아니므로) |
| `success` | bool | — | ✔ | 파지 성공 여부 |
| `fail_reason` | enum | — | ? | 부록D 코드, 성공 시 `null` |
| `bolt_rise_m` | f32 | m | ? | 리프트 후 볼트 상승량(센싱 가능할 때만 — 지상진실) |
| `gripper_width_m` | f32 | m | ? | 손끝 폭 실측(볼트 추적 불가 시 폴백 지표) |

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
