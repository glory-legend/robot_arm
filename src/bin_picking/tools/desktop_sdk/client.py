# -*- coding: utf-8 -*-
"""BinPickingClient — ROS 무의존 Python SDK.

desktop_bridge (REST+WS 하이브리드, v3) 와 통신하는 클라이언트 라이브러리.
데스크톱 팀이 ROS2/rclpy 없이 ``pip install websockets`` 만으로 쓸 수 있다.

사용법::

    import asyncio
    from desktop_sdk import BinPickingClient

    async def main():
        async with BinPickingClient('http://localhost:8765', token='abc') as c:
            status = await c.get_status()
            print(status.robot_phase)

            result = await c.pick_bolt(
                bolt_id='b-001', rank=1, stamp=0,
                position=[0.3, 0.0, 0.05],
                orientation=[0.0, 0.0, 0.0, 1.0],
            )
            print(result.success, result.fail_reason)

    asyncio.run(main())
"""
from __future__ import annotations

import asyncio
import itertools
import json
import logging
import time
from typing import Any, AsyncIterator, Callable

import websockets
import websockets.exceptions

from .exceptions import (
    AuthenticationError,
    BinPickingError,
    CommandRejectedError,
    ConnectionError,
    TimeoutError,
)
from .models import (
    Alert,
    ArmState,
    Envelope,
    GraspResult,
    Heartbeat,
    PickResult,
    Status,
)

logger = logging.getLogger(__name__)

_id_counter = itertools.count(1)

_WS_INVALID_STATUS = tuple(
    t for t in (
        getattr(websockets.exceptions, 'InvalidStatus', None),
        getattr(websockets.exceptions, 'InvalidStatusCode', None),
    ) if t is not None
)


def _to_ws_url(http_url: str) -> str:
    if http_url.startswith('https://'):
        return 'wss://' + http_url[len('https://'):]
    if http_url.startswith('http://'):
        return 'ws://' + http_url[len('http://'):]
    raise ValueError(f'URL must start with http(s)://: {http_url!r}')


