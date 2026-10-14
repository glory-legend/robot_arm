#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""KIPRIS 국내 선행조사 — 추가 20 특허후보(N1~N20)의 구별 개념.

기존 S1~S3·T1~T4·PS1~PS3·후보A·C1~C6·물리실패27종과 겹치지 않는 신규 후보의
국내 개별개시 여부를 1차 확인. → tools/kipris_results_more20.md
"""
import os, time, urllib.parse, urllib.request, xml.etree.ElementTree as ET
BASE='http://plus.kipris.or.kr'; SP='/kipo-api/kipi/patUtiModInfoSearchSevice'; OP='/getAdvancedSearch'
NR,PG,SL=100,1,0.5; HERE=os.path.dirname(os.path.abspath(__file__))
RESULT_MD=os.path.join(HERE,'kipris_results_more20.md')

QUERIES=[
 # 통신·시간·상관 계층
 ('N1-초록-이중시계정지구분','astrtCont','시뮬레이션*시계*정지*로봇',None),
 ('N2-초록-지령유효시각폐기','astrtCont','인식*시각*폐기*로봇',None),
 ('N3-초록-일련번호유실검출','astrtCont','일련번호*유실*텔레메트리',None),
 ('N4-초록-재매칭오상관방지','astrtCont','로봇*재매칭*좌표*센싱',None),
 # 모델무관·capability
 ('N5-초록-기종무관계약','astrtCont','로봇*기종*무관*메시지',None),
 ('N6-청구-capability협상','claimScope','로봇*모델*관절*프레임*협상',None),
 # 학습·탐험
 ('N7-초록-콜드스타트게이트','astrtCont','학습*준비*게이트*파지',None),
 ('N8-초록-대역예산텔레메트리','astrtCont','대역폭*예산*스트림*로봇',None),
 ('N9-초록-저신뢰보류재관측','astrtCont','신뢰도*낮음*보류*재관측*로봇',None),
 # 공정 솔루션(신규)
 ('N10-초록-트레이빈검증','astrtCont','트레이*비움*확인*로봇',None),
 ('N11-초록-불안정배치리젝트','astrtCont','적재*불안정*리젝트*로봇',None),
 ('N12-초록-공구자동교체결정','astrtCont','로봇*공구*자동*교체*품종',None),
 ('N13-초록-소모품보충점유맵','astrtCont','인서트*보충*점유*로봇',None),
 ('N14-초록-초품검사게이트','astrtCont','초도품*검사*로트*보류*로봇',None),
 ('N15-초록-층간스페이서삽입','astrtCont','적재*층간*스페이서*삽입*로봇',None),
 ('N16-초록-빈용기재적층','astrtCont','빈*용기*재적층*로봇',None),
 ('N17-초록-라인사이드보충','astrtCont','라인사이드*보충*로봇*소비',None),
 # 데이터·UX·안전
 ('N18-초록-섀도우감시전용','astrtCont','디지털*섀도우*지연*감시*로봇',None),
 ('N19-초록-운영자결정학습','astrtCont','작업자*결정*학습*피드백*로봇',None),
 ('N20-청구-개입라벨방화벽','claimScope','작업자*개입*라벨*학습',None),
]
FIELDS=['inventionTitle','applicantName','applicationNumber','registerStatus','ipcNumber','astrtCont','registerNumber','openNumber']

def load_key():
    e=os.environ.get('KIPRIS_SERVICE_KEY','').strip()
    if e:return e
    kf=os.path.join(HERE,'.kipris_key')
    return open(kf,encoding='utf-8').readline().strip() if os.path.exists(kf) else ''

def build(f,v,k,ipc=None):
    p={f:v,'patent':'true','utility':'true','numOfRows':NR,'pageNo':PG,'ServiceKey':k}
    if ipc:p['ipcNumber']=ipc
    return f'{BASE}{SP}{OP}?'+urllib.parse.urlencode(p)

def fetch(u,t=25):
    try:
        r=urllib.request.Request(u,headers={'User-Agent':'kipris/2'})
        with urllib.request.urlopen(r,timeout=t) as x:return True,x.read().decode('utf-8','replace'),''
    except Exception as e:return False,'',repr(e)

def ft(n,tag):
    for el in n.iter(tag):
        if el.text and el.text.strip():return el.text.strip()
    return ''

def parse(x):
    try:root=ET.fromstring(x)
    except ET.ParseError as e:return[],0
    tot=ft(root,'totalCount') or '0'; items=[]
    for it in root.iter('item'):
        rec={f:(it.findtext(f) or '').strip() for f in FIELDS}
        for f in FIELDS:
            if not rec[f]:rec[f]=ft(it,f)
        items.append(rec)
    try:n=int(tot)
    except ValueError:n=len(items)
    return items,n

def glink(rec):
    num=(rec.get('registerNumber') or rec.get('applicationNumber') or '').replace('-','')
    return f'https://patents.google.com/?q=KR{num}&country=KR' if num else ''

def run(k):
    by,order,per={}, [], []
    for label,f,v,ipc in QUERIES:
        ok,body,err=fetch(build(f,v,k,ipc))
        if not ok:print(f'[{label}] 실패:{err}');per.append((label,f'{f}:{v}',-1,0));time.sleep(SL);continue
        items,tot=parse(body); per.append((label,f'{f}:{v}',tot,len(items)))
        print(f'[{label}] {f}="{v}" → 총 {tot}(수신 {len(items)})'+(' ⚠캡' if tot>len(items) else ''))
        for rec in items:
            a=rec.get('applicationNumber') or rec.get('registerNumber') or rec.get('inventionTitle')
            if not a:continue
            if a not in by:by[a]=(set(),rec);order.append(a)
            by[a][0].add(label)
        time.sleep(SL)
    order.sort(key=lambda a:(0 if '등록' in (by[a][1].get('registerStatus') or '') else 1,by[a][1].get('inventionTitle') or ''))
    L=['# KIPRIS 추가 20후보(N1~N20) 국내 선행\n','- ⚠ 예비검색. 전세계 신규성. 0건=등록가능성↑ 신호.\n',
       '\n## 쿼리별 총건수 (0=국내 무검출)\n','| 라벨 | 검색 | 총 | 수신 |','|---|---|--:|--:|']
    for label,q,tot,got in per:L.append(f'| {label} | {q} | {tot} | {got} |')
    L+=['\n## 결과(등록 우선)\n','| 상태 | 명칭 | 출원인 | 출원번호 | IPC | 매칭 | 링크 |','|---|---|---|---|---|---|---|']
    for a in order:
        lb,rec=by[a]; ln=glink(rec)
        L.append(f'| {rec.get("registerStatus") or ""} | {(rec.get("inventionTitle") or "").replace("|","/")} | {(rec.get("applicantName") or "").replace("|","/")} | {rec.get("applicationNumber") or ""} | {(rec.get("ipcNumber") or "").split("|")[0][:14]} | {",".join(sorted(lb))} | {"[열기]("+ln+")" if ln else ""} |')
    open(RESULT_MD,'w',encoding='utf-8').write('\n'.join(L))
    print(f'\n총 {len(order)}건 — {RESULT_MD}')

if __name__=='__main__':
    k=load_key()
    if not k:raise SystemExit('✗ 키 없음')
    run(k)
