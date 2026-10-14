#!/usr/bin/env python3
"""KIPRIS Plus 예비검색 — '가상 회수 검증 기반 혼합 박스 적재 제어' 전용.

이 주제 전용 스크립트다. 같은 리포지토리의
  - tools/kipris_search.py                 : 빈피킹(볼트 파지) 전용, IPC=B25J 고정
  - tools/kipris_search_palletizing.py     : 바코드 재시퀀싱 버퍼 팔레타이징 전용
와 쿼리를 섞지 않는다. 서로 다른 발명 도메인의 질의가 섞이면 결과가 오염된다.

조사 초점(docs/virtual_retrieval_verification_claim_chart_2026-09-09.md §5-1의 D1~D6):
  D1 임시 배치 후보별 가상 배치 + 선행 순서 가상 회수로 후보 탈락
  D2 박스 제거 후 남은 적재물의 안정성 판정
  D3 회수 시 그리퍼 접근·파지 가능성 판정
  D4 버퍼 회수 경로를 대상으로 하는 충돌 검사
  D5 실제 위치 오차를 회수 가능성 재판정에 되먹임
  D6 실제 적재 성공 확인 전 후행 박스 선행조건 보류

사용법:
  python3 tools/kipris_search_virtual_retrieval.py --check      # 키/응답 확인
  python3 tools/kipris_search_virtual_retrieval.py --claims     # 청구항 전문 확보
  python3 tools/kipris_search_virtual_retrieval.py --sweep      # 키워드 스윕
  python3 tools/kipris_search_virtual_retrieval.py --subgroup   # CPC 서브그룹 전수 열람
  python3 tools/kipris_search_virtual_retrieval.py --all
키: tools/.kipris_key 또는 env KIPRIS_SERVICE_KEY 또는 --key <값>
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
OP_DETAIL = '/getBibliographyDetailInfoSearch'

NUM_ROWS = 100
PAGE_NO = 1
SLEEP_SEC = 0.4

HERE = os.path.dirname(os.path.abspath(__file__))
SWEEP_MD = os.path.join(HERE, 'kipris_results_virtual_retrieval.md')
CLAIMS_MD = os.path.join(HERE, 'kipris_claims_virtual_retrieval.md')

FIELDS = ['inventionTitle', 'applicantName', 'applicationNumber',
          'registerStatus', 'ipcNumber', 'astrtCont',
          'registerNumber', 'openNumber', 'applicationDate']

# ── 청구항 전문 확보 대상 ──────────────────────────────────────────
# 260909 Tanalysis 보고서 2건에서 새로 등장했거나 아직 청구항 미확보인 건.
CLAIM_LOOKUP = [
    # 가상 회수 검증 보고서에서 등장
    ('심보틱-팔레트화재계획(KR20250043453A)', '1020257005300'),
    ('현대차기아-물류적재작업제어(KR20260001669A)', '1020240084922'),
    ('로젠솔루션-혼합적재시뮬레이터(KR20190017133A)', '1020170101473'),
    # 버퍼 연계 보고서에서 등장
    ('브릴스-파렛타이징물품적재(KR102901586B1)', '1020240195453'),
    ('애자일소다-팔레타이징시스템(KR102641856B1)', '1020230079965'),
    # 재확인(비교표 근거 대조용)
    ('Mujin-실시간배치시뮬레이션(KR102332603B1)', '1020200065211'),
    ('심보틱-유연시퀀싱(KR102934201B1)', '1020247020877'),
]

# ── 키워드 스윕 ────────────────────────────────────────────────────
# (라벨, 필드, 검색어, IPC)
# 필드: astrtCont=초록 / claimScope=청구범위 / inventionTitle=명칭
# 연산자: '*' = AND
QUERIES = [
    # D1: 회수 순서를 고려한 임시 적재
    ('D1-회수순서-적재', 'astrtCont', '회수*순서*적재', None),
    ('D1-반출순서-적재', 'astrtCont', '반출*순서*적재', None),
    ('D1-인출순서-적재', 'astrtCont', '인출*순서*적재', None),
    ('D1-출고순서-임시', 'astrtCont', '출고*순서*임시', None),
    ('D1-임시적재-회수', 'astrtCont', '임시*적재*회수', None),
    ('D1-버퍼-회수순서', 'astrtCont', '버퍼*회수*순서', None),
    ('D1-재배치-순서-B65G', 'astrtCont', '재배치*순서', 'B65G'),
    ('D1-청구-회수순서적재', 'claimScope', '회수*순서*적재', None),
    ('D1-청구-임시적재회수', 'claimScope', '임시*적재*회수', None),
    # D2: 제거 후 잔여 안정성
    ('D2-제거-안정성', 'astrtCont', '제거*안정성', None),
    ('D2-반출-안정성', 'astrtCont', '반출*안정성', None),
    ('D2-붕괴-적재', 'astrtCont', '붕괴*적재', None),
    ('D2-전복-적재', 'astrtCont', '전복*적재', None),
    ('D2-잔여-안정성', 'astrtCont', '잔여*안정', None),
    ('D2-청구-제거안정성', 'claimScope', '제거*안정성', None),
    # D3: 회수 시 접근·파지 가능성
    ('D3-접근가능-파지', 'astrtCont', '접근*파지', None),
    ('D3-흡착-회수', 'astrtCont', '흡착*회수', None),
    ('D3-가림-박스', 'astrtCont', '가림', 'B65G'),
    ('D3-차단-회수', 'astrtCont', '차단*회수', 'B65G'),
    ('D3-간섭-회수', 'astrtCont', '간섭*회수', None),
    ('D3-청구-접근파지', 'claimScope', '접근*파지', 'B65G'),
    # D4: 회수 경로 충돌
    ('D4-경로-충돌-회수', 'astrtCont', '경로*충돌*회수', None),
    ('D4-경로-충돌-적재', 'astrtCont', '경로*충돌*적재', None),
    ('D4-충돌검사-팔레트', 'astrtCont', '충돌*팔레트', 'B25J'),
    # D5/D6: 오차 반영 재검증
    ('D5-오차-재계획', 'astrtCont', '오차*재계획', None),
    ('D5-오차-적재', 'astrtCont', '오차*적재', 'B65G'),
    ('D5-실제위치-보정-적재', 'astrtCont', '보정*적재*위치', 'B25J'),
    ('D6-적재확인-순서', 'astrtCont', '확인*적재*순서', 'B65G'),
    # 시뮬레이션 기반 검증 일반
    ('SIM-시뮬레이션-적재-검증', 'astrtCont', '시뮬레이션*적재*검증', None),
    ('SIM-가상-적재-검증', 'astrtCont', '가상*적재*검증', None),
    ('SIM-디지털트윈-적재', 'astrtCont', '디지털*트윈*적재', None),
    # 디팔레타이징(꺼내는 쪽) — 회수 순서 판정이 여기 있을 수 있다
    ('DP-디팔레타이징-순서', 'astrtCont', '디팔레타이징*순서', None),
    ('DP-하차-순서-안정', 'astrtCont', '하차*순서', 'B65G'),
    ('DP-제목-디팔레타이징', 'inventionTitle', '디팔레타이징', None),
    # 명칭 직접
    ('T-제목-가상회수', 'inventionTitle', '가상*회수', None),
    ('T-제목-회수순서', 'inventionTitle', '회수*순서', None),
    ('T-제목-임시팔레트', 'inventionTitle', '임시*팔레트', None),
]

# ── CPC 서브그룹 전수 열람 ─────────────────────────────────────────
# B65G57/03, B65G57/22는 팔레타이징 조사(6차 개정)에서 이미 전수 열람했다.
# 여기서는 '꺼내기/저장·인출' 쪽 서브그룹을 새로 본다.
SUBGROUP_SWEEP = [
    'B65G59/02',    # 스택에서 물품을 하나씩 분리(디스태킹)
    'B65G61/00',    # 팔레타이징/디팔레타이징 조합 장치
    'B65G1/04',     # 창고 저장·인출 장치
    'B65G1/137',    # 창고 재고·인출 순서 제어
    'B25J9/16',     # 로봇 프로그램 제어(넓음 — 건수 먼저 확인)
]


def load_key(argv_key=None):
    if argv_key:
        return argv_key.strip()
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


def fetch(url, timeout=30):
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'kipris-vr/1.0'})
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


def run_check(key):
    url = build_adv_url('astrtCont', '팔레타이징', key, ipc='B65G')
    print(f'[확인] {OP_ADV} (초록=팔레타이징, IPC=B65G)')
    ok, body, err = fetch(url)
    if not ok:
        print(f'  실패: {err}')
        return False
    status, items, total = parse_items(body)
    print(f'  {status} / totalCount={total} / item={len(items)}')
    return bool(items)


def run_sweep(key):
    per_query = []
    seen = {}
    for label, field, value, ipc in QUERIES:
        url = build_adv_url(field, value, key, ipc=ipc)
        ok, body, err = fetch(url)
        if not ok:
            print(f'[{label}] 요청 실패: {err}')
            per_query.append((label, field, value, ipc, f'실패: {err}', 0, []))
            time.sleep(SLEEP_SEC)
            continue
        status, items, total = parse_items(body)
        print(f'[{label}] {field}={value} ipc={ipc or "-"} → total={total} item={len(items)}')
        for rec in items:
            app = rec.get('applicationNumber') or rec.get('registerNumber')
            if app and app not in seen:
                seen[app] = rec
        per_query.append((label, field, value, ipc, status, total, items))
        time.sleep(SLEEP_SEC)
    return per_query, seen


def run_subgroup(key):
    out = []
    for sg in SUBGROUP_SWEEP:
        url = build_adv_url('inventionTitle', '', key, ipc=sg)
        ok, body, err = fetch(url)
        if not ok:
            print(f'[서브그룹 {sg}] 실패: {err}')
            out.append((sg, f'실패: {err}', 0, []))
            time.sleep(SLEEP_SEC)
            continue
        status, items, total = parse_items(body)
        print(f'[서브그룹 {sg}] total={total} item={len(items)}')
        out.append((sg, status, total, items))
        time.sleep(SLEEP_SEC)
    return out


def _row(rec):
    title = (rec.get('inventionTitle') or '').replace('|', '/')
    return (f"| {rec.get('applicationNumber','')} | {title[:70]} | "
            f"{(rec.get('applicantName') or '')[:28]} | "
            f"{rec.get('registerStatus','')} | {rec.get('applicationDate','')} |")


def write_sweep_md(per_query, seen, subgroups):
    lines = ['# KIPRIS 스윕 결과 — 가상 회수 검증 기반 혼합 박스 적재 제어',
             '',
             '> 생성: `tools/kipris_search_virtual_retrieval.py --sweep --subgroup`',
             '> 초록(astrtCont)/청구범위(claimScope)/명칭 키워드 + CPC 서브그룹 전수 열람.',
             '> **예비검색이며 법적 클리어런스가 아니다.**',
             '']
    lines.append(f'## 0. 중복 제거 후 고유 문헌 {len(seen)}건')
    lines.append('')
    lines.append('| 출원번호 | 발명의 명칭 | 출원인 | 상태 | 출원일 |')
    lines.append('|---|---|---|---|---|')
    for rec in sorted(seen.values(),
                      key=lambda r: r.get('applicationDate', ''), reverse=True):
        lines.append(_row(rec))
    lines.append('')
    lines.append('## 1. 질의별 결과')
    for label, field, value, ipc, status, total, items in per_query:
        lines.append('')
        lines.append(f'### {label} — `{field}={value}` ipc={ipc or "(제한없음)"}')
        lines.append(f'- {status} / totalCount={total} / 반환 {len(items)}건')
        if not items:
            lines.append('- (해당 없음)')
            continue
        lines.append('')
        lines.append('| 출원번호 | 발명의 명칭 | 출원인 | 상태 | 출원일 |')
        lines.append('|---|---|---|---|---|')
        for rec in items:
            lines.append(_row(rec))
    if subgroups:
        lines.append('')
        lines.append('## 2. CPC 서브그룹 전수 열람')
        for sg, status, total, items in subgroups:
            lines.append('')
            lines.append(f'### {sg}')
            lines.append(f'- {status} / totalCount={total} / 반환 {len(items)}건')
            if total > NUM_ROWS:
                lines.append(f'- **주의: 전체 {total}건 중 상위 {NUM_ROWS}건만 반환됨 '
                             f'— 전수 열람 아님**')
            if not items:
                lines.append('- (해당 없음)')
                continue
            lines.append('')
            lines.append('| 출원번호 | 발명의 명칭 | 출원인 | 상태 | 출원일 |')
            lines.append('|---|---|---|---|---|')
            for rec in items:
                lines.append(_row(rec))
    with open(SWEEP_MD, 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines) + '\n')
    print(f'\n스윕 결과 → {SWEEP_MD} (고유 {len(seen)}건)')


def fetch_full_detail(app_number, key):
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
    return {
        'title': root.findtext('.//inventionTitle') or '',
        'applicant': root.findtext('.//applicantInfo/name') or '',
        'status': root.findtext('.//registerStatus') or '',
        'appDate': root.findtext('.//applicationDate') or '',
        'openNumber': root.findtext('.//openNumber') or '',
        'registerNumber': root.findtext('.//registerNumber') or '',
        'ipc': ' / '.join(t.text.strip() for t in root.findall('.//ipcInfo/ipcNumber')
                          if t.text),
        'abstract': root.findtext('.//abstractInfo/astrtCont') or '',
        'claims': [c.text for c in root.findall('.//claimInfo/claim') if c.text],
    }, None


def run_claims(key):
    lines = ['# 청구항 전문 원본 — 가상 회수 검증 주제',
             '',
             '> `tools/kipris_search_virtual_retrieval.py --claims`',
             '> 오퍼레이션: `getBibliographyDetailInfoSearch` (출원번호 → 청구항 전문).',
             '> 공개(A) 단계 문헌은 청구항 전문이 반환되지 않을 수 있다.',
             '']
    ok_count = 0
    for label, appno in CLAIM_LOOKUP:
        info, err = fetch_full_detail(appno, key)
        if not info:
            print(f'[청구항 {label}] {appno} → 실패: {err}')
            lines.append(f'\n## {label} ({appno}) — 실패: {err}\n')
            time.sleep(SLEEP_SEC)
            continue
        ok_count += 1
        print(f'[청구항 {label}] {appno} → {info["title"][:40]} '
              f'/ {info["status"]} / 청구항 {len(info["claims"])}개')
        lines.append(f'\n## {label}\n')
        lines.append(f'- 출원번호: {appno} · 출원일: {info["appDate"]} · '
                     f'출원인: {info["applicant"]} · 상태: {info["status"]}')
        lines.append(f'- 공개번호: {info["openNumber"]} · 등록번호: {info["registerNumber"]}')
        lines.append(f'- IPC: {info["ipc"]}')
        lines.append(f'- 발명의 명칭: **{info["title"]}**')
        if info['abstract']:
            lines.append(f'\n<초록>\n{info["abstract"]}\n')
        if info['claims']:
            lines.append(f'\n<청구항 {len(info["claims"])}개>\n')
            for c in info['claims']:
                lines.append(c)
                lines.append('')
        else:
            lines.append('\n**청구항 전문 미반환** (공개 단계이거나 API 미제공)\n')
        time.sleep(SLEEP_SEC)
    with open(CLAIMS_MD, 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines) + '\n')
    print(f'\n{ok_count}/{len(CLAIM_LOOKUP)}건 조회 성공 — {CLAIMS_MD}')


def main():
    argv = sys.argv[1:]
    argv_key = None
    if '--key' in argv:
        i = argv.index('--key')
        if i + 1 < len(argv):
            argv_key = argv[i + 1]
    key = load_key(argv_key)
    if not key:
        print('서비스키가 없다. tools/.kipris_key 또는 KIPRIS_SERVICE_KEY 또는 --key')
        return 2
    do_all = '--all' in argv or not any(
        a in argv for a in ('--check', '--claims', '--sweep', '--subgroup'))
    if '--check' in argv or do_all:
        if not run_check(key):
            print('키 확인 단계에서 결과가 비었다. 키/쿼터를 확인할 것.')
    if '--claims' in argv or do_all:
        run_claims(key)
    if '--sweep' in argv or '--subgroup' in argv or do_all:
        per_query, seen = ([], {})
        if '--sweep' in argv or do_all:
            per_query, seen = run_sweep(key)
        subgroups = []
        if '--subgroup' in argv or do_all:
            subgroups = run_subgroup(key)
        write_sweep_md(per_query, seen, subgroups)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
