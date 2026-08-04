# 데스크톱앱 연결 가이드 (실전)

> `desktop_protocol.md`가 "무엇을 주고받는가"(데이터 계약)라면, 이 문서는
> **"어떻게 접속해서 그걸 실제로 주고받는가"**다. 데스크톱팀이 로봇쪽 통신
> 종단점(`desktop_bridge` 노드)에 처음 붙을 때 이 문서 하나로 끝나는 게 목표.
>
> **v3(2026-08-04) 업데이트: 명령은 REST API로, 텔레메트리는 WebSocket 스트림
> 전용으로 분리하고 Bearer 토큰 인증을 추가했다.** v2까지는 명령도 텔레메트리와
> 같은 WebSocket 연결로 받았다 — 왜 바꿨는지는 [`desktop_protocol.md`](./desktop_protocol.md)
> §4 참고. 이 문서에 적힌 접속 방법·명령은 전부 실제로 돌려본 것만 적었다.

---

## 0. 한눈에 요약

| 항목 | 값 |
|---|---|
| 명령 | REST API — `http(s)://<로봇IP>:8765/api/v1/...` |
| 텔레메트리 | WebSocket 스트림(순수 서버→클라이언트) — `ws(s)://<로봇IP>:8765/ws/telemetry` |
| 인증 | **Bearer 토큰 필수**. REST는 `Authorization: Bearer <token>` 헤더, WS는 `?token=<token>` 쿼리스트링 |
| 암호화(TLS) | 선택 — 인증서를 주면 HTTPS/WSS, 안 주면 평문(§5 캐비엇) |
| 실행 노드 | `ros2 run bin_picking desktop_bridge` (독립 프로세스, Gazebo/MoveIt 불필요) |
| 데이터 계약 전체 | [`desktop_protocol.md`](./desktop_protocol.md) — 메시지 카탈로그·필드 스펙·enum |
| 참고 구현(목 클라이언트) | `src/bin_picking/tools/mock_desktop_client.py` (ROS 무의존, REST는 표준 `urllib`만 사용) |
| 지금 실동작하는 명령 | `GET_STATUS`, `PICK_BOLT`(완전 실동작), `ESTOP`(소프트 플래그만) |
| 나머지 명령 | ACK 골격만(로봇 동작 미반영, 의도된 범위 — §3) |

---

## 1. 로봇 쪽 실행 방법

두 가지 모드가 있다. **데스크톱 개발 초기엔 A로 시작하는 걸 권장** — Gazebo가 없어도
프로토콜 왕복 전체(GET_STATUS/PICK_BOLT의 ACK/heartbeat/STATUS)를 검증할 수 있다.

### A) 통신 프로토콜만 (가장 가벼움 — Gazebo/MoveIt 불필요)
```bash
source /opt/ros/jazzy/setup.bash   # zsh면 setup.zsh (echo $SHELL로 확인)
source install/setup.bash          # zsh면 setup.zsh
ros2 run bin_picking desktop_bridge --ros-args -p api_token:=<원하는-토큰>
```
> zsh에서 `.bash`를 그대로 source하면 `setup.bash:.:11: ... setup.sh 없음` 에러가 난다
> (`$BASH_SOURCE`로 자기 위치를 찾는데 zsh엔 없어서 `$PWD` 기준으로 잘못 찾음) — `.zsh`
> 확장자 버전을 쓰면 해결된다.

`api_token`을 안 주면 임의 토큰을 생성해 **시작 로그에 크게 출력**한다(그 값을
그대로 쓰면 됨). `/joint_states`가 없으므로 `arm_state`만 안 나가고, 나머지
(GET_STATUS/PICK_BOLT의 ACK/heartbeat)는 정상 동작한다. `PICK_BOLT`를 보내면
`/next_bolt_pose`로 재발행까지는 되지만, 받아서 실제로 움직일
`integrated_pick_place`가 없으니 `RESULT`는 오지 않는다.

