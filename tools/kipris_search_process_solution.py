#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""KIPRIS 국내 선행조사 — 공정 솔루션 각도(실패 트리아지·무정지 복구·운영자 인계).

'공정 페인→솔루션 역설계' 각도. 페인: 로봇 실패 시 셀 전체 정지 후에만 사람 개입 가능.
솔루션: 유형화 실패 트리아지 + 선택적 운영자 인계 + 대상 격리 후 무정지 계속.
실행:  python3 tools/kipris_search_process_solution.py  # → tools/kipris_results_process_solution.md
"""
import os, time, urllib.parse, urllib.request, xml.etree.ElementTree as ET

BASE = 'http://plus.kipris.or.kr'
SERVICE_PATH = '/kipo-api/kipi/patUtiModInfoSearchSevice'
OP_ADV = '/getAdvancedSearch'
NUM_ROWS, PAGE_NO, SLEEP_SEC = 100, 1, 0.5
HERE = os.path.dirname(os.path.abspath(__file__))
RESULT_MD = os.path.join(HERE, 'kipris_results_process_solution.md')

QUERIES = [
    ('PS1-초록-무정지복구', 'astrtCont', '로봇*정지*없이*복구', None),
    ('PS1-초록-실패운영자인계', 'astrtCont', '로봇*실패*작업자*개입', None),
    ('PS1-초록-실패트리아지', 'astrtCont', '실패*자동*분류*처리*로봇', None),
    ('PS1-초록-대상격리계속', 'astrtCont', '로봇*건너뛰기*계속*작업', None),
    ('PS1-청구-실패복구계속', 'claimScope', '로봇*실패*복구*계속', None),
    ('PS1-초록-원격개입셀', 'astrtCont', '원격*개입*셀*로봇', None),
    ('PS1-초록-감시개입콘솔', 'astrtCont', '감시*개입*로봇*작업', None),
    ('PS2-초록-혼류무재교시', 'astrtCont', '다품종*교시*없이*로봇', None),
    ('PS2-초록-레시피교체', 'astrtCont', '레시피*품종*교체*로봇', None),
    ('PS3-초록-오조립복구', 'astrtCont', '조립*오류*검출*재작업*로봇', None),
    ('REF-청구-작업자개입로봇', 'claimScope', '작업자*개입*로봇*비전', None),
]
FIELDS = ['inventionTitle','applicantName','applicationNumber','registerStatus',
          'ipcNumber','astrtCont','registerNumber','openNumber']


def load_key():
    env = os.environ.get('KIPRIS_SERVICE_KEY','').strip()
    if env: return env
    kf = os.path.join(HERE,'.kipris_key')
    return open(kf,encoding='utf-8').readline().strip() if os.path.exists(kf) else ''


def build(field,value,key,ipc=None):
    p={field:value,'patent':'true','utility':'true','numOfRows':NUM_ROWS,'pageNo':PAGE_NO,'ServiceKey':key}
    if ipc: p['ipcNumber']=ipc
    return f'{BASE}{SERVICE_PATH}{OP_ADV}?'+urllib.parse.urlencode(p)


def fetch(url,timeout=25):
    try:
        req=urllib.request.Request(url,headers={'User-Agent':'kipris/2'})
        with urllib.request.urlopen(req,timeout=timeout) as r:
            return True,r.read().decode('utf-8','replace'),''
    except Exception as e:
        return False,'',repr(e)


def ft(node,tag):
    for el in node.iter(tag):
        if el.text and el.text.strip(): return el.text.strip()
    return ''


def parse(x):
    try: root=ET.fromstring(x)
    except ET.ParseError as e: return f'파싱실패:{e}',[],0
    tot=ft(root,'totalCount') or '0'
    items=[]
    for it in root.iter('item'):
        rec={f:(it.findtext(f) or '').strip() for f in FIELDS}
        for f in FIELDS:
            if not rec[f]: rec[f]=ft(it,f)
        items.append(rec)
    try: n=int(tot)
    except ValueError: n=len(items)
    return f'successYN={ft(root,"successYN") or "?"}',items,n


def glink(rec):
    num=(rec.get('registerNumber') or rec.get('applicationNumber') or '').replace('-','')
    return f'https://patents.google.com/?q=KR{num}&country=KR' if num else ''


def run(key):
    by_app,order,per={}, [], []
    for label,field,value,ipc in QUERIES:
        ok,body,err=fetch(build(field,value,key,ipc))
        if not ok:
            print(f'[{label}] 실패:{err}'); per.append((label,f'{field}:{value}',-1,0)); time.sleep(SLEEP_SEC); continue
        st,items,tot=parse(body)
        per.append((label,f'{field}:{value}',tot,len(items)))
        print(f'[{label}] {field}="{value}" → 총 {tot}(수신 {len(items)})' + (' ⚠캡초과' if tot>len(items) else ''))
        for rec in items:
            app=rec.get('applicationNumber') or rec.get('registerNumber') or rec.get('inventionTitle')
            if not app: continue
            if app not in by_app: by_app[app]=(set(),rec); order.append(app)
            by_app[app][0].add(label)
        time.sleep(SLEEP_SEC)
    order.sort(key=lambda a:(0 if '등록' in (by_app[a][1].get('registerStatus') or '') else 1, by_app[a][1].get('inventionTitle') or ''))
    _md(order,by_app,per)
    print(f'\n총 {len(order)}건 — {RESULT_MD}')
    for a in order[:15]:
        lb,rec=by_app[a]
        print(f'  - [{rec.get("registerStatus") or "?"}] {(rec.get("inventionTitle") or "")[:44]} ({rec.get("applicantName") or "?"}) [{",".join(sorted(lb))}]')


def _row(a,by_app):
    lb,rec=by_app[a]
    link=glink(rec)
    return (f'| {rec.get("registerStatus") or ""} | {(rec.get("inventionTitle") or "").replace("|","/")} | '
            f'{(rec.get("applicantName") or "").replace("|","/")} | {rec.get("applicationNumber") or ""} | '
            f'{(rec.get("ipcNumber") or "").split("|")[0][:14]} | {",".join(sorted(lb))} | '
            f'{"[열기]("+link+")" if link else ""} |')


def _md(order,by_app,per):
    L=['# KIPRIS 공정 솔루션(실패 트리아지·무정지 복구) 국내 선행\n',
       '- ⚠ 예비검색. 전체요소 대조는 변리사. 한국은 전세계 신규성.\n',
       '\n## 쿼리별 총건수 (0=국내 무검출 신호)\n','| 라벨 | 검색 | 총 | 수신 |','|---|---|--:|--:|']
    for label,q,tot,got in per: L.append(f'| {label} | {q} | {tot} | {got} |')
    L+=['\n## 결과 (등록 우선)\n','| 상태 | 명칭 | 출원인 | 출원번호 | IPC | 매칭 | 링크 |','|---|---|---|---|---|---|---|']
    for a in order: L.append(_row(a,by_app))
    L.append('\n## 초록 발췌\n')
    for a in order:
        rec=by_app[a][1]; ab=(rec.get('astrtCont') or '').strip()
        if not ab: continue
        L.append(f'**{rec.get("inventionTitle") or "(제목없음)"}** ({rec.get("applicationNumber") or ""}) — {",".join(sorted(by_app[a][0]))}  ')
        L.append(ab[:420]+('…' if len(ab)>420 else '')+'\n')
    open(RESULT_MD,'w',encoding='utf-8').write('\n'.join(L))


if __name__=='__main__':
    k=load_key()
    if not k: raise SystemExit('✗ 키 없음: tools/.kipris_key')
    run(k)
