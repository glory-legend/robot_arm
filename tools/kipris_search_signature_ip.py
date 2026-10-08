#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""KIPRIS 국내 선행조사 — 서명 IP/기술조각 브레인스토밍 후보 (S1·S2·T1·T2).

`docs/vision_desktop_robotarm_patent_brainstorm_2026-09-10.md` 후보의 국내 개별개시
여부를 확인한다. 사용자 방침이 '국내 특허 타깃'이므로 국내 선행 부재가 1차 결정변수.

  S1 마스터 핸드셰이크(인식-랭킹/실행-도달성 분리 + 거부 되먹임 재랭킹)
  S2 실패사유 어휘 구동 차등 재행동 정책
  T1 거부-히트맵(도달성 대리학습)
  T2 비힘센서 파지-무게 검증(관절 편차)

실행:  python3 tools/kipris_search_signature_ip.py   # → tools/kipris_results_signature_ip.md
주의: 예비검색. 청구항 전체요소 대조·법적상태는 변리사가 KIPRIS 원부로 확인.
"""
import os
import time
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET

BASE = 'http://plus.kipris.or.kr'
SERVICE_PATH = '/kipo-api/kipi/patUtiModInfoSearchSevice'
OP_ADV = '/getAdvancedSearch'
NUM_ROWS = 100
PAGE_NO = 1
SLEEP_SEC = 0.5
HERE = os.path.dirname(os.path.abspath(__file__))
RESULT_MD = os.path.join(HERE, 'kipris_results_signature_ip.md')

# (라벨, 필드, 검색어, IPC)  — * = AND / + = OR / ! = 제외
QUERIES = [
    # ── S1 마스터 핸드셰이크 (인식/실행 주체 분리 + 거부 되먹임) ──
    ('S1-초록-도달불가차순위', 'astrtCont', '도달*불가*다음*파지', None),
    ('S1-초록-거부재선택', 'astrtCont', '거부*재선택*로봇*비전', None),
    ('S1-초록-랭킹도달성분리', 'astrtCont', '순위*도달*파지*비전', None),
    ('S1-청구-거부되먹임', 'claimScope', '도달*거부*재선택', None),
    ('S1-초록-인식실행분리', 'astrtCont', '인식*실행*분리*로봇', None),
    # ── S2 실패사유 차등 재행동 ──
    ('S2-초록-실패사유정책', 'astrtCont', '파지*실패*원인*재시도', None),
    ('S2-초록-실패유형동작', 'astrtCont', '실패*유형*로봇*동작', None),
    ('S2-청구-실패분류재시도', 'claimScope', '실패*분류*재시도', None),
    # ── T1 거부-히트맵(도달성 대리학습) ──
    ('T1-초록-도달영역학습', 'astrtCont', '도달*영역*학습*로봇', None),
    ('T1-초록-작업공간거부누적', 'astrtCont', '작업공간*도달*맵', None),
    ('T1-청구-도달가능맵', 'claimScope', '도달*가능*맵*로봇', None),
    # ── T2 비힘센서 무게검증(관절 편차) ──
    ('T2-초록-관절편차무게', 'astrtCont', '관절*편차*무게', None),
    ('T2-초록-파지무게관절', 'astrtCont', '파지*무게*관절*추정', None),
    ('T2-초록-힘센서없이무게', 'astrtCont', '힘센서*없이*무게', None),
    ('T2-초록-리프트관절검증', 'astrtCont', '리프트*관절*파지*검증', None),
    ('T2-청구-관절토크무게', 'claimScope', '관절*토크*무게*추정', None),
    # ── 참고: 온라인 비딥 파지 랭커(폭넓게 붐빔 확인) ──
    ('REF-초록-온라인파지학습', 'astrtCont', '온라인*파지*학습*선택', None),
]

FIELDS = ['inventionTitle', 'applicantName', 'applicationNumber',
          'registerStatus', 'ipcNumber', 'astrtCont', 'registerNumber', 'openNumber']


def load_key():
    env = os.environ.get('KIPRIS_SERVICE_KEY', '').strip()
    if env:
        return env
    keyfile = os.path.join(HERE, '.kipris_key')
    if os.path.exists(keyfile):
        with open(keyfile, encoding='utf-8') as f:
            return f.readline().strip()
    return ''


def build_adv_url(field, value, key, ipc=None):
    params = {field: value, 'patent': 'true', 'utility': 'true',
              'numOfRows': NUM_ROWS, 'pageNo': PAGE_NO, 'ServiceKey': key}
    if ipc:
        params['ipcNumber'] = ipc
    return f'{BASE}{SERVICE_PATH}{OP_ADV}?' + urllib.parse.urlencode(params)


def fetch(url, timeout=25):
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'kipris-scan/2.0'})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return True, resp.read().decode('utf-8', errors='replace'), ''
    except Exception as exc:                       # noqa: BLE001
        return False, '', repr(exc)


def _first_text(node, tag):
    for el in node.iter(tag):
        if el.text and el.text.strip():
            return el.text.strip()
    return ''


def parse_items(xml_text):
    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError as exc:
        return f'XML 파싱 실패: {exc}', [], 0
    success = _first_text(root, 'successYN')
    total = _first_text(root, 'totalCount') or '0'
    status = f'successYN={success or "?"}'
    items = []
    for item in root.iter('item'):
        rec = {f: (item.findtext(f) or '').strip() for f in FIELDS}
        for f in FIELDS:
            if not rec[f]:
                rec[f] = _first_text(item, f)
        items.append(rec)
    try:
        total_n = int(total)
    except ValueError:
        total_n = len(items)
    return status, items, total_n


def google_link(rec):
    num = (rec.get('registerNumber') or rec.get('applicationNumber') or '').replace('-', '')
    return f'https://patents.google.com/?q=KR{num}&country=KR' if num else ''


def run_search(key):
    by_app = {}
    order = []
    per_query = []
    for label, field, value, ipc in QUERIES:
        url = build_adv_url(field, value, key, ipc)
        ok, body, err = fetch(url)
        if not ok:
            print(f'[{label}] {field}="{value}" → 실패: {err}')
            per_query.append((label, f'{field}:{value}', -1, 0))
            time.sleep(SLEEP_SEC)
            continue
        status, items, total = parse_items(body)
        per_query.append((label, f'{field}:{value}', total, len(items)))
        capped = ' ⚠캡초과' if total > len(items) else ''
        print(f'[{label}] {field}="{value}" → 총 {total}건(수신 {len(items)}){capped}')
        for rec in items:
            app = (rec.get('applicationNumber') or rec.get('registerNumber')
                   or rec.get('inventionTitle'))
            if not app:
                continue
            if app not in by_app:
                by_app[app] = (set(), rec)
                order.append(app)
            by_app[app][0].add(label)
        time.sleep(SLEEP_SEC)

    def sort_key(app):
        _labels, rec = by_app[app]
        reg = '등록' in (rec.get('registerStatus') or '')
        return (0 if reg else 1, rec.get('inventionTitle') or '')
    order.sort(key=sort_key)

    _write_md(order, by_app, per_query)
    print(f'\n총 {len(order)}건(중복 제거) — 상세는 {RESULT_MD}')
    for app in order[:15]:
        labels, rec = by_app[app]
        title = (rec.get('inventionTitle') or '(제목없음)')[:44]
        st = rec.get('registerStatus') or '?'
        print(f'  - [{st}] {title}  ({rec.get("applicantName") or "?"}) [{",".join(sorted(labels))}]')


def _row(app, by_app):
    labels, rec = by_app[app]
    title = (rec.get('inventionTitle') or '').replace('|', '/')
    appl = (rec.get('applicantName') or '').replace('|', '/')
    st = rec.get('registerStatus') or ''
    ipc = (rec.get('ipcNumber') or '').split('|')[0][:14]
    appno = rec.get('applicationNumber') or ''
    link = google_link(rec)
    link_md = f'[열기]({link})' if link else ''
    return (f'| {st} | {title} | {appl} | {appno} | {ipc} | '
            f'{",".join(sorted(labels))} | {link_md} |')


def _write_md(order, by_app, per_query):
    lines = ['# KIPRIS 서명 IP/기술조각 국내 선행검색 (S1·S2·T1·T2)\n']
    lines.append(f'- 쿼리 {len(QUERIES)}개 · 중복 제거 {len(order)}건 · 초록/청구항 필드 한정\n')
    lines.append('- ⚠ 예비검색. 전체요소 대조·법적상태는 변리사가 재확인.\n')
    lines.append('- ⚠ 한국은 전세계 신규성. 국내 0건=등록가능성↑ 이지 신규성 보장 아님.\n')
    lines.append('\n## 쿼리별 총건수 (0=국내 무검출 신호)\n')
    lines.append('| 라벨 | 검색 | 총건수 | 수신 |')
    lines.append('|---|---|--:|--:|')
    for label, q, total, got in per_query:
        lines.append(f'| {label} | {q} | {total} | {got} |')
    lines.append('\n## 결과 (등록 우선)\n')
    lines.append('| 상태 | 발명의 명칭 | 출원인 | 출원번호 | IPC | 매칭 | 링크 |')
    lines.append('|---|---|---|---|---|---|---|')
    for app in order:
        lines.append(_row(app, by_app))
    lines.append('\n## 초록(요약) 발췌\n')
    for app in order:
        rec = by_app[app][1]
        ab = (rec.get('astrtCont') or '').strip()
        if not ab:
            continue
        labels = ','.join(sorted(by_app[app][0]))
        lines.append(f'**{rec.get("inventionTitle") or "(제목없음)"}** '
                     f'({rec.get("applicationNumber") or ""}) — 매칭 {labels}  ')
        lines.append(ab[:450] + ('…' if len(ab) > 450 else '') + '\n')
    with open(RESULT_MD, 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines))


if __name__ == '__main__':
    k = load_key()
    if not k:
        raise SystemExit('✗ 서비스키 없음: tools/.kipris_key 첫 줄에 키를 넣으세요.')
    run_search(k)
