# 데스크톱 통신 프로토콜 정밀 감사 · v4 업그레이드 계획

> 작성: 2026-08-25  
> 대상: `desktop_protocol.md`의 v3 REST+WebSocket 계약, `desktop_bridge.py`,
> `protocol.py`, `tools/desktop_sdk/`, ROS 내부 명령 경로  
> 목적: Claude 또는 다른 작업자가 작업 ID별로 바로 구현할 수 있는 실행 백로그  
> 주의: 이 문서는 **목표 계약과 마이그레이션 계획**이다. 현재 와이어 계약의 단일
> 기준은 변경 전까지 `desktop_protocol.md`와 `protocol.py`다.
> PLC 없는 셀에서 이 계약의 명령을 실제 ROS 작업으로 조정하는 상세 설계는
> [`ros_supervisor_design.md`](./ros_supervisor_design.md)를 따른다.

---

## 1. 결론

현재 v3는 시뮬레이션 데모와 외부 앱 개발을 시작하기에는 실용적이다. 명령을 REST,
고주기 상태를 WebSocket으로 분리했고, correlation ID, sequence, wall/sim timestamp,
TLS 비-loopback 가드까지 갖췄다. 그러나 실물 로봇의 신뢰 가능한 원격 조작 계약으로
보기에는 다음 네 가지가 부족하다.

1. **명령 수명주기 보장 부재**: HTTP 수신, ROS 전달, 로봇 수락, 실행, 최종 결과가
   하나의 `accepted` 값에 섞여 있다.
2. **시간 도메인 결함**: 문서는 `deadline`을 `t_sim`으로 정의하지만 브릿지는 Unix
   벽시계와 비교한다. Gazebo 시각을 넣으면 정상 명령도 즉시 stale이 될 수 있다.
3. **중요 이벤트 유실 가능**: 20Hz `arm_state`, `RESULT`, `ALERT`가 같은 bounded
   queue를 쓰며 queue full이면 종류와 무관하게 버린다. 재접속 replay도 없다.
4. **운영 보안/제어권 부재**: WS URL에 장기 bearer token을 넣고, 한 토큰이 관측,
   로봇 조작, 모델 변경을 모두 허용하며, 여러 클라이언트 중 누가 조종권자인지 없다.

따라서 v3에 기능을 계속 덧대기보다 다음과 같이 나누는 것을 권장한다.

- **v3.0.x 안전 패치**: 이벤트 대소문자, SDK ready race, 입력 검증, 중요/샘플링
  큐 분리처럼 wire break 없이 가능한 수정.
- **v4 계약**: 비동기 command resource, idempotency, clock domain, robot ACK/action,
  replay 가능한 중요 이벤트, capability/role/lease를 명시하는 clean break.

---

## 2. 조사 기준과 공식 근거

다음 표준/공식 문서를 설계 기준으로 사용했다.

