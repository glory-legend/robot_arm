import { Matrix4, Vector3 } from "three";
import { ramp, type BoltSpec } from "./timeline";
import { flangeAtPath } from "./kinematics";
import paths from "./compact-motion-data.json";
import pathsC3 from "./compact-motion-data-c3.json";
import pathsR11 from "./compact-motion-data-r11.json";

// R09 tool frame, millimetres: z0 = chuck face = seated head underside, +Z towards the bolt tip.
// The robot flange sits at z = -BODY.length. Carriage datum 0 = bolt drawn in (head in chuck).
// A slim nose carries the chuck ahead of the body, so the body clears neighbouring bolt heads.
export const BODY = { width: 61, height: 59, length: 93 } as const;
export const NOSE = { radius: 14.5, length: 12 } as const; // body front face at z = -NOSE.length
export const DRAW_IN = 14; // R08: 50
export const STOW = 32; // R08: 70. Tweezer tips end up behind the body front plate.
export const GRASP = 14; // head underside -> body grasp point
export const CHUCK = { radius: 13.8, depth: 15, jawOpen: 11.9 } as const;
// Tweezer blade: flat spring strip, thin in x (the closing direction) and wide in y. Its shank runs
// parallel to the axis outside the nose, bends in at the knee (carriage z0) and ends in a short
// flat jaw parallel to the axis, like plucking tweezers. LX = shank offset outboard of the jaw.
export const TWEEZER = {
  lx: 11.8,
  knee: 0,
  flat: 2.5, // parallel jaw length before the grasp point
  overrun: 1.5, // jaw tip beyond the grasp point
  width: 2.2, // half width (y) at the shank
  thick: 0.6, // half thickness (x) at the shank
  tipWidth: 0.6,
  tipThick: 0.25,
} as const;
// Jaw clearance from the axis when opened past the nose before retracting.
export const WIDE_GAP = NOSE.radius + 1;
export const THUMB = {
  links: [24, 24],
  base: new Vector3(-8, 21, 4),
} as const;
export const YOKE_Z = [-36, -30] as const; // carriage-relative plate span
/**
 * R10 review concepts share R09's tweezers, thumb, chuck and robot cycle; they differ in the body
 * envelope (round / octagonal), the feed drive, nose length and, for c2, a cam-linked feed stroke.
 */
export type DesignId = "r09" | "c1" | "c2" | "c3" | "r11";
export const DESIGNS = {
  r11: {
    label: "R11 · 구조 외피 · 정지 인계",
    body: { width: 60.5, height: 60.5, length: 89 },
    nose: 12,
    stow: 29,
    yokeZ: YOKE_Z,
    shape: "cyl",
    cam: false,
  },
  r09: {
    label: "R09",
    body: BODY,
    nose: 12,
    stow: STOW,
    yokeZ: YOKE_Z,
    shape: "box",
    cam: false,
  },
  c1: {
    label: "시안 1 · 원통 동축 이송",
    body: { width: 62, height: 62, length: 93 },
    nose: 12,
    stow: 32,
    yokeZ: YOKE_Z,
    shape: "cyl",
    cam: false,
  },
  c2: {
    label: "R10 · 원통 + 캠 연속 스트로크 (시안 2)",
    body: { width: 62, height: 62, length: 93 },
    nose: 12,
    stow: 32,
    yokeZ: YOKE_Z,
    shape: "cyl",
    cam: true,
  },
  c3: {
    label: "시안 3 · 롱노즈 + 모서리 모따기",
    body: { width: 61, height: 59, length: 112 },
    nose: 22,
    stow: 42,
    yokeZ: [-45, -39],
    shape: "oct",
    cam: false,
  },
} as const;
export const designOf = (id: DesignId = "r09") => DESIGNS[id];

/** Closest bolt-to-bolt pitch the nose can fasten between, for a hex head of this size. */
export const minPitch = (spec: BoltSpec) =>
  NOSE.radius + (spec.headWidth * 1000) / Math.sqrt(3) + 1;