### B) 풀스택 데모 (실제 파지까지 — 한 줄 기동)
```bash
ros2 launch bin_picking desktop_integration_demo.launch.py
```
Gazebo+MoveIt → 볼트 스폰 → `desktop_bridge` → `integrated_pick_place` 를 순서대로
띄운다(느린 컴퓨터면 `bolts_delay:=25.0 apps_delay:=30.0` 등으로 지연 늘리기).
이 모드에서 `PICK_BOLT`를 보내면 실제로 로봇이 움직이고 `RESULT`가 온다.
비전(카메라→포인트클라우드)은 의도적으로 빠져 있다 — 데스크톱 앱이 직접 카메라
파이프라인과 통신하는 별개 경로라서다(§3 범위 참고).

### 사전 준비 (로봇 쪽, 최초 1회)
```bash
pip install --user --break-system-packages aiohttp   # 검증된 버전: 3.14.3
```

---

## 2. 접속 주소 — 어디서 접속하느냐에 따라 다르다

로봇 스택은 **현재 WSL2(Windows) 위에서 돈다**. 아래는 이 환경에서 실측 확인한 내용이다.

### 데스크톱앱이 로봇과 같은 Windows 컴퓨터에서 돌 때 (가장 흔한 경우)
```
REST:      http://localhost:8765/api/v1/...
텔레메트리: ws://localhost:8765/ws/telemetry?token=<토큰>
```
**별도 설정 불필요.** WSL2가 Windows `localhost`를 게스트로 자동 포워딩해준다 —
이 문서의 모든 검증도 이 경로로 했다.

### 데스크톱앱이 같은 LAN의 다른 물리 머신에서 돌 때
WSL2 내부 IP(예: `hostname -I`로 확인되는 `172.19.x.x` 대역)는 **외부에서 직접
안 보인다** — 이 IP는 WSL2 재부팅마다 바뀌므로 하드코딩하지 말 것. 대신 Windows
호스트에서 포트포워딩을 걸고 **Windows 호스트의 IP**로 접속해야 한다:
```powershell
netsh interface portproxy add v4tov4 listenport=8765 listenaddress=0.0.0.0 connectport=8765 connectaddress=<WSL2_IP>
netsh advfirewall firewall add rule name="bin_picking desktop_bridge" dir=in action=allow protocol=TCP localport=8765
```
그다음 `http://<Windows-호스트-IP>:8765`(REST), `ws://<Windows-호스트-IP>:8765/ws/telemetry`로 접속.
**신뢰된 사설망 밖(인터넷)에는 노출하지 말 것** — TLS를 켰더라도 인증은 토큰
하나뿐이라 인터넷향 배포 수준의 보안은 아니다(§5).

### 호스트/포트 바꾸기
```bash
# standalone
ros2 run bin_picking desktop_bridge --ros-args -p host:=0.0.0.0 -p port:=9000 -p api_token:=<토큰>
# 풀스택 데모
ros2 launch bin_picking desktop_integration_demo.launch.py bridge_host:=0.0.0.0 bridge_port:=9000
```

### 인증 토큰
```bash
# 고정 토큰으로 기동(데스크톱팀과 공유할 값)
ros2 run bin_picking desktop_bridge --ros-args -p api_token:=my-shared-secret

# 안 주면 임의 생성 후 로그에 출력됨:
#   [desktop_bridge] api_token 파라미터가 없어 임의 토큰을 생성했습니다.
#     API_TOKEN = <생성된 값>
```
REST는 `Authorization: Bearer <token>` 헤더, WS는 `?token=<token>` 쿼리스트링으로
보낸다. 틀리거나 없으면 REST는 401, WS는 핸드셰이크 자체가 거부된다(연결 후 별도
인증 절차 없음 — 핸드셰이크 통과 = 인증 완료).

### TLS(선택 — 자체서명 인증서로 로컬/LAN 테스트)
```bash
# 인증서 생성 (최초 1회, 365일 유효)
openssl req -x509 -newkey rsa:2048 -nodes -keyout key.pem -out cert.pem -days 365 -subj "/CN=robotarm"

# 브릿지를 HTTPS/WSS로 기동
ros2 run bin_picking desktop_bridge --ros-args -p api_token:=<토큰> -p tls_cert:=$PWD/cert.pem -p tls_key:=$PWD/key.pem
```
이후 `https://.../api/v1/...`, `wss://.../ws/telemetry` 로 접속. 자체서명
인증서라 대부분의 HTTP 클라이언트가 기본적으로 거부한다 — 개발 중엔 클라이언트
쪽 "인증서 검증 무시" 옵션을 쓰거나(curl `-k`), 실배포 전엔 정식 인증서로 교체할 것.

