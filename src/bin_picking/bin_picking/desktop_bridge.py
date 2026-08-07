# -*- coding: utf-8 -*-
"""데스크톱앱 ↔ 로봇 통신 브릿지 (독립 노드).

목적: `docs/desktop_protocol.md` 의 §2 데이터 카탈로그를 실제로 주고받는
**통신 방식 자체를 검증**한다. 데스크톱앱은 별도 팀이 만들 것이므로, 이 노드는
그 반대편(로봇 쪽) 통신 종단점을 먼저 완성해 두는 역할만 한다.

와이어(v3, 2026-08-04 개정): **REST(명령) + WebSocket(텔레메트리 스트림 전용)
하이브리드**, 같은 포트(기본 8765) 안에서 경로로만 구분한다.
  - `POST /api/v1/pick_bolt`, `POST /api/v1/estop`, `POST /api/v1/command`,
    `GET /api/v1/status` — 명령/조회. 아무 언어의 흔한 HTTP 클라이언트(curl 포함)로
    바로 붙을 수 있다.
  - `GET /ws/telemetry` — 접속 직후 STATUS 스냅샷 1회 + 이후 arm_state(20Hz)·
    heartbeat(1Hz)·RESULT·grasp_result·ALERT 를 순수 서버→클라이언트로 스트림.
    클라이언트가 보내는 메시지는 더 이상 명령으로 처리하지 않는다(v2까지는 명령도
    이 WS 연결로 받았다 — REST 로 분리한 이유는 desktop_protocol.md §4 참고).
  - **인증**: 모든 `/api/*` 는 `Authorization: Bearer <token>` 필수. WS 는 핸드셰이크에
    커스텀 헤더를 못 붙이는 클라이언트도 있어 `?token=` 쿼리스트링도 허용한다.
    토큰을 파라미터로 안 주면 기동 시 임의 생성해 로그에 크게 출력한다(로컬 테스트는
    설정 없이 바로 되고, 실배포는 `-p api_token:=<값>` 로 고정).
  - **TLS(선택)**: `tls_cert`/`tls_key` 파라미터를 주면 HTTPS/WSS 로 뜬다. 안 주면
    평문으로 뜨되 경고 로그를 남긴다 — 신뢰된 사설망 밖에 노출하지 말 것(§5).

rosbridge 대신 직접 구현한 이유는 desktop_protocol.md §4 참고 — 핵심은 "데스크톱
개발자가 ROS/roslib 없이, 표준 HTTP/WebSocket 클라이언트만으로 이 문서의 JSON
스키마를 주고받을 수 있어야 한다"는 것.

의도적으로 `integrated_pick_place` 노드(pick_place_node.py, 1000줄+ 갓클래스)와
프로세스를 분리했다:
  - 통신 프로토콜(이 파일)과 파지 로직(pick_place_node)이 서로 다른 이유로
    바뀌므로 같이 죽지 않는다 — 브릿지만 재시작해도 로봇 사이클이 안 끊긴다.
  - Gazebo/MoveIt 없이도 이 노드 혼자 켜서 와이어 프로토콜만 검증할 수 있다
    (/joint_states 가 없으면 arm_state 는 그냥 안 나갈 뿐, 나머지는 동작).

로봇 파이프라인과의 연결점은 딱 둘, 전부 기존 ROS 토픽이라 프로세스가
달라도 그대로 동작한다:
  - PICK_BOLT 수신 → EXT_POSE_TOPIC(`/next_bolt_pose`)에 그대로 재발행.
    (이미 존재하는 "외부 비전 입력" 경로를 재사용 — pick_place_node 쪽 코드는
    한 줄도 안 건드린다.)
  - 그 결과 → CYCLE_RESULT_TOPIC(`/bin_picking/cycle_result`)를 구독.
    (selection.py `_log_attempt` 에 추가한 1줄짜리 발행 훅이 소스.) 이 콜백은
    전송 방식(REST/WS)과 무관하다 — PICK_BOLT 가 어느 채널로 들어왔든 결과는
    항상 WS 텔레메트리로 나간다(상관관계는 `_pending_pick['id']`, REST 응답의
    `id` 와 동일).

현재 단계에서 "진짜로" 로봇에 반영되는 명령은 PICK_BOLT 뿐이다. 나머지
제어 명령(ESTOP/START/SET_SPEED 등)은 ACK 까지만 진짜고 실제 로봇 동작
연동은 다음 단계(로봇측 연동 인터페이스, PROGRESS.md 참고)로 남겨 둔다 —
이번 목표는 "통신 기능 자체 검증"이라 프로토콜 골격을 정직하게 완성하는 데 집중했다.
"""
import asyncio
import hmac
import json
import os
import secrets
import ssl
import sys
import threading
import time
import uuid

import rclpy
from rclpy.node import Node

from geometry_msgs.msg import PoseStamped
from sensor_msgs.msg import JointState
from std_msgs.msg import String
from tf2_ros import Buffer, TransformListener
from tf2_ros import LookupException, ConnectivityException, ExtrapolationException

