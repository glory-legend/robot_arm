#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""KIPRIS Plus 특허 선행조사 스크립트 — 바코드 재시퀀싱 버퍼 팔레타이징 국내특허 스윕.

목적
----
docs/barcode_resequencing_palletizing_patent_draft_2026-09-03.md 의 §3.2가
"Google Patents 웹검색으로 대체, KIPRIS 전수조사 아님"이라고 명시한 한계를
정식 KIPRIS Plus 고급검색 API로 메꾼다. tools/kipris_search.py(빈피킹 파지
전용)와 별개 스크립트로 분리했다 — 조사 대상 발명이 다르기 때문.

이 스크립트는 두 가지를 한다:
  1) IPC 한정 고급검색으로 팔레타이징×바코드×버퍼×안정성×충돌 관련 국내
     특허를 폭넓게 훑는다 (§3.2 전수조사 갭 메우기).
  2) 이전 조사(Google Patents 웹검색, 세션 중 차단됨)에서 "미검증"으로
     남긴 8건의 출원/공개번호를 KIPRIS 원부로 직접 조회해 재확인한다
     (§3.3 갭 메우기).

준비물
------
tools/.kipris_key 에 서비스키 1줄 (gitignore 됨).

실행
----
    python3 tools/kipris_search_palletizing.py --check   # 키 확인
    python3 tools/kipris_search_palletizing.py           # 전체 스윕 실행