/** Mechanism state for robot-cycle time 0-70 s. The tool returns to its t=0 state by 70 s. */
export function compactPose(
  time: number,
  spec: BoltSpec,
  id: DesignId = "r09",
) {
  const t = Math.max(0, Math.min(70, Number.isFinite(time) ? time : 0));
  const d = designOf(id);
  if (id === "r11") return lightPose(t, spec);
  if (d.cam) return camPose(t, spec);
  const extend = ramp(t, 66.5, 68.5);
  const feed = ramp(t, 15.5, 19) * (1 - extend),
    stow = ramp(t, 22, 25) * (1 - ramp(t, 65, 66.5)),
    grip = ramp(t, 3, 5),
    release = ramp(t, 20.5, 22),
    close = ramp(t, 68.5, 70);
  const closed = spec.diameter * 500 + 0.75,
    open = closed + 3;
  const lerp = (a: number, b: number, u: number) => a + (b - a) * u;
  const inserted = ramp(t, 33, 61);
  const thumbPark = ramp(t, 14, 15.5);
  return {
    time: t,
    grip,
    engaged: ramp(t, 8, 9.5) * (1 - thumbPark),
    align: ramp(t, 10, 14),
    thumbPark,
    feed,
    clamp: ramp(t, 19, 20.5) * (1 - ramp(t, 63, 65)),
    release,
    stow,
    inserted,
    spin: inserted * (spec.length / spec.pitch) * Math.PI * 2,
    carriageZ: DRAW_IN * (1 - feed) - d.stow * stow,
    // Tip offset from the axis: open -> closed on the shaft -> wide past the rim -> open again.
    gap: lerp(lerp(lerp(open, closed, grip), WIDE_GAP, release), open, close),
  };
}
export type CompactPose = ReturnType<typeof camPose>;

// R11 retains all five commanded axes. The existing grip drive opens the blades while the
// carriage dwells at the seated-head datum: no steep spreading cam, no additional actuator.
// Spring chuck release still uses 3 mm rear over-travel; reset keeps the blades wide until clear.
function lightPose(t: number, spec: BoltSpec) {
  const feed = ramp(t, 15.5, 19),
    stow = ramp(t, 22, 25);
  const over = ramp(t, 63, 64.5),
    reload = ramp(t, 65, 68.5);
  const close = ramp(t, 68.5, 70),
    grip = ramp(t, 3, 5);
  const release = ramp(t, 20.5, 22),
    thumbPark = ramp(t, 14, 15.5);
  const travel = DESIGNS.r11.stow;
  const carriageZ =
    DRAW_IN * (1 - feed) -
    travel * stow -
    3 * over +
    (DRAW_IN + travel + 3) * reload;
  const closed = spec.diameter * 500 + 0.75,
    open = closed + 3;
  const gripping = open + (closed - open) * grip;
  const wide = gripping + (WIDE_GAP - gripping) * release;
  const inserted = ramp(t, 33, 61);
  return {
    time: t,
    grip,
    engaged: ramp(t, 8, 9.5) * (1 - thumbPark),
    align: ramp(t, 10, 14),
    thumbPark,
    feed: 1 - Math.max(0, Math.min(DRAW_IN, carriageZ)) / DRAW_IN,
    clamp: ramp(t, 19, 20.5) * (1 - over),
    release,
    stow: stow * (1 - reload),
    inserted,
    spin: inserted * (spec.length / spec.pitch) * Math.PI * 2,
    carriageZ,
    gap: wide + (open - wide) * close,
  };
}

/**
 * c2: one continuous yoke stroke (carriage +14 -> -32) does draw-in, chuck close, tweezer spread
 * and stow. The chuck is spring-closed: a one-way trigger latches it shut as the yoke passes
 * carriage 0 going back, a cam spreads the tweezers over the next 0.6 mm, and a 3 mm rear
 * over-travel unlatches the chuck to release the seated bolt. No chuck-closing actuator.
 */