from bin_picking.config import PickPlaceConfig
from bin_picking import protocol

try:
    from aiohttp import web
    _AIOHTTP_IMPORT_ERR = ''
except Exception as _exc:                       # noqa: BLE001
    web = None
    _AIOHTTP_IMPORT_ERR = repr(_exc)


# 프로토콜 버전은 protocol.py 가 유일한 소스(v3 — REST+WS 하이브리드 전송 전환 +
# 토큰 인증 도입. v1→v2 때처럼 호환 shim 없이 클린 브레이크, 이유는 protocol.py 참고).
PROTOCOL_VERSION = protocol.PROTOCOL_VERSION
# pick_place_node 의 "외부 비전 6D 자세" 입력 토픽을 그대로 재사용한다
# (config.py 단일 소스 — 여기서 문자열을 따로 하드코딩하지 않는다).
EXT_POSE_TOPIC = PickPlaceConfig.EXT_POSE_TOPIC
REFERENCE_FRAME = PickPlaceConfig.REFERENCE_FRAME
ARM_JOINTS = PickPlaceConfig.ARM_JOINTS
GRIPPER_JOINT = PickPlaceConfig.GRIPPER_JOINT
TCP_LINK = PickPlaceConfig.END_EFFECTOR_LINK
JOINT_LIMITS = PickPlaceConfig.JOINT_LIMITS
# selection.py `_log_attempt` 훅이 사이클 결과를 얹어 발행하는 토픽.
CYCLE_RESULT_TOPIC = PickPlaceConfig.CYCLE_RESULT_TOPIC

# 실제 로봇 동작 연동 없이 ACK 만 돌려주는 "골격만" 명령 — §2A 전체 명령 표 중
# PICK_BOLT/GET_STATUS/ESTOP 을 뺀 나머지. `POST /api/v1/command` 하나로 받는다.
# 다음 단계에서 하나씩 실동작에 연결.
_ACK_ONLY_TYPES = frozenset([
    'START', 'STOP', 'PAUSE', 'RESUME', 'SET_MODE', 'STEP', 'SKIP_CURRENT',
    'BLACKLIST_ADD', 'BLACKLIST_REMOVE', 'HOLD_BOLT', 'UNHOLD_BOLT',
    'SET_SELECTOR', 'SET_PLACE_SLOT', 'SET_SPEED', 'GO_HOME', 'RESET',
    'ACK_ALARM',
])


def _now_ns():
    return time.time_ns()


