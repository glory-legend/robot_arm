#!/usr/bin/env python3
"""시각화용 프레임 로그 생성 — sim.py의 게이트·전략을 재사용하여 배치·회수 과정을
프레임 단위로 기록해 JSON으로 내보낸다. HTML 뷰어가 이 JSON을 애니메이션으로 재생한다.

대표 시나리오(종래 T0는 재배치가 많고 발명 T3는 적은 케이스)를 자동 선택한다.
"""
import json
import os
import random
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import sim  # noqa: E402
from run_experiment import make_scenario, run_one  # noqa: E402


def snap(buf):
    return [[{'id': b.id, 'order': b.order, 'width': b.width} for b in st]
            for st in buf.stacks]


def place_phase(strategy, boxes, S, H, frames):
    buf = sim.Buffer(S, H)
    frames.append({'stacks': snap(buf), 'cap': f'적재 시작', 'hl': None,
                   'reloc': 0, 'phase': '적재'})
    for b in boxes:
        s, _ = sim.choose_stack(strategy, buf, b)
        buf.stacks[s].append(b.clone())
        frames.append({
            'stacks': snap(buf),
            'cap': f'신규 박스(회수순서 {b.order}) → 스택 {s} 배치',
            'hl': {'s': s, 'i': buf.height(s) - 1, 'kind': 'place'},
            'reloc': 0, 'phase': '적재'})
    return buf


def retrieve_phase(strategy, buf, frames):
    """sim.evaluate_retrieval과 동일 정책을 프레임 기록판으로 재구현."""
    reloc = 0
    orders = sorted(b.order for st in buf.stacks for b in st)
    for target in orders:
        loc = sim._find(buf, target)
        if loc is None:
            continue
        s, idx = loc
        # 대상 위 박스 재배치
        while buf.height(s) - 1 > idx:
            mv = buf.top(s)
            dest = sim._reloc_dest(buf, s, mv)
            if dest is None:
                break
            buf.stacks[dest].append(buf.stacks[s].pop())
            reloc += 1
            frames.append({
                'stacks': snap(buf),
                'cap': f'[{strategy}] 회수순서 {target} 꺼내려 위 박스(순서 {mv.order}) '
                       f'재배치: 스택 {s} → {dest}  (재배치 {reloc}회)',
                'hl': {'s': dest, 'i': buf.height(dest) - 1, 'kind': 'reloc'}})
            s, idx = sim._find(buf, target)
        # 대상 회수
        s, idx = sim._find(buf, target)
        if idx == buf.height(s) - 1:
            buf.stacks[s].pop()
            frames.append({
                'stacks': snap(buf),
                'cap': f'[{strategy}] 회수순서 {target} 회수 완료  (누적 재배치 {reloc}회)',
                'hl': {'s': s, 'i': None, 'kind': 'retrieve'}})
    frames.append({'stacks': snap(buf),
                   'cap': f'[{strategy}] 전량 회수 완료 — 총 재배치 {reloc}회',
                   'hl': None})
    return reloc


def main():
    S, H, N = 5, 5, 10
    # 대표 시나리오: T0 재배치 − T3 재배치 차이가 큰 것
    best = None
    for sc in range(400):
        rng = random.Random(20260909 + sc)
        boxes = make_scenario(rng, N)
        r0 = run_one('T0', [b.clone() for b in boxes], S, H)
        r3 = run_one('T3', [b.clone() for b in boxes], S, H)
        if r0[1] == 0 and r3[1] == 0:
            gain = r0[0] - r3[0]
            if best is None or gain > best[0]:
                best = (gain, sc, boxes, r0[0], r3[0])
    gain, sc, boxes, t0r, t3r = best

    data = {'S': S, 'H': H, 'N': N, 'scenario': sc,
            'summary': {'T0': t0r, 'T3': t3r, 'gain': gain},
            'boxes': [{'id': b.id, 'order': b.order, 'width': b.width} for b in boxes],
            'runs': {}}
    for strat in ('T0', 'T3'):
        frames = []
        buf = place_phase(strat, [b.clone() for b in boxes], S, H, frames)
        reloc = retrieve_phase(strat, buf, frames)
        data['runs'][strat] = {'frames': frames, 'relocations': reloc}

    out = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                       'results', 'frames.json')
    with open(out, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False)
    print(f'대표 시나리오 #{sc}: T0 재배치 {t0r}회 vs T3 재배치 {t3r}회 (차이 {gain})')
    print(f'프레임: T0 {len(data["runs"]["T0"]["frames"])} · '
          f'T3 {len(data["runs"]["T3"]["frames"])}')
    print(f'[저장] {out}')


if __name__ == '__main__':
    main()