function camPose(t: number, spec: BoltSpec) {
  const smooth = (v: number) => {
    const x = Math.max(0, Math.min(1, v));
    return x * x * (3 - 2 * x);
  };
  const lerp = (a: number, b: number, u: number) => a + (b - a) * u;
  const stroke = DRAW_IN - (DRAW_IN + STOW) * ramp(t, 15.5, 25); // single back stroke
  const over = ramp(t, 63, 64.5),
    reload = ramp(t, 65, 68.5),
    close = ramp(t, 68.5, 70);
  const carriageZ = stroke - 3 * over + (STOW + 3 + DRAW_IN) * reload;
  const thumbPark = ramp(t, 14, 15.5);
  const grip = ramp(t, 3, 5);
  const clamp = smooth((0.8 - stroke) / 0.8) * (1 - over);
  const release = smooth(-stroke / 0.6);
  const closed = spec.diameter * 500 + 0.75,
    open = closed + 3;
  const inserted = ramp(t, 33, 61);
  return {
    time: t,
    grip,
    engaged: ramp(t, 8, 9.5) * (1 - thumbPark),
    align: ramp(t, 10, 14),
    thumbPark,
    feed: 1 - Math.max(0, Math.min(DRAW_IN, carriageZ)) / DRAW_IN,
    clamp,
    release,
    stow:
      Math.max(0, Math.min(1, (-stroke - 0.6) / (STOW - 0.6))) * (1 - reload),
    inserted,
    spin: inserted * (spec.length / spec.pitch) * Math.PI * 2,
    carriageZ,
    gap: lerp(lerp(lerp(open, closed, grip), WIDE_GAP, release), open, close),
  };
}

/** Bolt head-underside frame in tool millimetres. Pivot = body grasp point. */
export function boltToolMatrix(s: CompactPose) {
  return new Matrix4()
    .makeTranslation(0, 0, GRASP + DRAW_IN * (1 - s.feed))
    .multiply(new Matrix4().makeRotationX((-Math.PI / 2) * (1 - s.align)))
    .multiply(new Matrix4().makeTranslation(0, 0, -GRASP))
    .multiply(new Matrix4().makeRotationZ(s.spin));
}

/** Tweezer blade key points (tool mm): root on the yoke slide, knee, start of the flat jaw, tip. */
export function tweezerPoints(
  s: CompactPose,
  side: number,
  id: DesignId = "r09",
) {
  const x = side * (s.gap + TWEEZER.lx);
  return {
    root: new Vector3(x, 0, s.carriageZ + designOf(id).yokeZ[1]),
    knee: new Vector3(x, 0, s.carriageZ + TWEEZER.knee),
    bend: new Vector3(side * s.gap, 0, s.carriageZ + GRASP - TWEEZER.flat),
    tip: new Vector3(side * s.gap, 0, s.carriageZ + GRASP + TWEEZER.overrun),
  };
}

/** Planar 2R thumb in the y-z plane at x = THUMB.base.x. Parked folded back, roller above the bolt. */
export function thumbPose(s: CompactPose, spec: BoltSpec) {
  const base = THUMB.base.clone().add(new Vector3(0, 0, s.carriageZ));
  const park = base.clone().add(new Vector3(0, 3, 0));
  const a = (-Math.PI / 2) * (1 - s.align),
    r = spec.diameter * 500 + 2;
  const contact = new Vector3(0, 0, spec.length * 1000 - 2).applyMatrix4(
    boltToolMatrix({ ...s, spin: 0 }),
  );
  contact.add(new Vector3(0, Math.cos(a) * r, Math.sin(a) * r));
  contact.x = base.x;
  const tip = park.clone().lerp(contact, s.engaged);
  const delta = tip.clone().sub(base),
    d = delta.length();
  const [l1, l2] = THUMB.links;
  if (d > l1 + l2 || d < Math.abs(l1 - l2) + 0.01)
    throw new Error("R09 thumb target outside its reach");
  // Law of cosines; elbow on the right of base->tip: behind the base when parked,
  // swinging out in front of the tool while it reaches the bolt.
  const along = (l1 * l1 - l2 * l2 + d * d) / (2 * d);
  const h = Math.sqrt(Math.max(0, l1 * l1 - along * along));
  const perpendicular = new Vector3(0, delta.z, -delta.y).normalize();
  const elbow = base
    .clone()
    .addScaledVector(delta, along / d)
    .addScaledVector(perpendicular, h);
  return { base, elbow, tip };
}