class DesktopBridgeNode(Node):

    def __init__(self):
        # ⚠ use_sim_time 을 강제 True 로 박지 않는다(pick_place_node 와 달리).
        # 이 노드는 Gazebo 없이 "통신 자체"만 검증하는 용도로도 단독 실행되는데,
        # /clock 발행자가 없는 채로 use_sim_time=True 면 ROS 시계가 절대 안
        # 흘러 create_timer 가 전부 멈춘다(heartbeat/arm_state 무발행 — 실제로
        # 겪은 버그). 기본은 벽시계, Gazebo 스택과 같이 띄울 때만 launch 인자로
        # use_sim_time:=true 를 넘겨 나머지 노드들과 시계를 맞춘다.
        super().__init__('desktop_bridge')
        # ⚠ 이 가드가 클래스 정의 시점보다 먼저 돌아야 한다 — 그래서 `_auth_middleware`
        # 는 클래스 본문에서 `@web.middleware` 로 감싸지 않고, `web` 이 None 이 아님이
        # 보장된 서버 기동 시점(`_serve_forever`)에 감싼다.
        if web is None:
            raise RuntimeError(
                f'aiohttp 패키지가 없습니다 ({_AIOHTTP_IMPORT_ERR}). '
                f'`pip install --user --break-system-packages aiohttp` 후 재실행하세요.')

        self.declare_parameter('host', '0.0.0.0')
        self.declare_parameter('port', 8765)
        self.declare_parameter('arm_state_hz', 20.0)
        self.declare_parameter('heartbeat_hz', 1.0)
        self.declare_parameter('api_token', '')
        self.declare_parameter('tls_cert', '')
        self.declare_parameter('tls_key', '')
        self.declare_parameter('require_tls', False)
        self.declare_parameter('allow_insecure_nonloopback', False)
        self._require_tls = bool(self.get_parameter('require_tls').value)
        self._allow_insecure_nonloopback = bool(
            self.get_parameter('allow_insecure_nonloopback').value)
        self._host = self.get_parameter('host').value
        self._port = int(self.get_parameter('port').value)
        arm_state_hz = float(self.get_parameter('arm_state_hz').value)
        heartbeat_hz = float(self.get_parameter('heartbeat_hz').value)

        # --- 인증 토큰: 안 주면 임의 생성 + 로그에 크게 출력(Jupyter 토큰과 동일한
        # 관례) — 로컬 테스트는 설정 없이 바로 되고, 실배포는 launch 인자로 고정값을
        # 박아 데스크톱팀과 공유한다. ---
        token_param = self.get_parameter('api_token').value
        self._api_token = token_param if token_param else secrets.token_urlsafe(24)
        if not token_param:
            self.get_logger().warn(
                '=' * 70 + '\n'
                f'[desktop_bridge] api_token 파라미터가 없어 임의 토큰을 생성했습니다.\n'
                f'  API_TOKEN = {self._api_token}\n'
                f'데스크톱 클라이언트는 REST 는 `Authorization: Bearer <token>` 헤더,\n'
                f'WS 는 `?token=<token>` 쿼리스트링으로 이 값을 보내야 합니다.\n'
                f'고정값을 쓰려면 `-p api_token:=<값>` 로 지정하세요.\n'
                + '=' * 70)

        # --- TLS(선택): 인증서/키를 주면 HTTPS/WSS, 안 주면 평문 + 경고 로그. ---
        tls_cert = self.get_parameter('tls_cert').value
        tls_key = self.get_parameter('tls_key').value
        self._ssl_context = None
        if tls_cert and tls_key:
            ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
            ctx.load_cert_chain(tls_cert, tls_key)
            self._ssl_context = ctx
            self._scheme_http, self._scheme_ws = 'https', 'wss'
        else:
            self._scheme_http, self._scheme_ws = 'http', 'ws'
            self.get_logger().warn(
                '[desktop_bridge] tls_cert/tls_key 미설정 — 평문 HTTP/WS로 기동합니다. '
                '신뢰된 사설망 밖에 노출하지 마세요(desktop_protocol.md §5).')

        # 평문인데 loopback 밖으로 바인딩하면 Bearer 토큰이 네트워크에 그대로
        # 노출된다 — 경고만 남기고 그냥 열어 주던 걸 기동 거부로 바꾼다.
        if self._ssl_context is None:
            if self._require_tls:
                raise RuntimeError(
                    'require_tls:=true 인데 tls_cert/tls_key 가 없습니다. '
                    '인증서를 지정하거나 require_tls:=false 로 내리세요.')
            if (self._host not in ('127.0.0.1', 'localhost', '::1')
                    and not self._allow_insecure_nonloopback):
                raise RuntimeError(
                    f'TLS가 설정되지 않은 상태로 loopback이 아닌 host({self._host})에 '
                    f'바인딩할 수 없습니다 — tls_cert/tls_key 를 주거나 '
                    f'allow_insecure_nonloopback:=true 로 우회하세요.')

        # --- 로봇 상태 구독 (arm_state 스트림 재료) ---
        self._joint_state = None
        self._prev_q = None
        self._tf_buf = Buffer()
        self._tf_listener = TransformListener(self._tf_buf, self)
        self.create_subscription(JointState, 'joint_states', self._joint_state_cb, 10)

        # --- 사이클 결과 구독 (selection.py `_log_attempt` 훅 → RESULT) ---
        self.create_subscription(String, CYCLE_RESULT_TOPIC, self._cycle_result_cb, 10)

        # --- PICK_BOLT → 기존 외부비전 입력 경로로 재발행 ---
        self._pose_pub = self.create_publisher(PoseStamped, EXT_POSE_TOPIC, 10)

        # --- 명령 상태 (ACK-only 명령들의 최근값 — GET_STATUS 조회용) ---
        self._cmd_state = {}
        self._estop = False
        self._estop_lock = threading.Lock()  # 서버 스레드가 쓰고 rclpy 타이머가 읽는다
        self._pending_pick = None      # {'id':.., 'ts':.., 'bolt_id':..} 단일 슬롯
        self._pending_lock = threading.Lock()
        self._seq = 0
        self._seq_lock = threading.Lock()   # rclpy 스레드 + 서버 스레드 양쪽에서 증가됨
        self._connected = 0
        # 타이머 구동 메시지(heartbeat/arm_state)용 "가장 최근에 관측된 cycle_id".
        # 이 값은 절대 브릿지가 지어내지 않는다 — cycle_result 에서 echo 만 받는다
        # (첫 사이클 전에는 None — 어떤 사이클도 아직 없었다는 뜻을 정직하게 표현).
        self._last_cycle_id = None
        self._arm_state_stall_count = 0
        self._arm_state_stall_alerted = False

        # --- HTTP/WS 서버: 별도 스레드에서 자체 이벤트루프 실행 ---
        # `_outbox`(rclpy 스레드→서버 스레드 브로드캐스트 큐)는 asyncio.Queue 라
        # 이벤트루프가 생긴 뒤 서버 스레드에서 만든다(_run_server).
        self._outbox = None
        self._ws_clients = set()
        self._loop = None
        self._server_thread = threading.Thread(target=self._run_server, daemon=True)
        self._server_thread.start()

        # --- 텔레메트리 타이머 ---
        self.create_timer(1.0 / max(arm_state_hz, 1.0), self._tick_arm_state)
        self.create_timer(1.0 / max(heartbeat_hz, 0.1), self._tick_heartbeat)

        self.get_logger().info(
            f'[desktop_bridge] 대기 중: '
            f'{self._scheme_http}://{self._host}:{self._port}/api/v1/* (명령), '
            f'{self._scheme_ws}://{self._host}:{self._port}/ws/telemetry (스트림) '
            f'(PICK_BOLT → {EXT_POSE_TOPIC}, 결과 ← {CYCLE_RESULT_TOPIC})')

    # =========================================================
    # HTTP/WS 서버 (백그라운드 스레드 + 자체 asyncio 루프)
    # =========================================================
    def _run_server(self):
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        self._outbox = asyncio.Queue(maxsize=500)
        self._loop = loop   # _send 의 가드가 보는 값 — _outbox 다음에 세팅한다
        try:
            loop.run_until_complete(self._serve_forever())
        except Exception as exc:                   # noqa: BLE001
            # 이 스레드는 daemon 이라 여기서 예외가 나도 프로세스는 안 죽고 노드는
            # rclpy.spin() 만 계속 돈다 — 서버는 죽었는데 구독자/타이머는 살아
            # 있는 "절반만 동작하는" 상태로 조용히 남는다(실제로 겪음: 포트 충돌
            # 시 stderr 트레이스백 한 줄만 남고 ROS 로그는 "대기 중"이라고 계속
            # 보고해 운영자가 못 알아챈다). 그래서 조용히 넘어가지 않고 크게
            # 실패시킨다.
            self._fatal_exit(
                f'HTTP/WS 서버 기동 실패 ({self._host}:{self._port}) — 포트 충돌이면 '
                f'다른 desktop_bridge 프로세스가 이미 떠 있는지 확인하세요'
                f'(`ss -ltnp | grep {self._port}` 또는 `pkill -f desktop_bridge`)',
                exc)
        finally:
            loop.close()

    def _fatal_exit(self, context, exc):
        """절반만 동작하는 상태로 남지 않도록 즉시·확실하게 프로세스를 끝낸다."""
        self.get_logger().fatal(
            f'[desktop_bridge] {context}: {exc!r} — 절반만 동작하는 상태로 두지 않고 '
            f'노드를 즉시 종료합니다.')
        # rclpy.shutdown()/SIGINT 로 정상 종료 경로를 태우는 방식은 메인 스레드가
        # ROS 내부 C 대기 중일 때 신호 처리가 간헐적으로 지연·유실되어 프로세스가
        # 안 죽는 걸 실측으로 확인했다(스레드 간 신호 타이밍 레이스). 여기 오는
        # 실패들은 정리할 런타임 상태가 없으므로 os._exit 를 쓰되, 그 전에 로그가
        # 실제로 나가도록 flush 한다(os._exit 는 버퍼를 안 비운다).
        sys.stdout.flush()
        sys.stderr.flush()
        os._exit(1)

    async def _serve_forever(self):
        # `web.middleware` 적용은 여기서 — 클래스 정의 시점엔 aiohttp 임포트 실패로
        # `web` 이 None 일 수 있고, 그러면 __init__ 의 친절한 가드보다 먼저 죽는다.
        # 바운드 메서드에는 직접 못 씌운다(`web.middleware` 가 함수 객체에 마커
        # 속성을 다는데 메서드 객체는 속성 대입을 거부한다) — 얇은 함수로 감싼다.
        @web.middleware
        async def auth_middleware(request, handler):
            return await self._auth_middleware(request, handler)

        app = web.Application(middlewares=[auth_middleware])
        app.router.add_post('/api/v1/pick_bolt', self._http_pick_bolt)
        app.router.add_post('/api/v1/estop', self._http_estop)
        app.router.add_post('/api/v1/command', self._http_command)
        app.router.add_get('/api/v1/status', self._http_status)
        app.router.add_get('/ws/telemetry', self._ws_telemetry)

        # access_log=None: aiohttp 기본 액세스 로그는 요청 URL 을 통째로 찍어
        # `/ws/telemetry?token=<API 토큰>` 의 토큰이 로그 파일에 평문으로 남는다.
        # 의미 있는 이벤트는 이 파일이 self.get_logger() 로 따로 남긴다.
        runner = web.AppRunner(app, access_log=None)
        await runner.setup()
        site = web.TCPSite(runner, self._host, self._port, ssl_context=self._ssl_context)
        await site.start()   # 바인드 실패 시 여기서 OSError — _run_server 가 잡는다

        # 예외를 done-callback 으로 받는다 — 안 그러면 브로드캐스터가 죽어도
        # 텔레메트리만 조용히 멈춘 채 서버는 계속 살아 있다(침묵은 버그다).
        broadcaster_task = asyncio.create_task(self._broadcaster())
        broadcaster_task.add_done_callback(self._on_broadcaster_done)
        await asyncio.Future()   # 서버가 닫힐 때까지 무한 대기

    def _on_broadcaster_done(self, task):
        if task.cancelled():
            return
        exc = task.exception()
        if exc is not None:
            self._fatal_exit('broadcaster 태스크 실패', exc)

    async def _broadcaster(self):
        """rclpy 스레드가 `_outbox` 에 넣은 메시지를 연결된 모든 WS 클라이언트에 브로드캐스트."""
        while True:
            text = await self._outbox.get()
            if not self._ws_clients:
                continue
            await asyncio.gather(
                *(self._send_to_client(ws, text) for ws in list(self._ws_clients)),
                return_exceptions=True)

    async def _send_to_client(self, ws, text):
        """느린 클라이언트 하나가 나머지 브로드캐스트를 막지 않게 타임아웃을 건다."""
        try:
            await asyncio.wait_for(ws.send_str(text), timeout=2.0)
        except asyncio.TimeoutError:
            self.get_logger().warn(
                '[desktop_bridge] WS 클라이언트 송신 타임아웃(2s) — 연결을 닫습니다.')
            await ws.close()

    # =========================================================
    # 인증
    # =========================================================
    def _token_matches(self, token):
        # hmac.compare_digest 는 str 인자가 ASCII 밖이면 TypeError 를 던진다 —
        # 비ASCII 토큰을 보내는 클라이언트가 401 대신 500 을 받는 걸 막는다.
        if not isinstance(token, str) or not token.isascii():
            return False
        return hmac.compare_digest(token, self._api_token)

    async def _auth_middleware(self, request, handler):
        # `/api/*` 만 검사한다 — `/ws/telemetry` 는 핸드셰이크에 커스텀 헤더를 못
        # 붙이는 클라이언트도 있어 쿼리스트링 토큰으로 핸들러 안에서 따로 검사한다.
        if request.path.startswith('/api/'):
            auth = request.headers.get('Authorization', '')
            # RFC 7235: auth-scheme 은 대소문자 구분 없음("bearer" 도 유효).
            scheme, _, token = auth.partition(' ')
            if scheme.lower() != 'bearer':
                token = ''
            if not self._token_matches(token):
                return web.json_response({'error': 'unauthorized'}, status=401)
        return await handler(request)

    def _check_ws_token(self, request):
        return self._token_matches(request.query.get('token', ''))

    # =========================================================
    # 명령 처리 (§2A, REST) — 동기, 빠른 연산만 (asyncio 루프를 막지 않는다)
    # =========================================================
    async def _http_status(self, request):
        return web.json_response(self._status_args())

    async def _http_estop(self, request):
        with self._estop_lock:
            self._estop = True
        self.get_logger().warn(
            '[desktop_bridge] ESTOP 수신 — 소프트 플래그만 설정됨. '
            '실제 정지는 물리 E-STOP/로봇 안전컨트롤러가 담당(§5).')
        return web.json_response({'accepted': True})

    async def _http_command(self, request):
        body = await self._read_json(request)
        if body is None:
            return web.json_response({'error': 'invalid json'}, status=400)
        mtype = body.get('type')
        if mtype not in _ACK_ONLY_TYPES:
            return web.json_response(
                {'accepted': False, 'errors': [f'unknown command type: {mtype!r}']})
        self._cmd_state[mtype] = body.get('args') or {}
        return web.json_response({'accepted': True})

    async def _http_pick_bolt(self, request):
        args = await self._read_json(request)
        if args is None:
            return web.json_response({'error': 'invalid json'}, status=400)
        cmd_id = f'pick_bolt-{uuid.uuid4().hex[:8]}'
        result = self._pick_bolt_core(cmd_id, args)
        return web.json_response({'id': cmd_id, **result})

    @staticmethod
    async def _read_json(request):
        try:
            body = await request.json()
        except (json.JSONDecodeError, ValueError):
            return None
        return body if isinstance(body, dict) else None

    def _pick_bolt_core(self, cmd_id, args):
        """PICK_BOLT 검증+재발행 — 전송 형식(REST) 과 무관한 순수 로직.

        결과 상관관계: `cmd_id`(REST 응답의 `id`)가 나중에 WS 텔레메트리로 오는
        `RESULT.corr` 와 같은 값이다 — `_cycle_result_cb` 는 이 값을 그대로
        echo 하므로, PICK_BOLT 가 어느 채널로 들어왔는지는 신경 쓰지 않는다.
        """
        # ESTOP 이 걸린 동안은 새 파지를 로봇으로 흘려보내지 않는다 — 소프트
        # 플래그지만 "정지 요청 후에도 명령이 계속 나가는" 상태보다는 정직하다.
        with self._estop_lock:
            if self._estop:
                return {'accepted': False, 'errors': ['estop active']}

        # 부록F 필수 필드 검증 + frame/deadline 확인 + float 강제변환 — 전부
        # protocol.py 의 순수 함수가 담당한다(rclpy 없이 pytest 로 검증 가능).
        errors, pos, quat = protocol.build_pick_bolt_pose(args, REFERENCE_FRAME, _now_ns())
        if errors:
            # deadline 초과는 조용히 흘려보내지 않고 ALERT 까지 띄운다.
            if errors == ['stale: deadline exceeded']:
                self._send(self._envelope('ALERT', {
                    'severity': 'warn', 'code': 'STALE_COMMAND',
                    'msg': f'PICK_BOLT {cmd_id} deadline exceeded',
                    'context': {'bolt_id': args.get('bolt_id')},
                }))
            return {'accepted': False, 'errors': errors}

        # ⚠ 이 메서드는 aiohttp 서버 스레드에서 돈다(rclpy spin 스레드가 아니다).
        # 아래 rclpy Node API 들은 내부적으로 스레드 세이프하므로 그대로 호출해도
        # 된다 — publish 는 rcl_publish 가 락을 잡고, 시계 읽기/로깅도 rclpy·rcutils
        # 단에서 보호된다. 큐로 rclpy 스레드에 넘기는 식으로 "고치지" 말 것.
        msg = PoseStamped()
        msg.header.frame_id = REFERENCE_FRAME
        msg.header.stamp = self.get_clock().now().to_msg()
        msg.pose.position.x, msg.pose.position.y, msg.pose.position.z = pos
        (msg.pose.orientation.x, msg.pose.orientation.y,
         msg.pose.orientation.z, msg.pose.orientation.w) = quat

        # 결과 상관관계 슬롯은 하나뿐이라, 앞선 파지가 끝나기 전에 들어온 두 번째
        # PICK_BOLT 는 거부한다 — 덮어쓰면 먼저 온 명령의 RESULT 가 영영 안 나간다.
        # axis(옵션)는 예전엔 조용히 버려졌다 — 로그에 남겨 실제로 쓰였는지
        # 확인 가능하게만 해 둔다(로봇 정렬에 참고용, 필수 아님).
        with self._pending_lock:
            if self._pending_pick is not None:
                return {'accepted': False, 'errors': ['pick already in progress']}
            self._pending_pick = {
                'id': cmd_id, 'ts': time.time(), 'bolt_id': args.get('bolt_id'),
                'axis': args.get('axis')}

        self._pose_pub.publish(msg)
        self.get_logger().info(
            f'[desktop_bridge] PICK_BOLT {cmd_id} → {EXT_POSE_TOPIC} 재발행 '
            f'(bolt_id={args.get("bolt_id")}, rank={args.get("rank")}, '
            f'axis={args.get("axis")})')
        return {'accepted': True}

    # =========================================================
    # 텔레메트리 WebSocket (순수 서버→클라이언트 스트림)
    # =========================================================
    async def _ws_telemetry(self, request):
        if not self._check_ws_token(request):
            return web.Response(status=401, text='unauthorized')

        ws = web.WebSocketResponse()
        await ws.prepare(request)
        self._ws_clients.add(ws)
        self._connected = len(self._ws_clients)
        self.get_logger().info(f'[desktop_bridge] WS 클라이언트 연결 (현재 {self._connected}개)')
        try:
            # 재연결 시 즉시 스냅샷 — §4 "재연결 시 스냅샷+델타" 최소 구현.
            await ws.send_str(json.dumps(self._status_envelope()))
            # 순수 스트림이라 클라이언트가 보내는 메시지는 더 이상 명령으로 처리하지
            # 않는다(명령은 REST 로 분리, §4). 다만 v2 클라이언트가 WS 로 명령을
            # 보내면 예전엔 완전 무음이라 "먹혔는지 씹혔는지" 구분이 안 됐다 —
            # 연결당 딱 한 번 ALERT 로 알려 준다(§4 "침묵은 버그다").
            warned = False
            async for msg in ws:
                if warned or not msg.data:
                    continue
                warned = True
                self.get_logger().warn(
                    '[desktop_bridge] WS 로 들어온 메시지를 무시했습니다 — v3부터 명령은 '
                    'REST(/api/v1/*) 전용입니다.')
                await ws.send_str(json.dumps(self._envelope('ALERT', {
                    'severity': 'warn', 'code': 'WS_COMMANDS_DEPRECATED',
                    'msg': 'v3부터 WS로 명령을 보낼 수 없습니다. REST API를 사용하세요.',
                })))
        except Exception as exc:                 # noqa: BLE001
            self.get_logger().warn(f'[desktop_bridge] WS 연결 오류: {exc!r}')
        finally:
            self._ws_clients.discard(ws)
            self._connected = len(self._ws_clients)
            self.get_logger().info(f'[desktop_bridge] WS 클라이언트 연결 종료 (현재 {self._connected}개)')
        return ws

    # =========================================================
    # 로봇 → 데스크톱 (§2B, WS 텔레메트리)
    # =========================================================
    def _joint_state_cb(self, msg):
        self._joint_state = msg

    def _cycle_result_cb(self, msg):
        """selection.py `_log_attempt` 훅이 보낸 사이클 결과 → RESULT/grasp_result 로 변환."""
        try:
            rec = json.loads(msg.data)
        except (json.JSONDecodeError, TypeError):
            return

        # cycle_id 는 여기(selection.py `_cycle_seq`)서만 발급된다 — 브릿지는
        # 절대 스스로 짓지 않고, 타이머 메시지용 "가장 최근 관측값"만 echo 한다.
        cycle_id = rec.get('cycle_id')
        if cycle_id is not None:
            self._last_cycle_id = cycle_id

        success = bool(rec.get('success'))
        fail_code, retry_suggested = (None, None)
        if not success:
            fail_code, retry_suggested = protocol.map_fail_reason(rec.get('reason'))
            if fail_code == 'UNKNOWN':
                self.get_logger().warn(
                    f'[desktop_bridge] 매핑 안 된 fail_reason "{rec.get("reason")}" '
                    f'— protocol.FAIL_REASON_MAP 갱신 필요')
        metrics = rec.get('metrics') or {}

        # `.get()`(브래킷 접근 금지) — 수기 테스트 페이로드가 origin 을
        # 빠뜨려도 KeyError 로 rclpy 콜백이 죽지 않게 한다.
        origin = rec.get('origin')
        matched = None
        with self._pending_lock:
            pending = self._pending_pick
            if pending is not None and origin == 'DESKTOP':
                self._pending_pick = None
                matched = pending

        if matched is None:
            # DESKTOP 명령이 대기 중이 아니었거나(로봇 자체선택 사이클), origin
            # 이 'DESKTOP' 이 아닌 결과 — 텔레메트리로만 흘려보내고 대기 슬롯은
            # (있다면) 그대로 둔다. 여기서 소비해 버리면 진짜 매칭돼야 할
            # DESKTOP 결과를 놓친다 — 이게 오상관 방지의 핵심 규칙.
            self._send(self._envelope('grasp_result', {
                'bolt_id': rec.get('bolt_id'), 'success': success,
                'fail_reason': fail_code if not success else None,
                'bolt_rise_m': metrics.get('bolt_rise_m'),
                'gripper_width_m': metrics.get('gripper_width_m'),
            }))
            return

        # matched['id'] 는 REST `/api/v1/pick_bolt` 응답의 `id` 와 동일한 값 —
        # 데스크톱은 그 id 를 이 RESULT 의 `corr` 로 매칭한다.
        self._send(self._envelope('RESULT', {
            'success': success,
            'fail_reason': fail_code if not success else None,
            'retry_suggested': retry_suggested if not success else None,
            'retries': rec.get('retries'),
            'cycle_id': cycle_id,
            'bolt_id': matched.get('bolt_id'),        # 데스크톱이 원래 보낸 id
            'matched_bolt_id': rec.get('bolt_id'),    # 로봇이 내부적으로 매칭한 id
            'dur_s': rec.get('dur'),
        }, corr=matched['id']))

    def _tick_arm_state(self):
        if self._joint_state is None:
            self._note_arm_state_stall('NO_JOINT_STATE', '/joint_states 미수신')
            return
        lookup = dict(zip(self._joint_state.name, self._joint_state.position))
        if not all(j in lookup for j in ARM_JOINTS):
            self._note_arm_state_stall('NO_JOINT_STATE', '/joint_states 에 팔 관절 일부 누락')
            return
        q = [float(lookup[j]) for j in ARM_JOINTS]
        moving = self._prev_q is not None and any(
            abs(a - b) > 1e-4 for a, b in zip(q, self._prev_q))
        self._prev_q = q

        tcp = None
        tcp_quat = None
        try:
            tr = self._tf_buf.lookup_transform(REFERENCE_FRAME, TCP_LINK, rclpy.time.Time())
            t = tr.transform.translation
            r = tr.transform.rotation
            tcp = [t.x, t.y, t.z]
            tcp_quat = [r.x, r.y, r.z, r.w]
        except (LookupException, ConnectivityException, ExtrapolationException):
            pass
        if tcp is None:
            # TCP 프레임 미도착 — 다음 tick 재시도(유실 허용, §2B 정책). 다만
            # 계속 실패하면 "로봇 유휴"와 구분 안 되는 무음이 되므로 스톨로 집계.
            self._note_arm_state_stall('TF_STALE', f'tf lookup 실패 ({REFERENCE_FRAME}→{TCP_LINK})')
            return

        joint_margin_vals = protocol.joint_margins(lookup, JOINT_LIMITS, ARM_JOINTS)
        if any(v is None for v in joint_margin_vals):
            # 부록F 는 joint_margin 을 `f32[7]` 로 스펙한다 — null 이 섞인 배열을
            # 보내면 계약 위반이라 데스크톱 파서가 깨진다. 프레임을 통째로 거르고
            # 스톨로 집계해 원인이 드러나게 한다. (스톨 카운터 리셋보다 위에 둬야
            # 연속 실패가 실제로 누적돼 ≥3회 ALERT 까지 간다.)
            self._note_arm_state_stall(
                'JOINT_LIMITS_INCOMPLETE', 'JOINT_LIMITS 에 없는 팔 관절이 있어 joint_margin 미완성')
            return

        # 스톨에서 회복 — 다음에 다시 끊기면 새로 3회부터 센다(반복 알림 방지는
        # _arm_state_stall_alerted 가 already-alerted 상태일 때만 억제하는 걸로 충분).
        self._arm_state_stall_count = 0
        self._arm_state_stall_alerted = False

        finger = lookup.get(GRIPPER_JOINT)
        args = {
            'q': q, 'tcp': tcp, 'tcp_quat': tcp_quat,
            'gripper_width': (2.0 * finger) if finger is not None else None,
            'joint_margin': joint_margin_vals,
            'moving': moving,
            'last_cycle_id': self._last_cycle_id,   # heartbeat 와 동일 정의(§2B)
        }
        self._send(self._envelope('arm_state', args))

    def _note_arm_state_stall(self, code, detail):
        """arm_state 가 못 나가는 상황이 반복되면(≥3회) 딱 1회 ALERT.

        이전엔 완전히 무음이라 "로봇 유휴"와 "링크/TF 고장"이 구분 안 됐다
        (§4 원칙 "침묵은 버그다"). 회복되면 _tick_arm_state 가 플래그를 리셋해
        다음 스톨 때 다시 알릴 수 있게 한다.
        """
        self._arm_state_stall_count += 1
        if self._arm_state_stall_count >= 3 and not self._arm_state_stall_alerted:
            self._arm_state_stall_alerted = True
            self._send(self._envelope('ALERT', {
                'severity': 'warn', 'code': code, 'msg': detail,
                'context': {'consecutive_ticks': self._arm_state_stall_count},
            }))

    def _tick_heartbeat(self):
        with self._estop_lock:
            estop = self._estop
        self._send(self._envelope('heartbeat', {
            'state': 'SAFE_STOP' if estop else 'IDLE',
            'moveit_ok': self._joint_state is not None,
            # 사이클에 종속된 값이 아니라 "가장 최근에 관측된 cycle_id"다(nullable
            # — 아직 사이클이 한 번도 안 돌았으면 None). 실시간 진행 중인 사이클을
            # 뜻하지 않는다 — heartbeat 는 1Hz 타이머고 cycle_id 는 selection.py
            # 가 사이클마다 발급하므로 둘은 서로 다른 시계다.
            'last_cycle_id': self._last_cycle_id,
        }))

    def _status_args(self):
        with self._estop_lock:
            estop = self._estop
        return {
            'estop': estop,
            'connected_clients': self._connected,
            'joint_state_recv': self._joint_state is not None,
            'cmd_state': self._cmd_state,
        }

    def _status_envelope(self, corr=None):
        return self._envelope('STATUS', self._status_args(), corr=corr)

    # =========================================================
    # 봉투 / 발신 헬퍼 (WS 텔레메트리 전용 — REST 응답은 이 형식을 안 씀)
    # =========================================================
    def _envelope(self, mtype, args, corr=None, prio='NORMAL'):
        # seq 는 rclpy 스레드(타이머 콜백)와 서버 스레드(REST 핸들러) 양쪽에서
        # 증가되므로 락으로 보호한다 — 안 그러면 두 스레드의 read-modify-write
        # 가 겹쳐 중복/누락된 seq 가 나갈 수 있다(§3 "seq 단조증가로 순서/유실
        # 검출"이 근거로 삼는 바로 그 보장이 깨진다).
        with self._seq_lock:
            self._seq += 1
            seq = self._seq
        return {
            'v': PROTOCOL_VERSION, 'type': mtype,
            'id': f'{mtype.lower()}-{uuid.uuid4().hex[:8]}',
            'corr': corr, 'prio': prio, 'seq': seq,
            't_wall': _now_ns(), 't_sim': self.get_clock().now().nanoseconds,
            'use_sim_time': self.get_parameter('use_sim_time').value, 'args': args,
        }

    def _send(self, envelope):
        """rclpy 스레드에서 호출 — 서버 스레드의 이벤트루프로 넘긴다."""
        loop = self._loop
        if loop is None:
            # 서버 스레드가 아직 루프를 못 만든 기동 직후 — 텔레메트리는 유실 허용
            # (§2B)이라 조용히 버린다. 어차피 붙은 WS 클라이언트도 아직 없다.
            return
        loop.call_soon_threadsafe(self._outbox_put_nowait_safe, json.dumps(envelope))

    def _outbox_put_nowait_safe(self, text):
        """서버 스레드(이벤트루프) 위에서 실행 — 큐가 가득 차면 버리고 알린다.

        무한 큐로 두면 WS 클라이언트가 하나도 없거나 전부 느릴 때 20Hz arm_state 가
        메모리를 무한정 먹는다. 텔레메트리는 유실 허용이므로 드롭이 정답이다.
        """
        try:
            self._outbox.put_nowait(text)
        except asyncio.QueueFull:
            self.get_logger().warn('[desktop_bridge] outbox full, dropping telemetry frame')


def main(args=None):
    rclpy.init(args=args)
    node = DesktopBridgeNode()
    try:
        rclpy.spin(node)
    except (KeyboardInterrupt, rclpy.executors.ExternalShutdownException):
        # 바인드 실패 시 _run_server 는 os._exit(1) 로 즉시 종료하므로 이 분기를
        # 안 탄다 — 이건 정상적인 Ctrl+C/외부 종료 신호 처리 경로다.
        pass
    finally:
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == '__main__':
    main()