| 기준 | 이 프로젝트에 적용할 내용 |
|---|---|
| [RFC 9110 §15.3.3](https://www.rfc-editor.org/rfc/rfc9110.html#name-202-accepted) | 장시간 명령 접수는 `202 Accepted`; 응답은 현재 상태와 status monitor를 가리켜야 함 |
| [RFC 9457](https://www.rfc-editor.org/rfc/rfc9457.html) | REST 오류는 `application/problem+json`으로 일관되게 표현 |
| [RFC 6750 §2.3](https://www.rfc-editor.org/rfc/rfc6750.html#section-2.3), [RFC 9700](https://www.rfc-editor.org/rfc/rfc9700.html) | bearer token을 URI query에 싣지 않음; URL/로그/history 유출 방지 |
| [RFC 6455](https://www.rfc-editor.org/rfc/rfc6455.html) | browser Origin 검증, Ping/Pong 기반 연결 생존성 |
| [JSON Schema 2020-12](https://json-schema.org/draft/2020-12) | 런타임과 테스트가 공유할 메시지 스키마 |
| [OpenAPI 3.2.0](https://spec.openapis.org/oas/v3.2.0.html) | REST 계약의 기계 판독 가능한 단일 문서 |
| [AsyncAPI 3.1.0](https://www.asyncapi.com/docs/reference/specification/v3.1.0) | WebSocket 이벤트 계약과 correlation/security 문서화 |
| [ROS 2 Jazzy 인터페이스 가이드](https://docs.ros.org/en/jazzy/How-To-Guides/Topics-Services-Actions.html) | 장시간 pick은 feedback/result/cancel을 제공하는 Action으로 연결 |

`Idempotency-Key`는 좋은 설계 패턴이지만 2026-08-25 현재 IETF 문서는 아직
[Internet-Draft](https://datatracker.ietf.org/doc/draft-ietf-httpapi-idempotency-key-header/)다.
따라서 헤더 이름을 채택할 수는 있으나 “확정 RFC 준수”라고 표현하지 않고, 서버의
보존 기간·payload fingerprint·충돌 규칙을 이 프로젝트 계약에서 직접 정의해야 한다.

---

## 3. 현재 구현에서 확인한 장점

- `desktop_bridge.py`가 ROS 노드와 HTTP/WS 서버를 분리해 Gazebo 없이도 계약 시험이
  가능하다.
- 비-loopback 평문 바인딩은 기본 거부되며 TLS를 강제할 수 있다.
- bearer token 비교에 `hmac.compare_digest()`를 사용한다.
- REST 명령과 WS telemetry를 분리해 명령/스트림의 성격 차이를 드러냈다.
- `RESULT.corr`, `cycle_id`, `origin`, `matched_bolt_id`를 구분하려는 구조가 있다.
- envelope에 `seq`, `t_wall`, `t_sim`, `use_sim_time`이 있어 진단 기반은 갖췄다.
- 느린 WS 송신에 2초 제한이 있고 outbox가 bounded라 무제한 메모리 증가는 막는다.
- `protocol.py`가 ROS-free라 입력 검증과 실패 코드 매핑을 빠르게 단위 시험할 수 있다.

이 장점은 v4에서도 유지한다. 특히 REST+WS 조합 자체를 gRPC/MQTT로 교체할 이유는
현재 없다. 문제는 전송 기술이 아니라 명령 상태, 시간, 유실, 권한의 semantics다.

---

## 4. 확인된 결함과 위험도

| ID | 심각도 | 확인 내용 | 실제 영향 |
|---|---:|---|---|
| CP-C01 | P0 | `deadline(t_sim)`을 `time.time_ns()`와 비교 | 시뮬 명령이 즉시 stale 또는 잘못 허용 |
| CP-C02 | P0 | HTTP `accepted:true`가 ROS publisher 호출 직후 반환 | 로봇 미기동/미수락/유실도 성공처럼 보임 |
| CP-C03 | P0 | `RESULT`/`ALERT`와 `arm_state`가 같은 drop queue | 완료 결과·경고가 영구 유실될 수 있음 |
| CP-C04 | P0 | 재접속 시 STATUS만 있고 중요 이벤트 replay/status 조회 없음 | 실행됐지만 응답을 못 받은 명령의 상태를 복구 불가 |
| CP-C05 | P0 | PICK 요청의 ID/origin이 `PoseStamped`에서 소실 | 비전 pose와 desktop pose 동시 사용 시 오상관 가능 |
| CP-C06 | P1 | 브릿지는 `ALERT`, 문서/SDK는 `alert` | SDK의 typed alert listener가 경고를 못 받음 |
| CP-C07 | P1 | SDK `connect()`가 WS 준비 전 반환하고 POST 뒤 future 등록 | 빠른 결과 또는 연결 직후 결과를 놓칠 race |
| CP-C08 | P1 | WS 장기 token이 query string에 위치 | URL 로그, history, 진단 도구로 credential 유출 가능 |
| CP-C09 | P1 | 단일 static token, scope/expiry/rotation 없음 | 관측자도 모델 변경·로봇 조작 권한을 공유 |
| CP-C10 | P1 | 다중 WS/REST 클라이언트의 control owner 없음 | 두 앱/운영자의 상충 명령을 중재하지 못함 |
| CP-C11 | P1 | 전역 `seq`가 재시작 때 0으로 리셋되고 `boot_id` 없음 | restart와 reorder/loss를 구분하기 어려움 |
| CP-C12 | P1 | command별 strict schema가 없고 `axis`는 검증 없이 미사용 | 잘못된 타입/범위가 늦게 실패하거나 조용히 무시됨 |
| CP-C13 | P1 | slow client 송신을 한 `gather()`에서 기다림 | 한 클라이언트가 전체 broadcast를 최대 2초씩 지연 |
| CP-C14 | P1 | current `PICK_BOLT success`는 lift 성공, place 완료가 아님 | 앱이 drop 실패를 성공으로 표시할 수 있음 |
| CP-C15 | P2 | 문서 예시는 `v:1`, 본문은 v3; `q[7]`, `fr3_link0` 고정 | 다중 로봇 프로파일과 계약 문서가 충돌 |
| CP-C16 | P2 | SDK model이 누락 필드를 default로 삼고 version을 거부하지 않음 | schema drift가 즉시 실패하지 않고 오동작으로 전파 |
| CP-C17 | P2 | 명시적 body limit/rate limit/Origin allowlist/audit 정책 없음 | 오용·브라우저 cross-origin·운영 추적에 취약 |
| CP-C18 | P2 | server thread readiness/health endpoint가 없음 | ROS spin은 살아 있으나 API가 죽은 반쪽 상태 판단이 어려움 |

### 4.1 CP-C01 재현 논리

`desktop_protocol.md`는 `PICK_BOLT.args.stamp/deadline`을 시뮬레이션 ns로 정의한다.
`desktop_bridge.py::_pick_bolt_core()`는 `protocol.build_pick_bolt_pose(...,
time.time_ns())`를 호출하고 `protocol.is_stale()`은 단순히
`now_ns > deadline_ns`를 계산한다.

Gazebo `/clock`이 예를 들어 120초라면 `deadline=125_000_000_000`인 정상 명령과
Unix epoch 벽시계 약 `1.7e18 ns`를 비교하게 된다. 결과는 항상 stale이다. 반대로
두 시계를 혼용한 임의 값은 실제 pose age를 보장하지 못한다.

### 4.2 CP-C02/C05의 내부 전송 문제

현재 `desktop_bridge`는 `std_msgs/String` 토픽과 `PoseStamped` 토픽에 publish한 직후
HTTP ACK를 반환한다. 기본 ROS topic은 장시간 작업의 goal acceptance, feedback,
cancel, result 모델이 아니다. `PoseStamped`에는 `command_id`, `bolt_id`, `origin`도
없어 correlation이 로봇 노드까지 이어지지 않는다.

Pick은 ROS 2 Action으로 바꾸고, goal에 correlation과 pose를 함께 넣는 것이 맞다.
짧은 설정 명령은 Service, 연속 상태는 Topic으로 유지한다.

### 4.3 CP-C03/C04의 유실 문제

outbox는 `maxsize=500` 하나뿐이다. queue full이면 메시지 JSON을 해석하거나 우선순위를
보지 않고 버린다. `arm_state`는 다음 프레임으로 대체 가능하지만 `RESULT`는 그렇지
않다. WS가 끊긴 동안에는 STATUS snapshot 외에 replay도 없다.

전송 재시도만 추가해서는 해결되지 않는다. side-effect가 있는 POST가 이미 실행됐는지
모른 채 재전송하면 중복 pick이 된다. **명령 idempotency + 조회 가능한 command
resource + 중요 이벤트 replay**를 함께 도입해야 한다.

---

## 5. v4 목표 구조

```text
Desktop operator
  │
  ├─ POST /api/v2/commands  ── Idempotency-Key + operator lease
  │       │
  │       └─ 202 + Location: /api/v2/commands/{command_id}
  │                         │
  │                         └─ ROS 2 PickBolt Action
  │                              goal accepted/rejected
  │                              feedback(stage/progress)
  │                              cancel/result
  │
  ├─ GET /api/v2/commands/{id} ── 재연결 후 authoritative 상태 복구
  │
  └─ WSS /ws/v2/events
          ├─ sampled: arm_state (latest-value, 유실 허용)
          └─ critical: command_state/result/alert (ring buffer + replay)
```

### 5.1 명령 상태기계

```text
RECEIVED
  ├─ REJECTED          schema/auth/lease/state gate 실패
  └─ QUEUED
       ├─ EXPIRED      dispatch 전 TTL 초과
       ├─ REJECTED     robot action server가 goal 거부
       └─ EXECUTING
            ├─ CANCEL_REQUESTED ── CANCELED | CANCEL_FAILED
            ├─ SUCCEEDED
            └─ FAILED
```

규칙:

- HTTP `202`는 **API가 command resource를 만들고 처리를 예약했다**는 뜻뿐이다.
- `robot_accepted_at`이 기록되기 전에는 UI가 “로봇 수락”으로 표시하면 안 된다.
- `SUCCEEDED`는 place/detach까지 끝난 전체 cycle 성공이다.
- lift 성공은 별도 stage event `GRASP_VERIFIED`로 보낸다.
- 모든 terminal state는 `GET /commands/{id}`에서 재조회 가능해야 한다.
- cancel 요청도 command state에 기록하고 결과가 관측돼야 한다.

### 5.2 명령 생성 요청 예시

```http
POST /api/v2/commands HTTP/1.1
Authorization: Bearer <operate-token>
Idempotency-Key: "3d47e151-4c61-45f9-923e-28a0fd62c7b5"
Content-Type: application/json

{
  "type": "pick_bolt",
  "client_command_id": "3d47e151-4c61-45f9-923e-28a0fd62c7b5",
  "lease_id": "lease-7cfa",
  "ttl_ms": 1500,
  "args": {
    "bolt_id": "b-88",
    "rank": 1,
    "pose": {
      "frame": "fr3_link0",
      "position_m": [0.31, -0.04, 0.028],
      "orientation_xyzw": [0.0, 0.0, 0.7071, 0.7071],
      "observed_at": {"clock": "ros_sim", "ns": 120340000000}
    },
    "axis": [0.99, 0.01, 0.03]
  }
}
```

```http
HTTP/1.1 202 Accepted
Location: /api/v2/commands/01K3...
Content-Type: application/json

{
  "command_id": "01K3...",
  "client_command_id": "3d47e151-4c61-45f9-923e-28a0fd62c7b5",
  "state": "QUEUED",
  "status_url": "/api/v2/commands/01K3..."
}
```

### 5.3 idempotency 규칙

- 모든 side-effect POST에 `Idempotency-Key`를 요구한다.
- key scope는 `(principal_id, endpoint)`다.
- 서버는 최소 **24시간** key, canonical payload hash, command ID, 최종 응답을 보존한다.
- 같은 key + 같은 payload 재요청은 기존 command/status를 반환한다.
- 같은 key + 다른 payload는 `409 Conflict` problem detail로 거부한다.
- 최초 요청이 진행 중일 때의 중복도 새 pick을 만들지 않고 기존 command를 반환한다.
- SDK는 네트워크 timeout 후 같은 key로만 재시도한다. 새 key 자동 생성 재시도는 금지한다.

### 5.4 시간 계약

하나의 `deadline` 필드로 source freshness와 transport timeout을 표현하지 않는다.

| 목적 | 필드 | 시계 | 판정 주체 |
|---|---|---|---|
| 네트워크/queue 체류 제한 | `ttl_ms` | 서버 수신 시점의 monotonic clock | bridge |
| pose 관측 시각 | `pose.observed_at{clock,ns}` | `ros_sim`, `ros_system`, `unix` 중 명시 | 같은 clock을 가진 robot/bridge |
| 로그/감사 | `received_at` 등 | RFC 3339 UTC + ns 또는 Unix ns | bridge |
| WS 생존성 | Ping/Pong timeout | event loop monotonic clock | client/server |

규칙:

- 서로 다른 `clock` 값은 절대 뺄셈하지 않는다.
- simulation의 pose age는 bridge의 ROS clock과 `ros_sim`끼리 비교한다.
- 비교할 수 없는 clock이면 stale 여부를 추측하지 않고 `CLOCK_DOMAIN_MISMATCH`로 거부한다.
- `ttl_ms`는 1~10,000ms처럼 명시적 범위를 두고 서버 receipt부터 계산한다.
- ROS sim clock pause가 WS liveness와 인증 만료 타이머를 멈추게 해서는 안 된다.

### 5.5 REST 상태 코드와 오류

| 상황 | HTTP | 의미 |
|---|---:|---|
| command resource 생성 | 202 | 아직 robot acceptance/완료 아님 |
| 현재 command 조회 | 200 | authoritative snapshot |
| JSON/schema 오류 | 400/422 | syntax 또는 field validation 실패 |
| 인증 없음/실패 | 401 | `WWW-Authenticate: Bearer` 포함 |
| scope 부족 | 403 | 인증됐지만 권한 없음 |
| lease/idempotency payload 충돌 | 409 | 현재 상태와 요청이 충돌 |
| active operator lease 필요 | 423 | 제어권 잠김 |
| rate limit | 429 | `Retry-After` 포함 |
| action server/readiness 실패 | 503 | 현재 로봇에 안전하게 전달 불가 |

오류 body는 RFC 9457 `application/problem+json`으로 통일한다.

```json
{
  "type": "https://robot.local/problems/clock-domain-mismatch",
  "title": "Pose clock cannot be compared",
  "status": 422,
  "detail": "observed_at.clock=ros_sim, bridge.clock=ros_system",
  "instance": "/problems/01K3...",
  "code": "CLOCK_DOMAIN_MISMATCH",
  "invalid_params": [{"name": "args.pose.observed_at.clock", "reason": "mismatch"}]
}
```

### 5.6 이벤트 envelope

```json
{
  "protocol": {"major": 4, "minor": 0},
  "stream_id": "boot-f7c2...",
  "event_id": "01K3...",
  "seq": 1842,
  "type": "command.state_changed",
  "occurred_at": {"wall_ns": 1787, "ros_ns": 120340000000, "ros_clock": "sim"},
  "command_id": "01K3...",
  "cycle_id": 412,
  "trace_id": "tr-...",
  "data": {"from": "QUEUED", "to": "EXECUTING", "stage": "APPROACH"}
}
```

명명 규칙:

- event type은 전부 lowercase dot notation을 사용한다.
- `command_id`: 외부 명령의 수명주기.
- `cycle_id`: 실제 pick/place cycle.
- `trace_id`: REST→bridge→ROS action→result를 묶는 진단 ID.
- `stream_id`: bridge process boot/session. `seq`는 이 ID 안에서만 단조 증가한다.
- `event_id`: replay/dedup용 영구 이벤트 ID.

### 5.7 delivery class와 backpressure

| class | 예 | 정책 |
|---|---|---|
| sampled | `robot.arm_state` | 클라이언트별 latest-value 1개, 오래된 프레임 coalesce |
| snapshot | `robot.status` | 접속/요청 시 현재값, 과거 replay 불필요 |
| critical | `command.*`, `cycle.result`, `alert` | bounded ring buffer + command store, 유실 시 조회/replay 가능 |

- client마다 독립 송신 queue/task를 둔다. 느린 client가 다른 client를 막지 않는다.
- `arm_state` queue는 최신값으로 덮어쓰되 critical queue는 절대 조용히 drop하지 않는다.
- critical buffer가 한계에 도달하면 health를 degraded로 만들고 metric/로그를 남긴다.
- WS 연결 요청의 `last_event_id` 또는 `stream_id + last_seq`로 가능한 범위를 replay한다.
- replay 범위를 벗어나면 `replay.reset_required` 후 command/status snapshot을 다시 받는다.

### 5.8 version/capability discovery

`GET /api/v2/meta`는 최소 다음을 반환한다.

```json
{
  "api_version": "2.0",
  "event_protocol": "4.0",
  "boot_id": "boot-f7c2...",
  "schema_hash": "sha256:...",
  "robot": {
    "model": "fr3",
    "reference_frame": "fr3_link0",
    "joint_names": ["fr3_joint1"],
    "dof": 7
  },
  "capabilities": {
    "commands": ["pick_bolt", "soft_stop", "go_home"],
    "cancel": true,
    "event_replay": true,
    "max_arm_state_hz": 20
  }
}
```

SDK는 major 불일치를 즉시 거부하고 minor는 capability를 확인해 기능을 켠다. 관절 수,
관절 이름, reference frame을 더 이상 FR3 값으로 하드코딩하지 않는다.

### 5.9 인증, 권한, 제어 lease

- non-loopback은 HTTPS/WSS를 필수로 유지한다.
- native client는 WS handshake에도 `Authorization: Bearer`를 사용한다.
- custom header를 못 넣는 browser client는 인증된 REST로 **수십 초 수명의 single-use
  WS ticket**을 발급받는다. 장기 bearer token을 query에 넣지 않는다.
- token에는 expiry, audience, scope를 둔다: `observe`, `operate`, `admin`.
- 모델 전환/설정 저장은 `admin`, pick/stop은 `operate`, telemetry는 `observe`다.
- 자동운전 command에는 active operator `lease_id`가 필요하다. lease는 heartbeat와
  만료시간을 가지며 한 시점에 한 principal만 소유한다.
- 관측자는 여러 명 허용하고 조작자는 한 명만 허용한다.
- safety-rated E-STOP은 이 API 밖의 하드웨어 회로다. API의 현재 ESTOP은
  `soft_stop`으로 이름과 UI 의미를 낮춘다.
- access/audit log에는 token, WS ticket, 전체 pose cloud를 기록하지 않는다.
- 허용 browser Origin을 설정값으로 명시하고 나머지는 handshake에서 거부한다.

### 5.10 기계 판독 계약

권장 산출물:

```text
docs/protocol/
  openapi.yaml                 # REST — OpenAPI 3.2.0
  asyncapi.yaml                # WS events — AsyncAPI 3.1.0
  schemas/
    command-create.schema.json # JSON Schema 2020-12
    event-envelope.schema.json
    pick-bolt.schema.json
    problem.schema.json
```

모든 파일이 같은 JSON Schema component를 `$ref`한다. prose 표를 수기로 세 벌 유지하지
않는다. Python bridge validator, SDK model/codegen, fixture test가 같은 schema artifact를
소비한다. 도구 호환성 때문에 OpenAPI 3.2.0을 못 쓰는 경우에만 3.1.2를 택하고 그 이유를
문서에 남긴다.

---

## 6. Claude용 구현 백로그

### CP-H01 — v3 alert/SDK ready hotfix

**변경**

- 브릿지 event type을 문서대로 `alert`로 통일.
- SDK는 한 릴리스 동안 `ALERT`도 읽고 deprecation warning.
- `connect()`는 WS 연결 + 최초 STATUS 수신까지 기다리거나 timeout.
- `pick_bolt()`는 ready 이전 호출을 대기/명시 거부.
- future/result race를 없애기 위해 v3에서는 POST 직전에 client request ID를 만들 수
  없으므로 최소한 WS ready를 강제하고, v4에서 server-side command 조회로 완전히 해결.

**수용 기준**

- 실제 브릿지 형태의 `ALERT`/`alert` fixture가 typed callback에 도착.
- WS가 열리지 않은 상태에서 `connect()`가 성공 반환하지 않음.
- 인증 실패가 background task exception으로 묻히지 않고 호출자에게 전달.

### CP-H02 — v3 입력 검증 강화

**변경**

- `bolt_id`: non-empty, 길이 제한.
- `rank`: 정수, bool 제외, `>=1`.
- `stamp/deadline`: bool 제외 정수, `>=0`.
- `frame`: 허용값/길이.
- `axis`: 있으면 finite `f64[3]`, norm 범위 검증. 계속 미사용이면 필드 제거 또는
  `ignored_fields` 응답으로 드러냄.
- command별 args schema와 `RESET.confirm is true`, speed 범위 검증.
- `Content-Type`, 명시적 request body size, JSON의 NaN/Infinity 거부.

**수용 기준**

- property/fuzz test에서 invalid JSON number/type이 ROS message까지 도달하지 않음.
- 알려지지 않은 command field 정책(`reject` 또는 versioned extension)이 문서와 일치.

### CP-P01 — clock domain 수정

**변경**

- v3의 ambiguous `deadline` 사용 중단 공지.
- v4 `ttl_ms` + `observed_at{clock,ns}` 도입.
- bridge receipt monotonic time, ROS clock, Unix time를 별도 변수/타입으로 유지.

**수용 기준**

- sim time 120s, wall time epoch 환경에서 정상 TTL 명령 수락.
- 실제 stale pose, TTL 만료, clock mismatch가 서로 다른 코드로 거부.
- sim clock pause 중에도 WS ping/auth/lease timeout은 벽시계로 동작.

### CP-P02 — ROS PickBolt Action과 correlation 보존

**변경**

- custom `PickBolt.action`에 `command_id`, `bolt_id`, pose, axis, source timestamp 추가.
- bridge는 action server readiness를 확인하고 goal accepted/rejected를 command state로 기록.
- feedback에 stage, progress, retry를 제공하고 cancel을 연결.
- `/next_bolt_pose`는 비전 추천 pose 스트림으로만 남기고 desktop command 경로와 분리.
- Supervisor/Executor 분리와 Action 상세, 상태 전이·취소 정책은
  `ros_supervisor_design.md`의 SUP-02~SUP-06을 따른다.

**수용 기준**

- robot node 미기동 시 HTTP가 최종 수락처럼 보이지 않고 command가 명시 실패.
- vision publisher와 desktop command 동시 실행 100회에서 correlation 오상관 0.
- 실행 중 cancel 결과가 command resource와 WS 모두에서 관측됨.

### CP-P03 — command store와 idempotency

**변경**

- `POST/GET /api/v2/commands` 및 상태기계 구현.
- SQLite 또는 atomic local store로 진행/terminal 상태와 idempotency record 보존.
- restart recovery 정책을 정의: 실행 중이던 명령은 무조건 재실행하지 말고
  `UNKNOWN_AFTER_RESTART`/수동 확인 상태로 둔다.

**수용 기준**

- 동일 key/payload 100회 retry에도 robot goal은 정확히 1개.
- 같은 key/다른 payload는 409.
- WS 단절 후 GET으로 최종 결과 복구.
- bridge restart 후 완료 command 조회 가능.

### CP-P04 — delivery class와 replay

**변경**

- sampled/snapshot/critical lane 분리.
- client별 sender queue와 slow-client 격리.
- `boot_id`, `stream_id`, `event_id`, replay cursor 도입.

**수용 기준**

- arm_state flood/느린 client 상황에서도 critical RESULT 0건 유실.
- client A를 2초 지연시켜도 client B의 critical p99 지연이 정한 한계 이내.
- replay window 내 disconnect/reconnect에서 event 순서/중복 처리 검증.

### CP-P05 — auth scope와 operator lease

**변경**

- query bearer 제거, Authorization header 또는 short-lived one-time WS ticket.
- `observe/operate/admin` scope enforcement.
- acquire/renew/release operator lease API와 만료 정책.
- Origin allowlist, rate limit, redacted audit log.

**수용 기준**

- access log/exception/SDK logger에 bearer가 나타나지 않음.
- observe token의 pick/model switch는 403.
- 두 operator의 동시 명령 중 lease owner만 실행.
- lease 만료 시 새 동작 진입 차단; 진행 중 동작 처리 정책은 명시적으로 시험.

### CP-P06 — OpenAPI/AsyncAPI/JSON Schema 단일 소스

**변경**

- §5.10 산출물 추가.
- CI에서 schema lint, example validation, implementation contract test 실행.
- SDK dataclass의 permissive default 대신 strict parse + version/capability gate.

**수용 기준**

- 문서의 모든 JSON example이 schema validation 통과.
- bridge가 내보낸 fixture를 SDK가 strict parse.
- 필수 필드 누락/major mismatch는 즉시 typed error.
- OpenAPI/AsyncAPI에서 생성한 client fixture가 mock server와 왕복.

### CP-P07 — health/readiness/observability

**변경**

- `/health/live`: process/event loop 생존만.
- `/health/ready`: ROS action server, joint state freshness, TF, model/profile 상태 포함.
- command/event drop, queue depth, WS lag, action acceptance latency metric.
- 모든 로그에 command/cycle/trace ID를 선택적으로 포함.

**수용 기준**

- API thread 실패, ROS action server 미기동, TF stale을 서로 다른 readiness reason으로 표시.
- 중요 queue 포화는 silent drop 없이 degraded/metric/alert로 관측.

### CP-P08 — multi-robot payload 일반화

**변경**

- `q[7]`, `joint_margin[7]`, `fr3_link0` 고정 계약 제거.
- meta의 joint names/order/dof/profile revision을 telemetry와 연결.
- model switch는 admin command로 기록하고 restart-required state를 명시.

**수용 기준**

- 동일 SDK가 FR3 7축과 UR5e 6축 fixture를 하드코딩 없이 파싱.
- schema가 joint array 길이와 meta dof 불일치를 잡음.

---

## 7. 권장 구현 순서와 선행조건

| 순서 | 작업 | 선행 | 비고 |
|---:|---|---|---|
| 1 | CP-H01 | 없음 | 즉시 사용자 가시 결함 |
| 2 | CP-H02 | 없음 | v3 방어 강화 |
| 3 | CP-P01 | 없음 | v4 시간 모델 확정 |
| 4 | CP-P06 schema 초안 | P01 | 구현 전 계약 고정 |
| 5 | CP-P02 | schema 초안 | robot ACK/correlation 기반 |
| 6 | CP-P03 | P02 | command authoritative store |
| 7 | CP-P04 | P03 | replay가 command store를 참조 |
| 8 | CP-P05 | P03 | principal/lease를 command에 연결 |
| 9 | CP-P07 | P02~P05 | 전체 상태 관측 |
| 10 | CP-P08 | P06 | 프로파일 기반 일반화 |
| 11 | v3→v4 SDK migration | 전부 | dual-stack 종료 |

`docs/bin_picking_analysis_and_upgrade_plan.md`의 기존 작업과 연결:

- BP-C01 ↔ CP-H01
- BP-C03 ↔ CP-P02
- BP-C04 ↔ CP-P02/CP-P03/CP-P05
- BP-C05 ↔ v4 command terminal semantics
- BP-C06 ↔ CP-H01/CP-P03/CP-P04

---

## 8. v3→v4 마이그레이션 정책

1. v3.0.x에서 deprecation header/log와 `/api/v2/meta` capability preview를 추가한다.
2. bridge가 제한 기간 v1 REST path + v2 REST path를 동시에 제공한다.
3. v3 WS는 `alert` casing hotfix만 하고 신규 기능은 v4 event stream에만 추가한다.
4. SDK는 `protocol='auto'`에서 meta를 조회해 v4를 우선 사용한다.
5. v3 PICK_BOLT는 자동 retry 금지를 유지한다. v4 idempotency가 확인된 경우에만 재시도한다.
6. v3 query token은 loopback에서만 임시 허용하고 non-loopback에서는 명시적으로 거부한다.
7. 실제 desktop app이 v4 contract test를 통과한 뒤 v3 제거 날짜를 정한다.

호환성을 위해 v4 semantics를 v3 `accepted` 필드에 억지로 넣지 않는다. 특히
`accepted=true`의 의미를 조용히 “HTTP 수신”에서 “robot goal accepted”로 바꾸면 기존
클라이언트가 잘못 해석한다.

---

## 9. 검증 매트릭스

### 9.1 단위/계약

- JSON Schema valid/invalid fixture.
- 모든 command type의 field boundary와 unknown-field 정책.
- NaN/Infinity/bool-as-int/oversized body/invalid UTF-8.
- state transition table에서 허용되지 않은 역전이 거부됨.
- idempotency payload canonicalization/fingerprint.
- wall/sim/monotonic clock 교차 비교 금지.

### 9.2 통합

- REST 202 → ROS goal acceptance → feedback → terminal result → GET/WS 일치.
- robot action server 없음/늦은 discovery/restart/cancel race.
- WS disconnect 전후 replay, bridge restart 후 command 조회.
- 20Hz telemetry + 10 slow clients + critical event burst.
- 비전 pose와 desktop pick 동시 발행 correlation.
- FR3/UR5e meta와 arm state schema.

### 9.3 보안/운영

- no token in URL/log/history fixture.
- scope matrix와 expired/revoked token.
- Origin allowlist.
- lease acquire/renew/expiry/takeover conflict.
- rate limit과 `Retry-After`.
- readiness가 ROS/TF/API 부분 장애를 구분.

### 9.4 최소 실행 명령

```bash
cd src/bin_picking
python3 -m pytest test/

# 추가할 계약 검증 예시 — 실제 도구 선정 후 package/CI에 고정
python3 -m pytest test/test_protocol_v4.py test/test_desktop_sdk.py
```

Gazebo 통합 시험은 `bash -c` 또는 `.zsh` setup을 사용하고, 최소 다음 시나리오를 자동화한다.

1. 정상 pick/place 완료.
2. drop 실패.
3. 실행 중 cancel.
4. WS 단절 중 완료 후 재접속 조회.
5. 같은 idempotency key 재전송.
6. sim clock pause/resume.

---

## 10. 구현 전에 확정할 결정 6개

Claude가 임의로 정하지 말고 프로젝트 소유자가 승인해야 하는 정책이다.

1. command store 보존 기간과 SQLite 사용 허용 여부.
2. operator lease 만료가 진행 중 trajectory를 cancel할지, 새 동작만 막을지.
3. browser 기반 desktop인지 native client인지. WS 인증 방식에 직접 영향.
4. one-time WS ticket 발급/검증을 bridge 자체가 할지 상위 인증 서비스에 맡길지.
5. v3 동시 운영 기간과 제거 조건.
6. `SUCCEEDED`의 정의를 place 완료로 확정할지, pick-only command를 별도로 둘지.

그 외 사항은 이 문서의 기본값으로 구현해도 된다.

---

## 11. 완료 정의

통신 프로토콜 업그레이드는 단순히 새 JSON 필드를 보내는 것으로 끝나지 않는다. 다음을
모두 만족해야 완료다.

- 네트워크 timeout/retry가 중복 pick을 만들지 않는다.
- HTTP 접수와 robot 수락/실행/완료가 UI와 API에서 구분된다.
- simulation clock과 wall clock을 혼용하지 않는다.
- RESULT/alert는 느린 client, queue pressure, 짧은 재접속에서도 복구 가능하다.
- command ID가 REST에서 ROS action과 최종 result까지 보존된다.
- observer/operator/admin 권한과 한 명의 active control owner가 강제된다.
- FR3/UR5e를 같은 SDK가 capability 기반으로 처리한다.
- OpenAPI, AsyncAPI, JSON Schema, bridge, SDK, prose 문서가 CI에서 동기화된다.
- API soft stop과 실물 하드웨어 E-STOP/STO의 경계가 UI와 문서에서 명확하다.