class BinPickingClient:
    """desktop_bridge REST+WS 클라이언트.

    Parameters
    ----------
    base_url : str
        브릿지 HTTP URL (예: ``http://localhost:8765``).
    token : str
        Bearer 인증 토큰.
    frame : str
        좌표 프레임 (기본 ``'fr3_link0'``).
    reconnect_interval : float
        WS 자동 재연결 간격(초).
    result_timeout : float
        ``pick_bolt()`` RESULT 대기 제한(초).
    """

    def __init__(
        self,
        base_url: str,
        token: str,
        *,
        frame: str = 'fr3_link0',
        reconnect_interval: float = 2.0,
        result_timeout: float = 30.0,
    ):
        self._base_url = base_url.rstrip('/')
        self._token = token
        self._frame = frame
        self._reconnect_interval = reconnect_interval
        self._result_timeout = result_timeout

        self._ws: websockets.WebSocketClientProtocol | None = None
        self._ws_task: asyncio.Task | None = None
        self._closed = False

        self._listeners: dict[str, list[Callable]] = {}
        self._pending_results: dict[str, asyncio.Future[PickResult]] = {}
        self._last_status: Status | None = None
        self._last_heartbeat: Heartbeat | None = None

    # ------ context manager ------

    async def __aenter__(self) -> BinPickingClient:
        await self.connect()
        return self

    async def __aexit__(self, *exc: Any) -> None:
        await self.close()

    # ------ lifecycle ------

    async def connect(self) -> None:
        self._closed = False
        self._ws_task = asyncio.create_task(self._ws_loop())

    async def close(self) -> None:
        self._closed = True
        if self._ws_task and not self._ws_task.done():
            self._ws_task.cancel()
            try:
                await self._ws_task
            except asyncio.CancelledError:
                pass
        if self._ws:
            await self._ws.close()
            self._ws = None
        for fut in self._pending_results.values():
            if not fut.done():
                fut.cancel()
        self._pending_results.clear()

    # ------ REST commands ------

    async def _rest(self, method: str, path: str, body: dict | None = None) -> dict:
        import urllib.request
        import urllib.error

        url = f'{self._base_url}{path}'
        data = json.dumps(body).encode() if body is not None else None
        req = urllib.request.Request(url, data=data, method=method)
        req.add_header('Authorization', f'Bearer {self._token}')
        if data is not None:
            req.add_header('Content-Type', 'application/json')

        loop = asyncio.get_running_loop()
        try:
            def _call():
                try:
                    with urllib.request.urlopen(req, timeout=10) as resp:
                        return resp.status, json.loads(resp.read().decode())
                except urllib.error.HTTPError as exc:
                    try:
                        payload = json.loads(exc.read().decode())
                    except (json.JSONDecodeError, ValueError):
                        payload = {'error': str(exc)}
                    return exc.code, payload

            status, payload = await loop.run_in_executor(None, _call)
        except Exception as exc:
            raise ConnectionError(f'REST call failed: {exc}') from exc

        if status == 401:
            raise AuthenticationError('invalid or missing Bearer token')
        return payload

    async def get_status(self) -> Status:
        data = await self._rest('GET', '/api/v1/status')
        return Status.from_args(data)

    async def estop(self) -> dict:
        return await self._rest('POST', '/api/v1/estop')

    async def command(self, cmd_type: str, args: dict[str, Any] | None = None) -> dict:
        body: dict[str, Any] = {'type': cmd_type}
        if args:
            body['args'] = args
        resp = await self._rest('POST', '/api/v1/command', body)
        if not resp.get('accepted', True):
            raise CommandRejectedError(resp.get('errors'))
        return resp

    async def pick_bolt(
        self,
        bolt_id: str,
        rank: int,
        stamp: int,
        position: list[float],
        orientation: list[float],
        *,
        frame: str | None = None,
        deadline: int | None = None,
        timeout: float | None = None,
    ) -> PickResult:
        """PICK_BOLT 발행 + RESULT 대기.

        REST 로 ACK 를 받고, WS 텔레메트리에서 같은 correlation id 를 가진
        RESULT 를 ``timeout`` 초 내로 대기한다.
        """
        body: dict[str, Any] = {
            'bolt_id': bolt_id,
            'rank': rank,
            'stamp': stamp,
            'frame': frame or self._frame,
            'pose': {
                'position': position,
                'orientation': orientation,
            },
        }
        if deadline is not None:
            body['deadline'] = deadline

        resp = await self._rest('POST', '/api/v1/pick_bolt', body)
        if not resp.get('accepted', True):
            raise CommandRejectedError(resp.get('errors'))

        corr_id = resp.get('id')
        if not corr_id:
            raise BinPickingError('server did not return correlation id')

        loop = asyncio.get_running_loop()
        fut: asyncio.Future[PickResult] = loop.create_future()
        self._pending_results[corr_id] = fut

        wait = timeout if timeout is not None else self._result_timeout
        try:
            return await asyncio.wait_for(fut, timeout=wait)
        except asyncio.TimeoutError:
            raise TimeoutError(f'RESULT for {corr_id} not received within {wait}s')
        finally:
            self._pending_results.pop(corr_id, None)

    # convenience wrappers

    async def set_speed(self, scale: float) -> dict:
        return await self.command('SET_SPEED', {'scale': scale})

    async def pause(self) -> dict:
        return await self.command('PAUSE')

    async def resume(self) -> dict:
        return await self.command('RESUME')

    async def go_home(self, speed: float | None = None) -> dict:
        args = {'speed': speed} if speed is not None else {}
        return await self.command('GO_HOME', args or None)

    async def blacklist_add(self, bolt_id: str) -> dict:
        return await self.command('BLACKLIST_ADD', {'bolt_id': bolt_id})

    async def blacklist_remove(self, bolt_id: str) -> dict:
        return await self.command('BLACKLIST_REMOVE', {'bolt_id': bolt_id})

    async def reset(self) -> dict:
        return await self.command('RESET', {'confirm': True})

    # ------ WS telemetry ------

    def on(self, event: str, callback: Callable) -> None:
        """텔레메트리 이벤트 리스너 등록.

        event: ``'arm_state'``, ``'heartbeat'``, ``'RESULT'``,
        ``'grasp_result'``, ``'alert'``, ``'STATUS'``, ``'*'`` (전체).
        """
        self._listeners.setdefault(event, []).append(callback)

    def off(self, event: str, callback: Callable) -> None:
        cbs = self._listeners.get(event, [])
        if callback in cbs:
            cbs.remove(callback)

    async def telemetry_stream(self) -> AsyncIterator[Envelope]:
        """WS 텔레메트리를 Envelope 로 yield 하는 async generator."""
        ws_url = _to_ws_url(self._base_url) + f'/ws/telemetry?token={self._token}'
        async for ws in websockets.connect(ws_url):
            try:
                async for raw in ws:
                    env = Envelope.from_dict(json.loads(raw))
                    yield env
            except websockets.exceptions.ConnectionClosed:
                if self._closed:
                    return
                logger.warning('WS disconnected, reconnecting in %.1fs', self._reconnect_interval)
                await asyncio.sleep(self._reconnect_interval)

    async def _ws_loop(self) -> None:
        while not self._closed:
            ws_url = _to_ws_url(self._base_url) + f'/ws/telemetry?token={self._token}'
            try:
                async with websockets.connect(ws_url) as ws:
                    self._ws = ws
                    logger.info('WS connected to %s', ws_url)
                    async for raw in ws:
                        try:
                            data = json.loads(raw)
                        except json.JSONDecodeError:
                            continue
                        env = Envelope.from_dict(data)
                        self._dispatch(env)
            except _WS_INVALID_STATUS as exc:
                status_code = getattr(exc, 'status_code', None) or getattr(exc, 'status', None)
                if status_code == 401:
                    logger.error('WS authentication failed (401)')
                    raise AuthenticationError('WS token rejected') from exc
                logger.warning('WS error (status %s), retrying', status_code)
            except (OSError, websockets.exceptions.ConnectionClosed):
                if self._closed:
                    return
                logger.warning('WS disconnected, reconnecting in %.1fs', self._reconnect_interval)
            except asyncio.CancelledError:
                return

            if not self._closed:
                await asyncio.sleep(self._reconnect_interval)

        self._ws = None

    def _dispatch(self, env: Envelope) -> None:
        mtype = env.type

        if mtype == 'STATUS':
            status = Status.from_args(env.args)
            self._last_status = status
            self._fire('STATUS', status)
        elif mtype == 'arm_state':
            self._fire('arm_state', ArmState.from_args(env.args))
        elif mtype == 'heartbeat':
            hb = Heartbeat.from_args(env.args)
            self._last_heartbeat = hb
            self._fire('heartbeat', hb)
        elif mtype == 'RESULT':
            result = PickResult.from_envelope(env)
            self._fire('RESULT', result)
            if env.corr and env.corr in self._pending_results:
                fut = self._pending_results.pop(env.corr)
                if not fut.done():
                    fut.set_result(result)
        elif mtype == 'grasp_result':
            self._fire('grasp_result', GraspResult.from_args(env.args))
        elif mtype == 'alert':
            self._fire('alert', Alert.from_args(env.args))

        self._fire('*', env)

    def _fire(self, event: str, data: Any) -> None:
        for cb in self._listeners.get(event, []):
            try:
                result = cb(data)
                if asyncio.iscoroutine(result):
                    asyncio.ensure_future(result)
            except Exception:
                logger.exception('listener error for event %r', event)

    # ------ properties ------

    @property
    def last_status(self) -> Status | None:
        return self._last_status

    @property
    def last_heartbeat(self) -> Heartbeat | None:
        return self._last_heartbeat

    @property
    def connected(self) -> bool:
        return self._ws is not None and self._ws.open
