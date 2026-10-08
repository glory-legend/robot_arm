#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""KIPRIS Plus 국내 선행조사 — 새 공정 특허 후보(키팅·디네스팅·머신텐딩 등).

목적
----
`docs/vision_desktop_robotarm_new_process_scouting_2026-09-10.md` 의 후보
C1(키팅)·C2(트레이 디네스팅)·C5(머신텐딩)·C3(유연공급)·C4(결함분기)에 대해
**국내(한국) 개별개시가 이미 있는지**를 KIPRIS Plus 고급검색으로 1차 확인한다.
사용자 방침이 '국내 특허 타깃'이므로, 국내 선행 부재가 등록가능성의 1차 결정변수다.

기존 `kipris_search.py`(빈피킹)와 동일한 API·파서를 쓰되:
  - 검색어를 새 공정 후보로 교체
  - **IPC 필터를 쿼리별로 선택**(키팅/공급은 B25J 밖 분류가 많아 기본 무필터)

실행:  python3 tools/kipris_search_new_process.py            # → tools/kipris_results_new_process.md
       python3 tools/kipris_search_new_process.py --check   # 키/주소 확인
주의: 예비검색이다. 청구항 전체요소 대조·법적상태는 변리사가 KIPRIS 원부로 확인.
"""
import os
import sys
import time
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET

BASE = 'http://plus.kipris.or.kr'
SERVICE_PATH = '/kipo-api/kipi/patUtiModInfoSearchSevice'   # (원본 철자 유지)
OP_ADV = '/getAdvancedSearch'
NUM_ROWS = 100
PAGE_NO = 1
SLEEP_SEC = 0.5

# (라벨, 필드, 검색어, IPC)  — IPC=None 이면 무필터(넓게), 'B25J' 등 지정 가능.
#   필드 안 연산자:  * = AND / + = OR / ! = 제외
QUERIES = [
    # ── C1 혼류 키팅(세트 공급) ──
    ('C1-초록-키팅로봇', 'astrtCont', '키팅*로봇', None),
    ('C1-초록-부품세트로봇', 'astrtCont', '부품*세트*로봇', None),
    ('C1-초록-키트비전', 'astrtCont', '키트*비전*파지', None),
    ('C1-초록-다품종키팅', 'astrtCont', '다품종*키팅', None),
    ('C1-청구-키팅로봇', 'claimScope', '키팅*로봇', None),
    # ── C2 반품 트레이/던니지 디네스팅 ──
    ('C2-초록-트레이취출', 'astrtCont', '트레이*부품*취출', None),
    ('C2-초록-트레이로봇파지', 'astrtCont', '트레이*로봇*파지', None),
    ('C2-초록-던니지', 'astrtCont', '던니지', None),
    ('C2-초록-다단트레이취출', 'astrtCont', '다단*트레이*취출', None),
    ('C2-청구-트레이취출로봇', 'claimScope', '트레이*취출*로봇', None),
    # ── C5 혼류 소롯 머신텐딩 ──
    ('C5-초록-공작기계장착', 'astrtCont', '공작기계*로봇*장착', None),
    ('C5-초록-공작기계로딩', 'astrtCont', '공작기계*로봇*로딩', None),
    ('C5-초록-지그빈감지', 'astrtCont', '지그*비전*로봇', None),
    # ── C3 유연 공급(싱귤레이션-프레젠테이션) ──
    ('C3-초록-정렬공급비전', 'astrtCont', '부품*정렬*공급*비전', None),
    ('C3-초록-유연피더로봇', 'astrtCont', '유연*피더*로봇', None),
    # ── C4 인라인 결함 리라우팅 ──
    ('C4-초록-불량선별로봇', 'astrtCont', '불량*로봇*선별', None),
    ('C4-초록-검사재작업분류', 'astrtCont', '검사*재작업*분류', None),
]

FIELDS = ['inventionTitle', 'applicantName', 'applicationNumber',
          'registerStatus', 'ipcNumber', 'astrtCont',
          'registerNumber', 'openNumber']

RESULT_MD = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                         'kipris_results_new_process.md')


def load_key(argv_key=None):
    if argv_key:
        return argv_key.strip()
    env = os.environ.get('KIPRIS_SERVICE_KEY', '').strip()
    if env:
        return env
    keyfile = os.path.join(os.path.dirname(os.path.abspath(__file__)), '.kipris_key')
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
    code = _first_text(root, 'resultCode')
    msg = _first_text(root, 'resultMsg')
    total = _first_text(root, 'totalCount') or '0'
    status = f'successYN={success or "?"} resultCode={code or "?"} {msg or ""}'.strip()
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


def run_check(key):
    url = build_adv_url('astrtCont', '그리퍼', key)
    print(f'[확인] 고급검색 요청 → {OP_ADV} (초록=그리퍼)')
    ok, body, err = fetch(url)
    if not ok:
        print(f'  ✗ 요청 실패: {err}')
        return False
    status, items, total = parse_items(body)
    print(f'  응답: {status} / 총 {total}건')
    if 'successYN=Y' in status:
        print(f'  ✓ 정상 — 예시 {len(items)}건 수신.')
        return True
    print('  ✗ 인증/서비스 오류. 원문 앞부분:')
    print('  ' + body[:400].replace('\n', ' '))
    return False


def run_search(key):
    by_app = {}
    order = []
    per_query = []
    for label, field, value, ipc in QUERIES:
        url = build_adv_url(field, value, key, ipc)
        ok, body, err = fetch(url)
        if not ok:
            print(f'[{label}] {field}="{value}" ipc={ipc} → 요청 실패: {err}')
            per_query.append((label, f'{field}:{value}', ipc, -1, 0))
            time.sleep(SLEEP_SEC)
            continue
        status, items, total = parse_items(body)
        per_query.append((label, f'{field}:{value}', ipc, total, len(items)))
        capped = ' ⚠캡초과' if total > len(items) else ''
        print(f'[{label}] {field}="{value}" ipc={ipc} → 총 {total}건(수신 {len(items)}){capped}')
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
        print(f'  - [{st}] {title}  ({rec.get("applicantName") or "?"}) '
              f'[{",".join(sorted(labels))}]')


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
    lines = ['# KIPRIS 새 공정 특허 후보 국내 선행검색 (C1~C5)\n']
    lines.append(f'- 쿼리 {len(QUERIES)}개 · 중복 제거 {len(order)}건 · 초록/청구항 필드 한정\n')
    lines.append('- ⚠ 예비검색이다. 청구항 전체요소 대조·법적상태는 변리사가 재확인.\n')
    lines.append('- ⚠ 한국은 전세계 신규성(§29). 국내 무검출=등록가능성↑ 이지 신규성 보장 아님.\n')
    lines.append('\n## 쿼리별 총건수 (0=국내 무검출 신호, 캡초과=더 있음)\n')
    lines.append('| 라벨 | 검색 | IPC | 총건수 | 수신 |')
    lines.append('|---|---|---|--:|--:|')
    for label, q, ipc, total, got in per_query:
        lines.append(f'| {label} | {q} | {ipc or "-"} | {total} | {got} |')
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
        lines.append(ab[:500] + ('…' if len(ab) > 500 else '') + '\n')
    with open(RESULT_MD, 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines))


def main():
    argv = sys.argv[1:]
    argv_key = None
    if '--key' in argv:
        i = argv.index('--key')
        if i + 1 < len(argv):
            argv_key = argv[i + 1]
    key = load_key(argv_key)
    if not key:
        print('✗ 서비스키가 없습니다. tools/.kipris_key 파일 첫 줄에 키를 넣으세요.')
        sys.exit(1)
    if '--check' in argv:
        sys.exit(0 if run_check(key) else 2)
    run_search(key)


if __name__ == '__main__':
    main()
