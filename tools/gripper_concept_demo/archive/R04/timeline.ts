export const DURATION = 36;
export const PRESETS = [
  {
    id: "m6",
    label: "M6 × 20",
    diameter: 0.006,
    length: 0.02,
    headWidth: 0.01,
    headHeight: 0.004,
  },
  {
    id: "m8",
    label: "M8 × 35",
    diameter: 0.008,
    length: 0.035,
    headWidth: 0.013,
    headHeight: 0.0053,
  },
  {
    id: "m10",
    label: "M10 × 50",
    diameter: 0.01,
    length: 0.05,
    headWidth: 0.017,
    headHeight: 0.0064,
  },
] as const;
export type BoltSpec = (typeof PRESETS)[number];
export const STAGES = [
  {
    start: 0,
    end: 3,
    name: "볼트 접근",
    short: "접근",
    text: "접근 가능한 볼트의 헤드 가까운 몸통을 향해 이동합니다. 주변 볼트는 배경으로 고정되어 있습니다.",
    part: "관절식 주집게 2개",
  },
  {
    start: 3,
    end: 5,
    name: "몸통 파지",
    short: "파지",
    text: "두 주집게가 누워 있는 볼트의 헤드 가까운 몸통을 잡습니다.",
    part: "관절형 주집게",
  },
  {
    start: 5,
    end: 8,
    name: "무더기에서 인출",
    short: "인출",
    text: "집게의 파지를 유지한 채 볼트를 들어 올립니다. 정렬은 통 밖의 여유 공간에서 진행합니다.",
    part: "로봇팔 · 집게",
  },
  {
    start: 8,
    end: 10,
    name: "보조 엄지 접근",
    short: "받침",
    text: "작은 엄지가 두 관절을 움직여 볼트 끝부분 위에 닿습니다. 엄지가 받친 뒤 집게의 파지력을 낮춰 회전을 허용합니다.",
    part: "2관절 엄지 · 접촉 패드",
  },
  {
    start: 10,
    end: 14,
    name: "보조 엄지로 세우기",
    short: "세움",
    text: "주집게가 몸통을 가볍게 유지하고, 보조 엄지가 볼트 끝부분을 아래로 눌러 약 90° 세웁니다. 파지점을 중심으로 회전해 헤드는 위, 나사 끝은 아래로 향합니다.",
    part: "2관절 보조 엄지",
  },
  {
    start: 14,
    end: 16,
    name: "헤드 척 닫기",
    short: "헤드",
    text: "수직이 된 볼트를 집게로 다시 조인 뒤 헤드 척을 닫습니다. 육각면의 각도가 맞은 상태를 가정합니다.",
    part: "가변 3조 헤드 척",
  },
  {
    start: 16,
    end: 18,
    name: "파지 인계 · 간섭 회피",
    short: "인계",
    text: "헤드 척이 잡은 뒤 주집게를 열고 보조 엄지를 중앙 옆으로 접습니다. 척이 앞으로 나와 볼트를 집게 끝보다 아래에 둡니다.",
    part: "집게 열림 · 엄지 접힘 · 척 전진",
  },
  {
    start: 18,
    end: 23,
    name: "체결 위치 이동",
    short: "이동",
    text: "볼트를 유지한 채 체결판 위로 이동합니다. 확대 보기에서 헤드가 척에 유지되는 모습을 확인하세요.",
    part: "로봇팔 · 헤드 척",
  },
  {
    start: 23,
    end: 29,
    name: "회전하며 체결",
    short: "체결",
    text: "척과 볼트가 함께 회전하고 로봇팔이 전진합니다. 삽입량에 따른 회전은 설명용이며 토크는 계산하지 않습니다.",
    part: "회전 구동축",
  },
  {
    start: 29,
    end: 31,
    name: "헤드 해제",
    short: "해제",
    text: "볼트가 체결판에 자리 잡은 뒤 헤드 척을 엽니다. 볼트는 작업물에 남습니다.",
    part: "가변 헤드 척",
  },
  {
    start: 31,
    end: 36,
    name: "복귀",
    short: "복귀",
    text: "로봇팔이 작업물에서 물러나 대기 위치로 돌아옵니다. 처음으로 버튼으로 다시 확인할 수 있습니다.",
    part: "로봇팔",
  },
];
export function ramp(time: number, a: number, b: number) {
  const v = Math.max(0, Math.min(1, (time - a) / (b - a)));
  return v * v * (3 - 2 * v);
}
export function sampleCycle(input: number) {
  const time = Math.max(
    0,
    Math.min(DURATION, Number.isFinite(input) ? input : 0),
  );
  const stage = Math.min(
    STAGES.length - 1,
    STAGES.findIndex((s) => time < s.end) < 0
      ? STAGES.length - 1
      : STAGES.findIndex((s) => time < s.end),
  );
  const fingerClosed = ramp(time, 3, 5) * (1 - ramp(time, 16, 17));
  const chuckClosed = ramp(time, 14.5, 16) * (1 - ramp(time, 29, 31));
  const inserted = ramp(time, 23, 29);
  return {
    time,
    stage,
    fingerClosed,
    chuckClosed,
    rodEngaged: ramp(time, 8, 9) * (1 - ramp(time, 16, 17)),
    gripForce:
      fingerClosed *
      (1 - 0.75 * ramp(time, 9, 10) * (1 - ramp(time, 14, 14.5))),
    align: ramp(time, 10, 14),
    clear: ramp(time, 17, 18),
    spindle: inserted * Math.PI * 12,
    inserted,
    owner:
      time < 5 ? "bin" : time < 16 ? "fingers" : time < 29 ? "chuck" : "plate",
    finished: time === DURATION,
  };
}
export type CycleState = ReturnType<typeof sampleCycle>;
