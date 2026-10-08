export const DURATION = 70;
export const PRESETS = [
  {
    id: "m6",
    label: "M6 × 20",
    diameter: 0.006,
    length: 0.02,
    headWidth: 0.01,
    headHeight: 0.004,
    pitch: 0.001,
    exampleTorque: 8,
  },
  {
    id: "m8",
    label: "M8 × 35",
    diameter: 0.008,
    length: 0.035,
    headWidth: 0.013,
    headHeight: 0.0053,
    pitch: 0.00125,
    exampleTorque: 20,
  },
  {
    id: "m10",
    label: "M10 × 50",
    diameter: 0.01,
    length: 0.05,
    headWidth: 0.017,
    headHeight: 0.0064,
    pitch: 0.0015,
    exampleTorque: 40,
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
    part: "일자형 테이퍼 집게 2개",
  },
  {
    start: 3,
    end: 5,
    name: "몸통 파지",
    short: "파지",
    text: "두 주집게가 누워 있는 볼트의 헤드 가까운 몸통을 잡습니다.",
    part: "평행 개폐 · 얇은 팁",
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
    text: "작은 엄지가 두 관절을 움직여 볼트 끝부분 위에 닿습니다. 몸통을 잡는 작은 회전 패드가 볼트의 자세 변화를 따라갑니다.",
    part: "2관절 엄지 · 접촉 패드",
  },
  {
    start: 10,
    end: 14,
    name: "보조 엄지로 세우기",
    short: "세움",
    text: "주집게의 회전 패드가 몸통을 유지하고, 보조 엄지가 볼트 끝부분을 아래로 눌러 약 90° 세웁니다. 파지점을 중심으로 회전해 헤드는 위, 나사 끝은 아래로 향합니다.",
    part: "2관절 보조 엄지",
  },
  {
    start: 14,
    end: 16,
    name: "헤드 척 닫기",
    short: "헤드",
    text: "척이 18mm 전진한 뒤 여섯 턱이 헤드의 육각면에 맞춰 닫힙니다. 같은 척이 10·13·17mm 대변을 잡습니다. 그림은 위상 정렬이 완료된 상태입니다.",
    part: "자동 조절 6조 척",
  },
  {
    start: 16,
    end: 18,
    name: "파지 인계 · 간섭 회피",
    short: "인계",
    text: "헤드 척이 잠기면 주집게를 엽니다. 파지 모듈이 뒤·위로 35mm씩 물러난 다음 엄지를 접어 작업면을 비웁니다.",
    part: "파지 인계 · 파지 모듈 후퇴",
  },
  {
    start: 18,
    end: 23,
    name: "체결 위치 이동",
    short: "이동",
    text: "헤드 척이 볼트를 유지합니다. 고정 지그의 키 홈으로 반력 탭이 들어간 뒤 체결축을 구동합니다.",
    part: "로봇팔 · 헤드 척",
  },
  {
    start: 23,
    end: 63,
    name: "회전하며 체결",
    short: "체결",
    text: "나사 피치에 맞춰 회전·전진합니다. 마지막 2초는 최종 토크 제어 구간입니다. 8·20·40Nm는 시연 목표값이며 측정값이나 권장값이 아닙니다.",
    part: "회전 구동축",
  },
  {
    start: 63,
    end: 65,
    name: "헤드 해제",
    short: "해제",
    text: "볼트가 체결판에 자리 잡은 뒤 헤드 척을 엽니다. 볼트는 작업물에 남습니다.",
    part: "가변 헤드 척",
  },
  {
    start: 65,
    end: 70,
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
export function sampleCycle(input: number, spec: BoltSpec = PRESETS[1]) {
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
  const fingerClosed = ramp(time, 3, 5) * (1 - ramp(time, 16, 16.5));
  const chuckClosed = ramp(time, 15, 16) * (1 - ramp(time, 63, 65));
  const inserted = ramp(time, 23, 61);
  return {
    time,
    stage,
    fingerClosed,
    chuckClosed,
    rodEngaged: ramp(time, 8, 9) * (1 - ramp(time, 17.5, 18)),
    gripForce: fingerClosed,
    headAdvance: ramp(time, 14, 15) * (1 - ramp(time, 64, 65)),
    docked: time >= 23 && time <= 65,
    torquePhase: time >= 61 && time < 63,
    align: ramp(time, 10, 14),
    clear: ramp(time, 16.5, 17.5),
    spindle: inserted * (spec.length / spec.pitch) * Math.PI * 2,
    inserted,
    owner:
      time < 5 ? "bin" : time < 16 ? "fingers" : time < 63 ? "chuck" : "plate",
    finished: time === DURATION,
  };
}
export type CycleState = ReturnType<typeof sampleCycle>;
