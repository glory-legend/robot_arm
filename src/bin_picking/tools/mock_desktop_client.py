#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""데스크톱앱 대역 — 통신 검증용 목(mock) 클라이언트 (REST+WS 하이브리드, v3).

진짜 데스크톱앱은 별도 팀이 만든다. 이 스크립트는 그때까지 로봇쪽
desktop_bridge 노드(`ros2 run bin_picking desktop_bridge`)가 문서
(`docs/desktop_protocol.md`) 그대로 동작하는지 확인하는 용도다.

ROS 의존성이 전혀 없다 — 이게 핵심이다. `pip install -r tools/requirements.txt` 만으로
아무 컴퓨터에서나 이 스크립트를 돌려 브릿지에 붙을 수 있다(데스크톱 개발자가
ROS2/roslib를 설치할 필요가 없다는 게 이 통신 방식을 고른 이유, §4 참고).
REST 호출은 표준 라이브러리 `urllib` 만 쓴다 — 새 의존성을 안 늘린다.

명령은 REST, 텔레메트리(arm_state/heartbeat/RESULT/grasp_result/ALERT)는
WS 스트림 전용이다(v3, 2026-08-04 — v2 까지는 명령도 WS 로 받았다. 이유는
desktop_protocol.md §4). 인증은 Bearer 토큰 — 브릿지를 토큰 없이 띄우면
시작 로그에 임의 생성된 토큰이 찍히니 그 값을 `--token` 또는
`BIN_PICKING_API_TOKEN` 환경변수로 넘기면 된다.

사용법:
    python3 mock_desktop_client.py --token <TOKEN>                    # 데모
    python3 mock_desktop_client.py --url http://192.168.0.10:8765 --token <TOKEN>
    python3 mock_desktop_client.py --token <TOKEN> --assert           # 자동검증 모드
    BIN_PICKING_API_TOKEN=<TOKEN> python3 mock_desktop_client.py --assert