// Flange pose follows the R09 path generated for this tool length.
export function compactJoints(
  time: number,
  id: BoltSpec["id"],
  design: DesignId = "r09",
) {
  const frames = (
    design === "c3" ? pathsC3 : design === "r11" ? pathsR11 : paths
  )[id];
  const idx = Math.min(frames.length - 2, Math.max(0, Math.floor(time * 10)));
  const a = frames[idx],
    b = frames[idx + 1];
  const f = Math.max(0, Math.min(1, (time - a[0]) / (b[0] - a[0])));
  return a.slice(1).map((v, i) => v + (b[i + 1] - v) * f);
}

/** Bolt world matrix (metres). Before the grip closes it rests in the bin; after release it stays seated. */
export function compactBoltWorld(
  time: number,
  spec: BoltSpec,
  design: DesignId = "r09",
) {
  const hold = time < 5 ? [3, 5] : time >= 63 ? [63, 63] : [time, time];
  return flangeAtPath(compactJoints(hold[0], spec.id, design))
    .multiply(
      new Matrix4().makeTranslation(0, 0, designOf(design).body.length / 1000),
    )
    .multiply(new Matrix4().makeScale(0.001, 0.001, 0.001))
    .multiply(boltToolMatrix(compactPose(hold[1], spec, design)))
    .multiply(new Matrix4().makeScale(1000, 1000, 1000));
}

// Same robot cycle as R06 (70 s), with the R08 in-hand sequence between lift and transfer.
export const COMPACT_STAGES = [
  {
    start: 0,
    end: 3,
    short: "접근",
    name: "볼트 접근",
    part: "FR3 · 핀셋 날 2개",
    text: "핀셋 끝만 노즈보다 29mm 앞으로 나와 있습니다. 엄지는 뒤로 접혀 핀셋 끝보다 6mm 이상 위에 있습니다.",
  },
  {
    start: 3,
    end: 5,
    short: "파지",
    name: "몸통 파지",
    part: "핀셋 날 2개 · 평평한 끝",
    text: "털 뽑는 핀셋처럼 가늘고 평평한 두 끝이 볼트 사이로 들어가 헤드에서 14mm 떨어진 몸통을 집습니다.",
  },
  {
    start: 5,
    end: 8,
    short: "인출",
    name: "무더기에서 인출",
    part: "FR3",
    text: "파지를 유지한 채 통 밖 여유 공간으로 들어 올립니다.",
  },
  {
    start: 8,
    end: 10,
    short: "받침",
    name: "보조 엄지 접근",
    part: "2관절 엄지 · 롤러",
    text: "뒤로 접혀 있던 엄지가 펴지며 롤러를 볼트 끝부분 아래에 댑니다.",
  },
  {
    start: 10,
    end: 14,
    short: "세움",
    name: "보조 엄지로 세우기",
    part: "2관절 엄지 · 끝 패드",
    text: "엄지가 볼트 끝을 밀어 파지점을 중심으로 90° 세웁니다. 핀셋 끝의 작은 패드는 따라 돕니다.",
  },
  {
    start: 14,
    end: 15.5,
    short: "엄지",
    name: "엄지 접기",
    part: "2관절 엄지",
    text: "세운 볼트는 아래로 매달려 안정합니다. 엄지는 인입 전에 처음 자세로 접힙니다.",
  },
  {
    start: 15.5,
    end: 19,
    short: "인입",
    name: "몸체 안으로 인입",
    part: "인입 요크 · 이송나사",
    text: "요크가 14mm 당겨 헤드를 척 안에 넣습니다. 척은 축방향으로 움직이지 않습니다.",
  },
  {
    start: 19,
    end: 20.5,
    short: "헤드",
    name: "헤드 척 닫기",
    part: "고정 위치 6조 척",
    text: "6개 턱이 반경 방향으로 닫혀 육각 헤드를 잡습니다.",
  },
  {
    start: 20.5,
    end: 22,
    short: "인계",
    name: "몸통 해제",
    part: "핀셋 날 2개",
    text: "헤드가 잡힌 뒤에만 핀셋을 노즈 바깥까지 벌립니다.",
  },
  {
    start: 22,
    end: 25,
    short: "수납",
    name: "몸체 안에 수납",
    part: "인입 요크",
    text: "요크가 32mm 더 물러나 핀셋 끝을 몸체 안으로 넣습니다. 앞에는 가는 노즈와 볼트만 남습니다.",
  },
  {
    start: 25,
    end: 33,
    short: "이동",
    name: "체결 위치 이동",
    part: "FR3",
    text: "작업물 위로 옮겨 구멍 위에서 수직으로 내려갑니다. 지그 없이 접근하고, 가는 노즈만 이웃 볼트 사이로 들어갑니다.",
  },
  {
    start: 33,
    end: 63,
    short: "체결",
    name: "회전하며 체결",
    part: "동축 스핀들 · 척",
    text: "척과 볼트만 회전하고 로봇은 피치만큼 내려갑니다. 반력은 로봇팔이 받습니다. 토크값은 시연 목표이며 측정값이 아닙니다.",
  },
  {
    start: 63,
    end: 65,
    short: "해제",
    name: "헤드 해제",
    part: "6조 척",
    text: "착좌 후 척을 열어 볼트를 작업물에 남깁니다.",
  },
  {
    start: 65,
    end: 70,
    short: "복귀",
    name: "복귀 · 재장전",
    part: "FR3 · 요크",
    text: "물러나면서 캐리지를 다시 내밀고 핀셋을 접근 간격으로 모읍니다.",
  },
];

