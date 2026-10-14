#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""KIPRIS Plus 특허 선행조사 스크립트 — 빈피킹 파지 특허 후보 정밀 검색.

목적
----
길 1(특허 실적 확보)로 가기 전에, 우리 발명 후보(특히 ① 손가락 개구 계산)와 비슷한
**한국 특허가 이미 있는지**를 KIPRIS Plus 고급검색(getAdvancedSearch)으로 훑는다.
초록(astrtCont)·청구범위(claimScope) 필드를 콕 집고 IPC 를 B25J(로봇 조작)로
좁혀, 이전 단어검색의 잡음(의자·포장기·팔토시 등)을 원천 차단한다.

준비물
------
1) KIPRIS Plus 에서 "특허·실용신안 공개/등록공보" API 신청 → 승인.
2) 서비스키(Decoding 키)를 아래 중 하나로:
     - 파일(권장):  tools/.kipris_key  첫 줄에 키만  (gitignore 됨, 채팅에 안 남음)
     - 환경변수:    export KIPRIS_SERVICE_KEY="키"
     - 명령줄:      python3 tools/kipris_search.py --key "키"

실행
----
    python3 tools/kipris_search.py --check     # 키·주소 확인(1회)
    python3 tools/kipris_search.py             # 정밀 검색 → tools/kipris_results.md

주소가 다르면 BASE / SERVICE_PATH 두 상수만 콘솔 'REST 활용가이드' 값으로 바꾼다.
주의: 예비검색이다. 청구항 전체요소 대조·법적상태는 변리사가 KIPRIS 원부로 확인해야 한다.
"""
import os
import sys
import time
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET

# ---------------------------------------------------------------------------
# ★ 주소가 안 맞으면 이 두 줄만 고친다 (콘솔 'REST 활용가이드' 참고)
# ---------------------------------------------------------------------------
BASE = 'http://plus.kipris.or.kr'
SERVICE_PATH = '/kipo-api/kipi/patUtiModInfoSearchSevice'   # (철자 'Sevice' 는 원본 그대로)
OP_ADV = '/getAdvancedSearch'         # 고급검색 — 필드 지정 + IPC 필터
OP_WORD = '/getWordSearch'            # (참고용) 자유 단어검색

# 검색을 IPC 로 B25J(로봇 조작·파지)에만 한정 → 기계식/포장/가구 잡음 제거.
IPC_FILTER = 'B25J'
NUM_ROWS = 100                        # 쿼리당 최대 건수(고급검색은 잡음이 적어 넉넉히)
PAGE_NO = 1
SLEEP_SEC = 0.5

# ---------------------------------------------------------------------------
# ★ 정밀 검색어 — (라벨, 검색필드, 검색어).
#   필드:  astrtCont=초록 / claimScope=청구범위 / inventionTitle=발명명칭
#   연산자(필드값 안):  * = 둘 다 포함(AND) / + = 둘 중 하나(OR) / ! = 제외
#   모든 쿼리는 자동으로 IPC=B25J 로 한정된다.
#   ★ 후보 ①(개구를 무더기 충돌로 계산)에 집중. 초록과 청구항 양쪽을 본다.
# ---------------------------------------------------------------------------
QUERIES = [
    # ── ① 초록에서: 파지 폭/개구 + 간섭/충돌 조합 (우리 개념의 핵심) ──
    ('①초록-폭간섭', 'astrtCont', '파지*폭*간섭'),
    ('①초록-폭충돌', 'astrtCont', '파지*폭*충돌'),
    ('①초록-개구간섭', 'astrtCont', '그리퍼*개구*간섭'),
    ('①초록-손가락충돌', 'astrtCont', '손가락*충돌*회피'),
    ('①초록-핑거간섭', 'astrtCont', '핑거*간섭*파지'),
    ('①초록-주변간섭', 'astrtCont', '그리퍼*주변*간섭'),
    # ── ① 청구범위에서: 실제로 '개구/폭을 결정'을 청구했는지 (법적 범위) ──
    ('①청구-폭간섭', 'claimScope', '파지*폭*간섭'),
    ('①청구-개구충돌', 'claimScope', '개구*충돌'),
    ('①청구-폭결정', 'claimScope', '파지*폭*결정'),
    # ── ④ 기울임 접근 ──
    ('④초록-기울', 'astrtCont', '빈피킹*기울*파지'),
    ('④초록-경사', 'astrtCont', '파지*경사*접근'),
    # ── ② 학습형 파지 선택 (붐빔 확인용) ──
    ('②초록-학습', 'astrtCont', '빈피킹*파지*학습'),
]

FIELDS = ['inventionTitle', 'applicantName', 'applicationNumber',
          'registerStatus', 'ipcNumber', 'astrtCont',
          'registerNumber', 'openNumber']

RESULT_MD = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                         'kipris_results.md')


def load_key(argv_key=None):
    if argv_key:
        return argv_key.strip()
    env = os.environ.get('KIPRIS_SERVICE_KEY', '').strip()
    if env:
        return env
    keyfile = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                           '.kipris_key')
    if os.path.exists(keyfile):
        with open(keyfile, encoding='utf-8') as f:
            return f.readline().strip()
    return ''


def build_adv_url(field, value, key):
    """고급검색 URL. field 하나 + IPC 한정 + 특허·실용 모두."""
    params = {field: value, 'ipcNumber': IPC_FILTER,
              'patent': 'true', 'utility': 'true',
              'numOfRows': NUM_ROWS, 'pageNo': PAGE_NO, 'ServiceKey': key}
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
    """응답 XML → (상태문자열, item목록, 총건수). 총건수로 40/100 잘림 여부 판단."""
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
    print(f'[확인] 고급검색 요청 → {OP_ADV} (초록=그리퍼, IPC={IPC_FILTER})')
    ok, body, err = fetch(url)
    if not ok:
        print(f'  ✗ 요청 실패: {err}')
        return False
    status, items, total = parse_items(body)
    print(f'  응답: {status} / 총 {total}건')
    if 'successYN=Y' in status:
        print(f'  ✓ 정상 — 예시 {len(items)}건 수신. 이제 인자 없이 정밀검색을 돌리세요.')
        return True
    print('  ✗ 인증/서비스 오류. 원문 앞부분:')
    print('  ' + body[:400].replace('\n', ' '))
    return False


def run_search(key):
    by_app = {}
    order = []
    per_query = []          # (라벨, 검색어, 총건수, 수신건수)
    for label, field, value in QUERIES:
        url = build_adv_url(field, value, key)
        ok, body, err = fetch(url)
        if not ok:
            print(f'[{label}] {field}="{value}" → 요청 실패: {err}')
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
    for app in order[:12]:
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
    lines = ['# KIPRIS 빈피킹 파지 특허 정밀검색 결과 (고급검색·IPC=B25J)\n']
    lines.append(f'- 쿼리 {len(QUERIES)}개 · 중복 제거 {len(order)}건 · '
                 f'초록/청구항 필드 한정 · IPC {IPC_FILTER}\n')
    lines.append('- ⚠ 예비검색이다. 청구항 전체요소 대조·법적상태는 변리사가 재확인.\n')
    lines.append('\n## 쿼리별 총건수 (캡 초과 = 더 있음, 좁힐 필요)\n')
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