`--assert` 모드는 Gazebo/MoveIt 없이 `desktop_bridge` 단독 기동만으로 확인 가능한
것만 검증한다 — REST 인증(401), 필수필드 검증(REST 응답에서 200+accepted:false),
정상 PICK_BOLT(REST 200+accepted:true), WS 인증(핸드셰이크 거부), STATUS 스냅샷,
`last_cycle_id`(≠`cycle_id`) 필드명, `joint_margin` 배열 shape, 동시 요청 하 WS
`seq` 중복 없음(REST 스레드 ↔ rclpy 타이머 스레드 동시성 검증). 실패가 있으면
종료코드 1.
"""
import argparse
import asyncio
import itertools
import json
import os
import sys
import time
import urllib.error
import urllib.request

import websockets
import websockets.exceptions

_id_seq = itertools.count(1)

_ws_status_exceptions = tuple(
    exc_type for exc_type in (
        getattr(websockets.exceptions, 'InvalidStatus', None),
        getattr(websockets.exceptions, 'InvalidStatusCode', None),
    ) if exc_type is not None
)


def _to_ws_url(http_url):
    if http_url.startswith('https://'):
        return 'wss://' + http_url[len('https://'):]
    if http_url.startswith('http://'):
        return 'ws://' + http_url[len('http://'):]
    raise ValueError(f'--url 은 http(s):// 로 시작해야 합니다: {http_url!r}')


def _rest_call_sync(base_url, path, token, method='GET', body=None):
    """동기 HTTP 호출(urllib, 표준 라이브러리만 사용) — run_in_executor 로 감싸 쓴다."""
    url = f'{base_url}{path}'
    data = json.dumps(body).encode('utf-8') if body is not None else None
    req = urllib.request.Request(url, data=data, method=method)
    req.add_header('Authorization', f'Bearer {token}')
    if data is not None:
        req.add_header('Content-Type', 'application/json')
    try:
        with urllib.request.urlopen(req, timeout=5) as resp:
            return resp.status, json.loads(resp.read().decode('utf-8'))
    except urllib.error.HTTPError as exc:
        try:
            payload = json.loads(exc.read().decode('utf-8'))
        except (json.JSONDecodeError, ValueError):
            payload = {'error': str(exc)}
        return exc.code, payload


async def rest_call(base_url, path, token, method='GET', body=None):
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(
        None, _rest_call_sync, base_url, path, token, method, body)


async def _print_incoming(ws):
    """연결이 살아있는 동안 들어오는 모든 메시지를 계속 출력(스트림 관찰용)."""
    async for raw in ws:
        msg = json.loads(raw)
        tag = msg['type']
        if tag == 'arm_state':
            q = msg['args'].get('q')
            q0 = f'{q[0]:+.3f}' if q else 'N/A'
            print(f'  <- arm_state  q0={q0} tcp={msg["args"].get("tcp")}')
        elif tag == 'heartbeat':
            print(f'  <- heartbeat  state={msg["args"].get("state")}')
        else:
            print(f'  <- {tag}  corr={msg.get("corr")}  {msg.get("args")}')


async def main(http_url, token):
    ws_url = f'{_to_ws_url(http_url)}/ws/telemetry?token={token}'
    print(f'[mock desktop] WS 접속: {ws_url}')
    async with websockets.connect(ws_url) as ws:
        print('[mock desktop] 연결됨. 첫 프레임은 재연결 스냅샷(STATUS)이어야 함:')
        print(' ', json.loads(await ws.recv()))
        watcher = asyncio.create_task(_print_incoming(ws))

        status, body = await rest_call(http_url, '/api/v1/status', token)
        print(f'[mock desktop] GET /api/v1/status -> {status} {body}')

        pick_args = {
            'bolt_id': 'b_demo', 'rank': 1, 'frame': 'fr3_link0',
            'stamp': time.time_ns(),
            'pose': {'position': [0.42, -0.02, 0.19],
                     'orientation': [0.0, 0.707, 0.0, 0.707]},
        }
        status, body = await rest_call(http_url, '/api/v1/pick_bolt', token, 'POST', pick_args)
        print(f'[mock desktop] POST /api/v1/pick_bolt -> {status} {body} '
              f'— RESULT 는 WS 스트림에서 corr={body.get("id")} 로 옴')

        print('[mock desktop] 10초간 텔레메트리 관찰 (Ctrl+C 로 종료)...')
        await asyncio.sleep(10)
        watcher.cancel()


async def run_assertions(http_url, token):
    """단독 기동(Gazebo 불필요)만으로 확인 가능한 것만 검증."""
    failures = []

    def check(name, cond):
        print(f'[{"PASS" if cond else "FAIL"}] {name}')
        if not cond:
            failures.append(name)

    print(f'[assert] {http_url} 접속...')

    # 0) REST 인증 — 토큰 없음/틀림은 401.
    status, _ = await rest_call(http_url, '/api/v1/status', 'wrong-token')
    check('REST: 틀린 토큰 -> 401', status == 401)

    # 1) WS 인증 — 틀린 토큰은 핸드셰이크 자체가 거부됨(HTTP 401).
    try:
        async with websockets.connect(f'{_to_ws_url(http_url)}/ws/telemetry?token=wrong'):
            check('WS: 틀린 토큰 -> 핸드셰이크 거부', False)
    except _ws_status_exceptions as exc:
        status = getattr(getattr(exc, 'response', None), 'status_code', None)
        if status is None:
            status = getattr(exc, 'status_code', None)
        check('WS: 틀린 토큰 -> 핸드셰이크 거부(401)', status == 401)

    ws_url = f'{_to_ws_url(http_url)}/ws/telemetry?token={token}'
    async with websockets.connect(ws_url) as ws:
        snapshot = json.loads(await ws.recv())
        check('재연결 즉시 스냅샷은 STATUS', snapshot.get('type') == 'STATUS')
        check('PROTOCOL_VERSION == 3', snapshot.get('v') == 3)

        # 2) REST: 필수 필드 누락 PICK_BOLT -> HTTP 200 + {accepted:false, errors:[...]}
        status, body = await rest_call(http_url, '/api/v1/pick_bolt', token, 'POST', {
            'pose': {'position': [0.0, 0.0, 0.0], 'orientation': [0.0, 0.0, 0.0, 1.0]}})
        check('REST: 필수필드 누락 PICK_BOLT -> HTTP 200', status == 200)
        check('accepted=false', body.get('accepted') is False)
        errors = body.get('errors') or []
        check('errors 에 bolt_id 명시', any('bolt_id' in e for e in errors))
        check('errors 에 rank 명시', any('rank' in e for e in errors))
        check('errors 에 stamp 명시', any('stamp' in e for e in errors))

        # 3) REST: 정상 PICK_BOLT -> HTTP 200 + {accepted:true, id:...}
        #    (id 값이 정수형(0 등) 좌표를 포함해도 브릿지가 안 죽는지도 같이 확인 —
        #    JSON 은 int/float 구분이 없어 값이 정확히 0 이면 int 로 파싱되는데,
        #    rclpy 바인딩은 float64 필드에 int 가 들어오면 과거 실측으로 프로세스
        #    전체가 abort 된 적이 있다. 이 케이스를 일부러 넣는다.)
        status, body = await rest_call(http_url, '/api/v1/pick_bolt', token, 'POST', {
            'bolt_id': 'b_assert', 'rank': 1, 'frame': 'fr3_link0',
            'stamp': time.time_ns(),
            'pose': {'position': [0.4, 0, 0.2],
                     'orientation': [0, 0.707, 0, 0.707]},
        })
        check('REST: 정상 PICK_BOLT(int 좌표 포함) -> HTTP 200', status == 200)
        check('accepted=true', body.get('accepted') is True)
        check('응답에 상관관계 id 포함', isinstance(body.get('id'), str) and body['id'])

        # 4) REST: 알 수 없는 명령 타입 -> accepted:false (범용 /api/v1/command)
        status, body = await rest_call(http_url, '/api/v1/command', token, 'POST',
                                        {'type': 'BOGUS'})
        check('REST: 알 수 없는 명령 -> accepted=false', body.get('accepted') is False)

        # 5) REST: 정상 ACK-only 명령 -> accepted:true, GET_STATUS 에 반영
        status, body = await rest_call(http_url, '/api/v1/command', token, 'POST',
                                        {'type': 'SET_SPEED', 'args': {'scale': 0.5}})
        check('REST: SET_SPEED -> accepted=true', body.get('accepted') is True)
        _, status_body = await rest_call(http_url, '/api/v1/status', token)
        check('GET_STATUS.cmd_state 에 SET_SPEED 반영',
              status_body.get('cmd_state', {}).get('SET_SPEED') == {'scale': 0.5})

        # 6) 텔레메트리 관찰: heartbeat 는 last_cycle_id(≠cycle_id), arm_state
        #    가 오면 joint_margin 이 f32[7] 리스트인지.
        saw_heartbeat = False
        saw_arm_state = False
        seen_seqs = []
        deadline = time.time() + 3.0
        while time.time() < deadline:
            try:
                raw = await asyncio.wait_for(ws.recv(), timeout=max(0.05, deadline - time.time()))
            except asyncio.TimeoutError:
                break
            msg = json.loads(raw)
            seen_seqs.append(msg.get('seq'))
            if msg.get('type') == 'heartbeat':
                saw_heartbeat = True
                check('heartbeat.args 에 last_cycle_id 존재', 'last_cycle_id' in msg['args'])
                check('heartbeat.args 에 cycle_id 는 없음(last_cycle_id 로 대체됨)',
                      'cycle_id' not in msg['args'])
            elif msg.get('type') == 'arm_state':
                saw_arm_state = True
                jm = msg['args'].get('joint_margin')
                check('arm_state.joint_margin 은 7개 원소 리스트(f32[7], 스칼라 아님)',
                      isinstance(jm, list) and len(jm) == 7)
        check('heartbeat 최소 1회 수신(1Hz 타이머)', saw_heartbeat)
        if not saw_arm_state:
            print('[SKIP] arm_state 미수신 — Gazebo 없이 단독 실행 시 정상'
                  '(/joint_states 발행자가 없어 검증 불가, 풀스택에서 확인)')

        # 7) 동시성: REST 스레드(스테일 PICK_BOLT -> ALERT)와 rclpy 타이머 스레드
        #    (heartbeat/arm_state)가 동시에 `_send()`/`_envelope()` 를 호출해도
        #    `seq` 가 중복 없이 나오는지(§3 "seq 단조증가" 근거인 `_seq_lock` 검증).
        stale_pick = {
            'bolt_id': 'b_stale', 'rank': 1, 'frame': 'fr3_link0',
            'stamp': 1, 'deadline': 1,   # 이미 지난 deadline -> ALERT 트리거
            'pose': {'position': [0.4, 0.0, 0.2],
                     'orientation': [0.0, 0.707, 0.0, 0.707]},
        }
        await asyncio.gather(*(
            rest_call(http_url, '/api/v1/pick_bolt', token, 'POST', stale_pick)
            for _ in range(20)))
        seen_seqs = []
        end = time.time() + 2.0
        while time.time() < end:
            try:
                raw = await asyncio.wait_for(ws.recv(), timeout=max(0.05, end - time.time()))
            except asyncio.TimeoutError:
                break
            seen_seqs.append(json.loads(raw).get('seq'))
        check('동시 요청 하 WS seq 중복 없음(REST↔타이머 스레드 락 검증)',
              len(seen_seqs) > 0 and len(seen_seqs) == len(set(seen_seqs)))

    print()
    if failures:
        print(f'{len(failures)}개 실패: {failures}')
        sys.exit(1)
    print('전부 통과')


def _parse_args():
    p = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument('--url', default='http://127.0.0.1:8765',
                    help='desktop_bridge REST 베이스 URL (기본: http://127.0.0.1:8765)')
    p.add_argument('--token', default=os.environ.get('BIN_PICKING_API_TOKEN'),
                    help='Bearer 토큰. 안 주면 BIN_PICKING_API_TOKEN 환경변수 사용. '
                         '브릿지를 api_token 파라미터 없이 띄웠다면 시작 로그에 찍힌 '
                         '임의 생성 토큰을 쓰세요.')
    p.add_argument('--assert', dest='assert_mode', action='store_true',
                    help='자동검증 모드(Tier 1 — Gazebo 불필요)')
    return p.parse_args()


if __name__ == '__main__':
    ns = _parse_args()
    if not ns.token:
        print('오류: --token 이 필요합니다(또는 BIN_PICKING_API_TOKEN 환경변수). '
              '브릿지 시작 로그에서 API_TOKEN 값을 확인하세요.', file=sys.stderr)
        sys.exit(2)
    try:
        if ns.assert_mode:
            asyncio.run(run_assertions(ns.url, ns.token))
        else:
            asyncio.run(main(ns.url, ns.token))
    except KeyboardInterrupt:
        pass