---

## 3. 지금 "진짜로" 되는 것 vs 골격만인 것

| 명령 | 경로 | 상태 | 비고 |
|---|---|---|---|
| `GET_STATUS` | `GET /api/v1/status` | ✅ 완전 실동작 | |
| `PICK_BOLT` | `POST /api/v1/pick_bolt` | ✅ **완전 실동작** | 응답은 `{id, accepted, errors?}`(HTTP 200). `/next_bolt_pose`로 재발행 → 실제 파지 시도 → `RESULT`(WS, `corr`=응답의 `id`)에 `fail_reason`/`retry_suggested`/`retries`/`cycle_id`/`matched_bolt_id` 전부 실제 값. 필수필드 검증·deadline 시행도 동작 |
| `ESTOP` | `POST /api/v1/estop` | 🔶 ACK + 소프트 플래그(heartbeat.state)만 | 실제 정지 연동은 다음 단계(§5) |
| `START`/`STOP`/`SET_SPEED`/`BLACKLIST_ADD`/그 외 | `POST /api/v1/command` | 🔶 ACK 골격만 | body `{"type":"...", "args":{...}}`. 프로토콜 형태 확인용, 로봇 동작 미반영(의도된 범위) |

**범위(의도적 축소):** 비전(카메라→포인트클라우드→볼트 인식)은 이 브릿지를 거치지
않는다 — 데스크톱 앱이 직접 통신하는 별개 파이프라인이라서다. 여기서 검증하는 건
**로봇팔 ↔ 데스크톱 통신**뿐이다.

전체 메시지 카탈로그, 필드 스펙(타입/단위/필수여부), enum, `fail_reason` 코드
표는 [`desktop_protocol.md`](./desktop_protocol.md) §2·부록 참고. `fail_reason`
매핑의 유일한 소스는 코드: `src/bin_picking/bin_picking/protocol.py`의
`FAIL_REASON_MAP`.

---

## 4. 5분 안에 확인해보기 + 실측한 검증 내역

### 데스크톱 개발자가 지금 바로 해볼 수 있는 것
```bash
# 로봇쪽 (터미널 1)
ros2 run bin_picking desktop_bridge --ros-args -p api_token:=devtoken

# 데스크톱쪽 (터미널 2) — curl로 바로 테스트 가능
curl -H "Authorization: Bearer devtoken" http://localhost:8765/api/v1/status
curl -H "Authorization: Bearer devtoken" -H "Content-Type: application/json" \
  -X POST http://localhost:8765/api/v1/pick_bolt \
  -d '{"bolt_id":"b1","rank":1,"frame":"fr3_link0","stamp":1753305599980000000,
       "pose":{"position":[0.4,0.0,0.2],"orientation":[0.0,0.707,0.0,0.707]}}'

# 참고 구현이자 스모크테스트(REST+WS 왕복 전체)
python3 src/bin_picking/tools/mock_desktop_client.py --token devtoken            # 대화형 데모
python3 src/bin_picking/tools/mock_desktop_client.py --token devtoken --assert   # 자동 검증(종료코드 0/1)
```
`mock_desktop_client.py`는 ROS 의존성이 전혀 없다 — REST 호출은 표준 라이브러리
`urllib`, 텔레메트리 수신은 `pip install websockets`만으로 아무 컴퓨터에서나 실행
가능. 실제로 어떻게 접속·명령을 보내는지 보는 참고 코드로 그대로 써도 된다.

### 실측 검증 내역
| 검증 | 결과 |
|---|---|
| `protocol.py` 단위 테스트 (`pytest test/`, ROS 불필요) | **21개 전부 통과**(v3 전환 후에도 그대로) |
| 단독 기동(Gazebo 없이) + `mock_desktop_client.py --assert` | **전부 통과**(2026-08-04) — REST/WS 인증(401), 필수필드 검증, 정상 PICK_BOLT(int 좌표 포함), 알 수 없는 명령 거부, `SET_SPEED`→`GET_STATUS` 반영, heartbeat, 동시 요청 하 WS `seq` 중복 없음(REST 스레드↔rclpy 타이머 스레드 락 검증) |
| Gazebo+MoveIt+`desktop_bridge`+`integrated_pick_place` 풀스택(구v2 전송으로 검증, 2026-08-04) | **정상 기동, 실제 자동 파지 사이클 성공(볼트 3개 픽업·이동 완료, 로그 근거)** — `_pick_bolt_core`/`_cycle_result_cb`(전송 방식과 무관한 순수 로직)는 v3 전환 후에도 문자 그대로 동일 |