// c2 merges the in-hand steps into one stroke (14 -> 11 stages); other concepts keep R09's list.
export const CAM_STAGES = [
  ...COMPACT_STAGES.slice(0, 6),
  {
    start: 15.5,
    end: 25,
    short: "한 번에",
    name: "인입 · 고정 · 벌림 · 수납 (한 스트로크)",
    part: "링 너트 요크 · 스프링 척 · 캠",
    text: "요크가 한 번 물러나는 동안 헤드가 척에 들어가고, 원점을 지나는 순간 스프링 척이 닫히며, 캠이 0.6mm 안에 핀셋을 벌리고, 그대로 32mm 수납합니다. 척 폐쇄 구동부가 없습니다.",
  },
  ...COMPACT_STAGES.slice(10, 12),
  {
    start: 63,
    end: 65,
    short: "해제",
    name: "헤드 해제 (요크 초과행정 3mm)",
    part: "요크 · 해제 로드",
    text: "요크가 3mm 더 물러나 해제 로드로 스프링 척을 열고 래치합니다. 볼트는 작업물에 남습니다.",
  },
  COMPACT_STAGES[13],
];
export function stagesFor(id: DesignId = "r09") {
  if (id === "r11")
    return [
      ...COMPACT_STAGES.slice(0, 6),
      {
        start: 15.5,
        end: 25,
        short: "인계·수납",
        name: "인입 · 정지 인계 · 수납",
        part: "요크 · 스프링 척 · 기존 개폐 구동부",
        text: "14mm 인입한 뒤 멈춰 헤드를 고정합니다. 기존 개폐 구동부로 핀셋을 벌린 다음 29mm 수납합니다. 급경사 벌림 캠을 없애고, 헤드 고정 → 핀셋 해제 → 수납 순서를 지킵니다.",
      },
      ...COMPACT_STAGES.slice(10, 12),
      CAM_STAGES[9],
      COMPACT_STAGES[13],
    ];
  if (designOf(id).cam) return CAM_STAGES;
  const d = designOf(id);
  return COMPACT_STAGES.map((st) => ({
    ...st,
    text: st.text.replace("32mm", `${d.stow}mm`),
  }));
}
