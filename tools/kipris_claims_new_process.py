#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""KIPRIS 청구항 전문 조회 — 새 공정 후보(C1 키팅·C2 디네스팅)의 국내 근접 선행.

getBibliographyDetailInfoSearch(출원번호 → 청구항 전문)로 아래 등록건의 청구항을 받아
`tools/kipris_claims_new_process.md`에 원문 그대로 저장한다. 우리 구성과의 요소별
대조(claim chart)는 결과 md 를 보고 사람이/후속 분석이 수행한다.

대상:
  - 덱스테러티 "로봇 키팅 기계" (C1 최근접): 1020227013599
  - 윈텍오토메이션 "CVD 코팅 트레이 초경인서트 분리 배큠 그립퍼" (C2 최근접): 1020210050884
  - 웍스탭 "스마트 키팅 시스템" (C1 대조 — SW/물류 여부 확인): 1020230048927

실행:  python3 tools/kipris_claims_new_process.py
주의: 예비조사다. 법적상태·전체요소 대조는 변리사가 KIPRIS 원부로 확인.
"""
import os
import time
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET

BASE = 'http://plus.kipris.or.kr'
SERVICE_PATH = '/kipo-api/kipi/patUtiModInfoSearchSevice'
OP_DETAIL = '/getBibliographyDetailInfoSearch'
SLEEP_SEC = 0.5
HERE = os.path.dirname(os.path.abspath(__file__))
CLAIMS_MD = os.path.join(HERE, 'kipris_claims_new_process.md')

CLAIM_LOOKUP = [
    ('C1-덱스테러티-로봇키팅기계', '1020227013599'),
    ('C2-윈텍-CVD트레이배큠그립퍼', '1020210050884'),
    ('C1-웍스탭-스마트키팅시스템', '1020230048927'),
]


def load_key():
    env = os.environ.get('KIPRIS_SERVICE_KEY', '').strip()
    if env:
        return env
    keyfile = os.path.join(HERE, '.kipris_key')
    if os.path.exists(keyfile):
        with open(keyfile, encoding='utf-8') as f:
            return f.readline().strip()
    return ''


def fetch(url, timeout=25):
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'kipris-claims/1.0'})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return True, resp.read().decode('utf-8', errors='replace'), ''
    except Exception as exc:                       # noqa: BLE001
        return False, '', repr(exc)


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
    lines = ['# 청구항 전문 원본 — 새 공정 후보 국내 근접 선행 (C1/C2)',
             '',
             '> `tools/kipris_claims_new_process.py` · 오퍼레이션 `getBibliographyDetailInfoSearch`',
             '> ⚠ 예비조사. 전체요소 대조·법적상태는 변리사가 KIPRIS 원부로 재확인.',
             '']
    ok_count = 0
    for label, appno in CLAIM_LOOKUP:
        info, err = fetch_full_detail(appno, key)
        if not info:
            print(f'[{label}] {appno} → 실패: {err}')
            lines.append(f'\n## {label} ({appno}) — 실패: {err}\n')
            time.sleep(SLEEP_SEC)
            continue
        ok_count += 1
        print(f'[{label}] {appno} → {info["title"][:40]} / {info["status"]} '
              f'/ 청구항 {len(info["claims"])}개')
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
    print(f'\n{ok_count}/{len(CLAIM_LOOKUP)}건 청구항 전문 확보 — {CLAIMS_MD}')


if __name__ == '__main__':
    k = load_key()
    if not k:
        raise SystemExit('✗ 서비스키 없음: tools/.kipris_key 첫 줄에 키를 넣으세요.')
    run_claims(k)