### 이번에 발견해서 고친 것

**1) WS 바인드 실패 시 좀비 상태(2026-08-04, v2 단계에서 발견):** 이전
`desktop_bridge` 인스턴스가 남아 포트를 쥔 채로 새 인스턴스를 띄우면, 새 인스턴스는
서버 바인드에 실패하는데 이 실패가 stderr 트레이스백 한 줄로만 남고 ROS 로그는
계속 "대기 중"이라고 보고했다 — ROS 노드는 살아서 구독·타이머는 계속 돌지만 서버는
죽은 "절반만 동작하는" 좀비 상태였다. 바인드 실패 시 `FATAL` 로그로 원인+대처법을
남기고 좀비로 안 남기고 즉시 프로세스를 종료(`os._exit(1)`)하도록 하드닝했다
(`SIGINT` 로 정상 종료 경로를 태우는 방식은 스레드 간 신호 타이밍 레이스로 간헐적으로
안 죽는 걸 실측으로 확인하고 폐기).

**2) REST 전환 중 발견한 프로세스 전체 abort 버그(2026-08-04):** REST 로 좌표에
정수값(`0` — 소수점 없음, 예: `"position":[0.4, 0, 0.2]`)을 보내면 브릿지 전체가
죽었다. 원인: JSON은 int/float을 구분하지 않아 `json.loads()`가 `0`을 Python
`int`로 파싱하는데, rclpy 생성 바인딩은 float64 메시지 필드에 int가 들어오면
**catch 가능한 예외가 아니라 C 단 `assert()` 로 프로세스 전체를 abort**시킨다.
`validate_pick_bolt()`는 부록F 스펙대로 "숫자"면 int/float 상관없이 통과시키므로
이 방어는 놓치기 쉬웠다 — `_pick_bolt_core()`에서 좌표를 ROS 메시지에 넣기 직전
`float()`로 명시 변환하도록 고쳤다. **데스크톱 개발자에게 중요:** 좌표를 보낼 때
`0`처럼 정수로 보여도 서버가 알아서 방어하니 문제없지만, 혹시 다른 통신 방식으로
포팅할 때 이 함정을 기억해 둘 것 — JSON 라이브러리에 따라 정수/실수 구분이 다르다.

---

## 5. 알려진 제약 (지금 단계, 의도된 범위)

- **TLS는 선택, 기본은 평문.** `tls_cert`/`tls_key`를 안 주면 HTTP/WS 그대로 뜬다
  (경고 로그는 남음). 신뢰된 사설망(같은 컴퓨터/LAN) 밖에는 노출하지 말 것.
- **인증은 고정 공유 토큰 하나뿐**(사용자별 계정/권한 구분 없음). 이 프로젝트
  규모(로봇 1대, 데스크톱 앱 1개, 신뢰된 팀 내 사용) 기준으로는 충분하지만, 여러
  운영자가 다른 권한으로 붙어야 하면 다음 단계 과제.
- **동시 다중 클라이언트**: 텔레메트리(`arm_state`/`heartbeat`)는 연결된 모든 WS
  클라이언트에 브로드캐스트되지만, `PICK_BOLT` 대기 슬롯은 **1개뿐**이다. 여러
  데스크톱 클라이언트가 동시에 `PICK_BOLT`를 보내면 경쟁 상태 — 지금은 "한 번에
  한 사이클"만 전제한다.