주의: 예비검색이다. 아래에서 확인되는 astrtCont(초록)는 KIPRIS가 실제로
돌려주는 값이며, claimScope로 검색은 하지만 응답에 청구항 전문이 포함되는지는
현장에서 확인해야 한다(포함되면 FIELDS에서 그대로 추출해 사용).
"""
import os
import sys
import time
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET

BASE = 'http://plus.kipris.or.kr'
SERVICE_PATH = '/kipo-api/kipi/patUtiModInfoSearchSevice'
OP_ADV = '/getAdvancedSearch'
# 6차→7차 개정 핵심 발견: getAdvancedSearch는 초록만 주지만, 이 오퍼레이션은
# 출원번호 하나로 청구항 전문(claimInfoArray)·출원인·법적상태 이력까지 전부
# 돌려준다. Google Patents가 최근 공개건을 색인하지 못해 막혔던 §3.4 갭을
# 이걸로 전부 닫았다 — 앞으로 이 조사에서는 Google Patents보다 이걸 우선 쓸 것.
OP_DETAIL = '/getBibliographyDetailInfoSearch'

# 청구항 전문을 확보할 문헌 목록 (라벨, applicationNumber).
# 6차 개정까지 청구항 전문 확인 9건 + 7차 개정에서 OP_DETAIL로 새로 닫은 4건.
CLAIM_LOOKUP = [
    ('Mujin-비순서도착패키지', '1020200065151'),
    ('티이에스-적재최적화', '1020220147750'),
    ('톱텍가치소프트CJ-배치최적화', '1020220157242'),
    ('가치소프트-재정렬배출', '1020210129414'),
    ('씨메스-버퍼내위치', '1020230037244'),
    ('씨메스-강화학습팔레타이징', '1020230197541'),
    ('Symbotic-유연시퀀싱', '1020247020877'),
    ('CJ-로터리버퍼', '1020240157396'),
    ('씨메스-안정성평가', '1020250207937'),
    ('한기대-무게중심', '1020240015387'),
    ('삼성전자-파렛타이징', '1020210133254'),
    ('고레로보틱스-하역위치', '1020250207927'),
]

NUM_ROWS = 100
PAGE_NO = 1
SLEEP_SEC = 0.5

# (라벨, 검색필드, 검색어, IPC 또는 None)
# 필드: astrtCont=초록 / claimScope=청구범위 / inventionTitle=발명명칭 / applicantName=출원인
QUERIES = [
    # ── §2.1 청구항 1의 핵심 결합요소를 IPC B65G(적재·파레타이징)로 좁혀 스캔 ──
    ('버퍼-바코드', 'astrtCont', '바코드*버퍼', 'B65G'),
    ('버퍼-재적재', 'astrtCont', '버퍼*재적재', 'B65G'),
    ('임시보관-회수', 'astrtCont', '임시*보관*회수', 'B65G'),
    ('팔레타이징-안정성', 'astrtCont', '팔레타이징*안정성', 'B65G'),
    ('팔레타이징-온라인적재', 'astrtCont', '팔레타이징*온라인*적재', 'B65G'),
    ('혼합박스-적재순서', 'astrtCont', '혼합*박스*적재*순서', 'B65G'),
    # ── IPC B25J(로봇 제어)로 좁혀 로봇 실행가능성 게이트 관련 스캔 ──
    ('팔레타이징-충돌', 'astrtCont', '팔레타이징*충돌', 'B25J'),
    ('팔레타이징-역기구학', 'astrtCont', '팔레타이징*역기구학', 'B25J'),
    ('팔레타이징-배치위치', 'astrtCont', '팔레타이징*배치*위치', 'B25J'),
    # ── IPC G06Q(물류/업무처리)로 좁혀 바코드 기반 계획 스캔 ──
    ('바코드-팔레타이징', 'astrtCont', '바코드*팔레타이징', 'G06Q'),
    ('적재계획-갱신', 'astrtCont', '적재*계획*갱신', 'G06Q'),
    # ── 제목 직접 검색 (IPC 제한 없음 — 놓친 것 없는지 확인) ──
    ('제목-팔레타이징버퍼', 'inventionTitle', '팔레타이징*버퍼', None),
    ('제목-재시퀀싱', 'inventionTitle', '재시퀀싱', None),
    # ── 청구범위 필드 직접 검색 (실제로 무엇을 "청구"했는지) ──
    ('청구-버퍼재적재', 'claimScope', '버퍼*재적재', 'B65G'),
    ('청구-바코드순서', 'claimScope', '바코드*순서', 'B65G'),
    ('청구-적재안정성', 'claimScope', '적재*안정성', 'B25J'),
    # ── 5차 개정 추가: 무게중심·실시간재계획·버퍼로봇 조합 ──
    ('바코드-로봇-B65G', 'astrtCont', '바코드*로봇', 'B65G'),
    ('바코드-로봇-B25J', 'astrtCont', '바코드*로봇', 'B25J'),
    ('실시간-재계획-로봇', 'astrtCont', '실시간*재계획', 'B25J'),
    ('무게중심-로봇-적재', 'astrtCont', '무게중심*적재', 'B25J'),
    ('버퍼-로봇-팔레트', 'astrtCont', '버퍼*로봇*팔레트', None),
]

# 5차 개정: 'applicantName'이 아니라 'applicant'가 정답 필드명이었다
# (버그 원인 규명, §3.4). 이 리스트로 팔레타이징 관련 핵심 업체를
# IPC B65G/B25J/G06Q 각각에서 전수 확인한다.
COMPANIES = [
    '씨메스로보틱스', '씨제이대한통운', '가치소프트', '현대로보틱스',
    '두산로보틱스', '레인보우로보틱스', '뉴로메카', '심보틱',
]
COMPANY_IPCS = ['B65G', 'B25J', 'G06Q']

# 직접 확인이 필요한 이전 조사(Google Patents 웹검색)의 미검증 후보 +
# 5차 개정에서 새로 특정된 핵심 후보. applicationNumber로 원부 직접 조회.
DIRECT_LOOKUP = [
    ('KR101869896B1', 'registerNumber', '1018698960000'),
    ('KR100865165B1', 'registerNumber', '1008651650000'),
    ('KR20190017133A', 'openNumber', '1020190017133'),
    ('KR20110048870A', 'openNumber', '1020110048870'),
    ('KR20080112230A', 'openNumber', '1020080112230'),
    ('KR20070121262A', 'openNumber', '1020070121262'),
    ('KR20180101308A', 'openNumber', '1020180101308'),
    ('KR101480868B1', 'registerNumber', '1014808680000'),
    ('KR1020250207937(씨메스-안정성)', 'applicationNumber', '1020250207937'),
    ('KR1020230037244(씨메스-버퍼내위치)', 'applicationNumber', '1020230037244'),
    ('KR1020220157242(CJ+가치소프트-배치최적화)', 'applicationNumber', '1020220157242'),
    ('KR1020247020877(심보틱-유연시퀀싱등록)', 'applicationNumber', '1020247020877'),
    ('KR1020210002643(CJ-디팔레타이저)', 'applicationNumber', '1020210002643'),
    ('KR1020240015387(한기대-무게중심)', 'applicationNumber', '1020240015387'),
    # 6차 개정: CPC 서브그룹(B65G57/03, B65G57/22) 전수 열람에서 발견
    ('KR102400028B1(Mujin-비순서도착패키지)', 'registerNumber', '1024000280000'),
    ('KR102408914B1(Mujin-오류검출동적패킹)', 'registerNumber', '1024089140000'),
    ('KR102930151B1(Mujin-벽기반패킹)', 'registerNumber', '1029301510000'),
    ('KR1020210133254(삼성전자-파렛타이징)', 'applicationNumber', '1020210133254'),
    ('KR102585996B1(티이에스-적재최적화)', 'registerNumber', '1025859960000'),
    ('KR102786556B1(티이에스-파손방지)', 'registerNumber', '1027865560000'),
    ('KR1020230130102(티이에스-무게기반변경)', 'applicationNumber', '1020230130102'),
]

# 6차 개정: CPC 서브그룹 전수 열람 대상. IPC만으로 열람하려면
# inventionTitle 등 필드값을 빈 문자열로 둔다.
SUBGROUP_SWEEP = ['B65G57/03', 'B65G57/22']

FIELDS = ['inventionTitle', 'applicantName', 'applicationNumber',
          'registerStatus', 'ipcNumber', 'astrtCont', 'claimScope',
          'registerNumber', 'openNumber']

RESULT_MD = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                          'kipris_results_palletizing.md')


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
    url = build_adv_url('astrtCont', '팔레타이징', key, ipc='B65G')
    print(f'[확인] 고급검색 요청 → {OP_ADV} (초록=팔레타이징, IPC=B65G)')
    ok, body, err = fetch(url)
    if not ok:
        print(f'  ✗ 요청 실패: {err}')
        return False
    status, items, total = parse_items(body)
    print(f'  응답: {status} / 총 {total}건')
    if 'successYN=Y' in status:
        print(f'  ✓ 정상 — 예시 {len(items)}건 수신.')
        if items:
            print(f'  claimScope 필드 수신 여부: '
                  f'{"있음" if items[0].get("claimScope") else "없음(초록만 반환)"}')
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
            print(f'[{label}] {field}="{value}" IPC={ipc} → 요청 실패: {err}')
            per_query.append((label, f'{field}:{value} ipc={ipc}', -1, 0))
            time.sleep(SLEEP_SEC)
            continue
        status, items, total = parse_items(body)
        per_query.append((label, f'{field}:{value} ipc={ipc}', total, len(items)))
        capped = ' ⚠캡초과' if total > len(items) else ''
        print(f'[{label}] {field}="{value}" IPC={ipc} → 총 {total}건(수신 {len(items)}){capped}')
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

    # 5차 개정: 업체별 전수 확인 ('applicant' 필드, applicantName 아님 — §3.4 버그 규명)
    company_results = []  # (company, ipc, total, [rec,...])
    for co in COMPANIES:
        for ipc in COMPANY_IPCS:
            url = build_adv_url('applicant', co, key, ipc=ipc)
            ok, body, err = fetch(url)
            if not ok:
                company_results.append((co, ipc, -1, []))
                time.sleep(SLEEP_SEC)
                continue
            status, items, total = parse_items(body)
            company_results.append((co, ipc, total, items))
            print(f'[업체 {co}] IPC={ipc} → 총 {total}건')
            time.sleep(SLEEP_SEC)

    # 6차 개정: CPC 서브그룹 전수 열람 (IPC만으로, 키워드 제한 없이)
    subgroup_results = []  # (ipc, total, [rec,...])
    for ipc in SUBGROUP_SWEEP:
        url = build_adv_url('inventionTitle', '', key, ipc=ipc)
        ok, body, err = fetch(url)
        if not ok:
            subgroup_results.append((ipc, -1, []))
            time.sleep(SLEEP_SEC)
            continue
        status, items, total = parse_items(body)
        subgroup_results.append((ipc, total, items))
        print(f'[서브그룹 {ipc}] → 총 {total}건(수신 {len(items)})')
        time.sleep(SLEEP_SEC)

    # 직접 조회: 이전 조사(§3.3)의 미검증 후보를 KIPRIS 원부로 재확인
    direct_results = []
    for label, field, value in DIRECT_LOOKUP:
        url = build_adv_url(field, value, key)
        ok, body, err = fetch(url)
        if not ok:
            direct_results.append((label, field, value, None, f'요청 실패: {err}'))
            time.sleep(SLEEP_SEC)
            continue
        status, items, total = parse_items(body)
        direct_results.append((label, field, value, items[0] if items else None, status))
        print(f'[직접조회 {label}] {field}={value} → 총 {total}건, {status}')
        time.sleep(SLEEP_SEC)

    def sort_key(app):
        _labels, rec = by_app[app]
        reg = '등록' in (rec.get('registerStatus') or '')
        return (0 if reg else 1, rec.get('inventionTitle') or '')
    order.sort(key=sort_key)

    _write_md(order, by_app, per_query, direct_results, company_results, subgroup_results)
    print(f'\n총 {len(order)}건(스윕, 중복 제거) + 직접조회 {len(direct_results)}건 — '
          f'상세는 {RESULT_MD}')
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


def _write_md(order, by_app, per_query, direct_results, company_results, subgroup_results):
    lines = ['# KIPRIS 바코드·팔레타이징 국내특허 정밀검색 결과\n']
    lines.append(f'- 스윕 쿼리 {len(QUERIES)}개 · 업체 {len(COMPANIES)}곳 × '
                 f'IPC {len(COMPANY_IPCS)}개 전수 확인 · 중복 제거 {len(order)}건 · '
                 f'초록/제목/청구범위/출원인(applicant) 필드 한정\n')
    lines.append('- ⚠ 예비검색이다. 청구항 전체요소 대조·법적상태는 변리사가 재확인.\n')
    lines.append('- ⚠ 5차 개정: 출원인 검색 파라미터는 `applicant`다 (`applicantName`은 '
                 '응답 필드명일 뿐 질의 파라미터로 쓰면 API가 무시하고 전체 IPC 결과를 '
                 '반환하는 버그가 있었음).\n')
    lines.append('\n## 쿼리별 총건수 (캡 초과 = 더 있음, 좁힐 필요)\n')
    lines.append('| 라벨 | 검색 | 총건수 | 수신 |')
    lines.append('|---|---|--:|--:|')
    for label, q, total, got in per_query:
        lines.append(f'| {label} | {q} | {total} | {got} |')
    lines.append('\n## 스윕 결과 (등록 우선)\n')
    lines.append('| 상태 | 발명의 명칭 | 출원인 | 출원번호 | IPC | 매칭 | 링크 |')
    lines.append('|---|---|---|---|---|---|---|')
    for app in order:
        lines.append(_row(app, by_app))
    lines.append('\n## CPC 서브그룹 전수 열람 (키워드 없이 IPC만으로)\n')
    for ipc, total, items in subgroup_results:
        if total <= 0:
            continue
        lines.append(f'\n**IPC={ipc}** — 총 {total}건'
                     f'{" (상위 100건만 표시)" if total > len(items) else " (전건 표시)"}\n')
        for rec in items:
            lines.append(f'- [{rec.get("registerStatus")}] '
                         f'{rec.get("inventionTitle")} '
                         f'({rec.get("applicantName")}) '
                         f'{rec.get("applicationNumber")}')
    lines.append('\n## 업체별 전수 확인 (applicant 필드, IPC별)\n')
    lines.append('쿼리 문자열과 무관하게, 이름을 아는 핵심 업체가 관련 IPC에 낸 '
                 '문헌 제목을 전부 나열한다(최대 30건/조합, 캡 초과분은 총건수만).\n')
    for co, ipc, total, items in company_results:
        if total <= 0:
            continue
        lines.append(f'\n**{co} · IPC={ipc}** — 총 {total}건'
                     f'{" (캡 초과, 상위만 표시)" if total > len(items) else ""}\n')
        for rec in items[:30]:
            lines.append(f'- [{rec.get("registerStatus")}] '
                         f'{rec.get("inventionTitle")} '
                         f'({rec.get("applicationNumber")})')
    lines.append('\n## §3.3 미검증 후보 직접 재조회 (KIPRIS 원부)\n')
    lines.append('| 후보 | 조회 필드 | 조회값 | 결과 |')
    lines.append('|---|---|---|---|')
    for label, field, value, rec, status in direct_results:
        if rec:
            desc = (f'{rec.get("inventionTitle") or "?"} / '
                    f'{rec.get("applicantName") or "?"} / '
                    f'{rec.get("registerStatus") or "?"}')
        else:
            desc = f'미발견 ({status})'
        lines.append(f'| {label} | {field} | {value} | {desc} |')
    lines.append('\n## 초록(요약) 발췌 — 스윕 결과\n')
    for app in order:
        rec = by_app[app][1]
        ab = (rec.get('astrtCont') or '').strip()
        if not ab:
            continue
        labels = ','.join(sorted(by_app[app][0]))
        lines.append(f'**{rec.get("inventionTitle") or "(제목없음)"}** '
                     f'({rec.get("applicationNumber") or ""}) — 매칭 {labels}  ')
        lines.append(ab[:500] + ('…' if len(ab) > 500 else '') + '\n')
    lines.append('\n## claimScope(청구범위) 발췌 — 응답에 포함된 경우\n')
    any_claim = False
    for app in order:
        rec = by_app[app][1]
        cs = (rec.get('claimScope') or '').strip()
        if not cs:
            continue
        any_claim = True
        lines.append(f'**{rec.get("inventionTitle") or "(제목없음)"}** '
                     f'({rec.get("applicationNumber") or ""})  ')
        lines.append(cs[:800] + ('…' if len(cs) > 800 else '') + '\n')
    if not any_claim:
        lines.append('(이번 응답에는 claimScope 필드가 채워진 항목이 없었다 — '
                      'API가 청구항 전문을 반환하지 않거나, 별도 상세조회 오퍼레이션이 '
                      '필요할 수 있다.)\n')
    with open(RESULT_MD, 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines))


CLAIMS_MD = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                          'kipris_claims_palletizing.md')


def fetch_full_detail(app_number, key):
    """OP_DETAIL로 출원번호 하나의 서지+청구항 전문+법적상태를 가져온다."""
    params = {'applicationNumber': app_number, 'ServiceKey': key}
    url = f'{BASE}{SERVICE_PATH}{OP_DETAIL}?' + urllib.parse.urlencode(params)
    ok, body, err = fetch(url)
    if not ok:
        return None, err
    try:
        root = ET.fromstring(body)
    except ET.ParseError as exc:
        return None, f'파싱 실패: {exc}'
    if (root.findtext('.//successYN') or '') != 'Y':
        return None, root.findtext('.//resultMsg') or '실패'
    info = {
        'title': root.findtext('.//inventionTitle') or '',
        'applicant': root.findtext('.//applicantInfo/name') or '',
        'status': root.findtext('.//registerStatus') or '',
        'appDate': root.findtext('.//applicationDate') or '',
        'openNumber': root.findtext('.//openNumber') or '',
        'registerNumber': root.findtext('.//registerNumber') or '',
        'claims': [c.text for c in root.findall('.//claimInfo/claim') if c.text],
    }
    return info, None


def run_claims(key):
    """CLAIM_LOOKUP 전체의 청구항 전문을 받아 kipris_claims_palletizing.md에 쓴다."""
    lines = ['# 청구항 전문 원본 (KIPRIS getBibliographyDetailInfoSearch)\n']
    lines.append('- 6차→7차 개정에서 발견한 API. Google Patents 미색인 최신건도 '
                 '전부 여기서 확보된다.\n')
    ok_count = 0
    for label, appno in CLAIM_LOOKUP:
        info, err = fetch_full_detail(appno, key)
        if not info:
            print(f'[청구항 {label}] {appno} → 실패: {err}')
            lines.append(f'\n## {label} ({appno}) — 실패: {err}\n')
            time.sleep(SLEEP_SEC)
            continue
        ok_count += 1
        print(f'[청구항 {label}] {appno} → {info["title"]} '
              f'/ {info["status"]} / 청구항 {len(info["claims"])}개')
        lines.append(f'\n## {label}\n')
        lines.append(f'- 출원번호: {appno} · 출원인: {info["applicant"]} · '
                     f'상태: {info["status"]} · 공개번호: {info["openNumber"]} · '
                     f'등록번호: {info["registerNumber"]}')
        lines.append(f'- 발명의 명칭: **{info["title"]}**\n')
        for c in info['claims']:
            lines.append(c)
            lines.append('')
        time.sleep(SLEEP_SEC)
    with open(CLAIMS_MD, 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines))
    print(f'\n{ok_count}/{len(CLAIM_LOOKUP)}건 청구항 전문 확보 — {CLAIMS_MD}')


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
    if '--claims' in argv:
        run_claims(key)
        return
    run_search(key)


if __name__ == '__main__':
    main()