- **heartbeat/arm_state 타이밍**: 풀스택(Gazebo) 기동 시 이 타이머들은 **시뮬
  시계** 기준이다. 로봇 컴퓨터가 파지 계획(MoveIt/OMPL)으로 바빠 시뮬 실시간계수가
  떨어지면 1Hz heartbeat 간격이 벽시계 기준으로 늘어질 수 있다. `t_sim`/`t_wall`
  이중 표기로 구분 가능하니(`desktop_protocol.md` §3), **진짜 연결 끊김 판정은
  heartbeat 수신 횟수보다 `t_wall` 기준 정체 시간으로 하길 권장**한다(예: 수 초
  이상 `t_wall` 기준 응답 없음 → `LINK_DOWN`으로 판정, 단발성 heartbeat 지연은
  정상 범위로 흡수).
- `PICK_BOLT`/`GET_STATUS`/`ESTOP` 외 제어 명령(`/api/v1/command`)은 ACK 골격만 —
  로봇 동작 미반영(다음 단계, `PROGRESS.md` 로드맵 참고).

---

## 6. 트러블슈팅

| 증상 | 원인 / 대처 |
|---|---|
| REST 요청에 `401 {"error":"unauthorized"}` | 토큰 누락/오타. `Authorization: Bearer <token>` 헤더 확인, 값은 브릿지 시작 로그의 `API_TOKEN` 또는 `-p api_token:=`로 지정한 값과 일치해야 함 |
| WS 연결이 핸드셰이크 단계에서 거부됨(HTTP 401) | `?token=<token>` 쿼리스트링 누락/오타. REST와 동일한 토큰 사용 |
| `[FATAL] HTTP/WS 서버 기동 실패 ... address already in use` | 다른 `desktop_bridge` 프로세스가 이미 포트를 쥐고 있음. `ss -ltnp \| grep 8765`로 확인 → `pkill -f desktop_bridge`로 정리 후 재시작. (이 상황은 조용히 넘어가지 않고 로그에 바로 FATAL로 찍히고 그 인스턴스는 즉시 종료된다 — §4 참고) |
| `arm_state`가 안 옴 | Gazebo 없이 `desktop_bridge`만 단독 기동했으면 **정상**(설계상 그럼, `/joint_states` 발행자가 없어서). 풀스택(§1-B)으로 띄웠는데도 안 오면 `alert{code:"NO_JOINT_STATE"|"TF_STALE"}` 수신 여부 확인 |
| WS 연결은 되는데 아무 메시지도 안 옴 | 연결 직후 브릿지가 자동으로 `STATUS` 스냅샷을 먼저 보낸다 — 그게 안 오면 접속 자체가 안 된 것. WS는 이제 순수 스트림이라 클라이언트가 보내는 메시지에 응답하지 않는다(명령은 REST로) |
| `PICK_BOLT` REST 응답은 오는데 `RESULT`가 WS로 안 옴 | Gazebo/MoveIt 없이 단독 기동(§1-A) 상태면 정상(받을 로봇이 없음) — §1-B로 풀스택 기동 필요. deadline을 지정했다면 초과 여부도 확인(응답에서 바로 `accepted:false`로 거부됨) |
| `ModuleNotFoundError: aiohttp`(로봇쪽) | `pip install --user --break-system-packages aiohttp` |
| `ModuleNotFoundError: websockets`(mock_desktop_client 쪽) | `pip install --user --break-system-packages websockets` |
| 다른 컴퓨터에서 접속이 안 됨 | WSL2 내부 IP는 외부에서 직접 안 보임 — §2 "다른 물리 머신" 절의 포트포워딩 필요 |
| 자체서명 인증서 경고/거부 | 개발 중엔 클라이언트의 "인증서 검증 무시" 옵션 사용(curl `-k` 등). 실배포 전엔 정식 인증서로 교체 |

---

## 7. 다음 단계 (아직 준비 안 된 것)

- `ESTOP` 외 나머지 제어 명령의 실제 로봇 동작 연동.
- `fail_reason` 세분화(`REACH_FILTERED`/`COLLISION_ABORT`/`JOINT_LIMIT`/`TIMEOUT` — 현재
  로봇 파이프라인이 아직 구분해내지 못하는 실패 종류).
- Deadman 워치독 + `RESET` 안전 게이팅(하드웨어 안전회로 연동 대비 자리 확보용).
- 사용자별 인증/권한 구분(지금은 고정 공유 토큰 하나뿐, §5).

자세한 로드맵은 [`PROGRESS.md`](../PROGRESS.md) 참고.
