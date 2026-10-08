import "./r11-showcase.css";
import * as T from "three";
import { RoomEnvironment } from "three/addons/environments/RoomEnvironment.js";
import { HDRLoader } from "three/addons/loaders/HDRLoader.js";
import { WebGLPathTracer } from "three-gpu-pathtracer";
import { makeCompactGripper } from "./compact-model";
import {
  DESIGNS,
  boltToolMatrix,
  compactBoltWorld,
  compactJoints,
  compactPose,
  minPitch,
  stagesFor,
  tweezerPoints,
} from "./compact-kinematics";
import { finishes, loadWrist, makeRealBolt, realize } from "./r11-real";
import { PRESETS, ramp, type BoltSpec } from "./timeline";
import type { Viewer } from "./viewer";

// R11 showcase: one fixed WebGL stage driven by scroll chapters, an SVG drawing layer
// (dimension lines, item balloons, leaders) projected from the live model, and the
// existing FR3 cell viewer lazily mounted further down. Units: tool mm inside gripper roots.
// The stage is rasterised while anything moves; once it holds still, a path tracer refines it.
document.documentElement.lang = "ko";
const SPEC = PRESETS[1];
const STAGES = stagesFor("r11");
const HERO_T = 12;
const reduced = matchMedia("(prefers-reduced-motion: reduce)").matches;
const clamp01 = (v: number) => Math.min(1, Math.max(0, v));
const ease = (v: number) => {
  const x = clamp01(v);
  return x < 0.5 ? 4 * x * x * x : 1 - (-2 * x + 2) ** 3 / 2;
};
const mix = (a: number, b: number, u: number) => a + (b - a) * u;
const $ = <E extends Element = HTMLElement>(sel: string) =>
  document.querySelector(sel) as E;
const pad = (i: number) => String(i + 1).padStart(2, "0");

// ---------- Panels first: they must exist even when WebGL does not.
const PARTS: [anchor: string, prefix: string, name: string, text: string][] = [
  [
    "slim-nose-tube",
    "slim-nose-tube",
    "노즈 Ø29 × 12",
    "이웃 볼트 머리 사이로 들어가는 유일한 부분입니다.",
  ],
  [
    "head-jaw-1",
    "head-jaw",
    "6조 척",
    "육각 헤드를 반경 방향으로 물고 돌립니다.",
  ],
  [
    "chuck-spring-pack",
    "chuck-spring-pack",
    "척 스프링 팩",
    "척을 늘 닫아 두고, 요크 초과행정 3mm로 엽니다.",
  ],
  [
    "tweezer-blade",
    "tweezer-blade",
    "핀셋 날 2개",
    "끝 1.2 × 0.5mm 판재로 무더기 속 몸통을 집습니다.",
  ],
  [
    "thumb-distal",
    "thumb-",
    "2관절 엄지",
    "24 + 24mm 링크로 볼트를 90° 세웁니다.",
  ],
  [
    "feed-yoke",
    "feed-yoke",
    "요크 3mm",
    "핀셋과 엄지를 싣고 14mm 인입, 29mm 수납합니다.",
  ],
  [
    "feed-ring-motor",
    "feed-ring-motor",
    "이송 링 모터",
    "스핀들을 감싼 나사 슬리브를 돌려 요크를 보냅니다.",
  ],
  [
    "structural-guide-housing",
    "structural-guide-housing",
    "1mm 구조 튜브",
    "가이드 리브 세 줄이 붙은 덮개이자 뼈대입니다.",
  ],
  [
    "spindle-motor-envelope",
    "spindle-motor-envelope",
    "체결 모터 공간",
    "R10과 같은 크기로 남겨 둔 설치 공간입니다. 모터는 미선정입니다.",
  ],
];
const partButtons = PARTS.map(([, , name, text], i) => {
  const li = document.createElement("li");
  const button = document.createElement("button");
  button.type = "button";
  button.innerHTML = `<span class="no">${i + 1}</span><span><b>${name}</b><small>${text}</small></span>`;
  const on = () => setHot(i),
    off = () => setHot(-1);
  button.addEventListener("pointerenter", on);
  button.addEventListener("focus", on);
  button.addEventListener("pointerleave", off);
  button.addEventListener("blur", off);
  li.append(button);
  $("#parts").append(li);
  return button;
});

const rail = $("#rail");
STAGES.forEach((s, i) => {
  const li = document.createElement("li");
  const b = document.createElement("button");
  b.type = "button";
  b.innerHTML = `<span>${pad(i)}</span>${s.short}`;
  b.addEventListener("click", () => {
    const sec = $("#cycle");
    const y =
      sec.offsetTop +
      ((i + 0.5) / STAGES.length) * (sec.offsetHeight - innerHeight);
    scrollTo({ top: y, behavior: reduced ? "auto" : "smooth" });
  });
  li.append(b);
  rail.append(li);
});
const clock = $("#clock");
let stageIndex = -1;
function setStage(i: number, time: number) {
  clock.textContent = `${time.toFixed(1)}초 / 70초`;
  if (i === stageIndex) return;
  stageIndex = i;
  const s = STAGES[i];
  $("#stage-no").textContent = pad(i);
  $("#stage-name").textContent = s.name;
  $("#stage-text").textContent = s.text;
  $("#stage-part").textContent = s.part;
  tag.textContent = s.part;
  rail.querySelectorAll("button").forEach((b, k) => {
    if (k === i) b.setAttribute("aria-current", "step");
    else b.removeAttribute("aria-current");
  });
}
const tags = $("#tags");
const tag = document.createElement("p");
tag.className = "tag";
tags.append(tag);
setStage(0, 0);
const steps = [...document.querySelectorAll<HTMLElement>("#steps li")];
function setSteps(p: number) {
  let on = 0;
  steps.forEach((s, k) => {
    if (Number(s.dataset.at) <= p) on = k;
  });
  steps.forEach((s, k) => s.classList.toggle("on", k === on));
}

// Comparison bars (values from archive/R11/geometry-comparison.json and R11.md).
const METRICS: [string, number, number, string][] = [
  ["외접 원통 체적", 280773.5602, 255853.0729, "mm³"],
  ["지정 구조 재료 체적", 57796.9271, 41794.8551, "mm³"],
  ["알루미늄 환산 질량", 156.0517, 112.8461, "g"],
  ["몸체 길이", 93, 89, "mm"],
  ["수납 행정", 32, 29, "mm"],
];
const num = (v: number) =>
  v.toLocaleString("ko-KR", { maximumFractionDigits: 2 });
const bars = $("#bars");
for (const [name, a, b, unit] of METRICS) {
  const row = document.createElement("div");
  row.className = "row";
  const pct = ((b - a) / a) * 100;
  row.innerHTML = `<p class="name">${name}</p>
    <div class="pair">
      <div class="meter r10" style="--w:1"><i></i><span>${num(a)} ${unit}</span></div>
      <div class="meter r11" style="--w:${(b / a).toFixed(4)}"><i></i><span>${num(b)} ${unit}</span></div>
    </div>
    <p class="delta">${pct.toFixed(2).replace("-", "−")}%</p>`;
  bars.append(row);
}
// Bars rest at full length; they only grow in when they start below the fold.
if (!reduced && bars.getBoundingClientRect().top > innerHeight) {
  bars.classList.add("armed");
  new IntersectionObserver(
    ([e], o) => {
      if (!e.isIntersecting) return;
      bars.classList.remove("armed");
      o.disconnect();
    },
    { threshold: 0.35 },
  ).observe(bars);
}

// ---------- Stage
const canvas = $<HTMLCanvasElement>("#stage");
let renderer: T.WebGLRenderer | null = null;
try {
  renderer = new T.WebGLRenderer({ canvas, antialias: true, alpha: true });
} catch (error) {
  console.error(error);
  document.body.classList.add("no-webgl");
}
let contextLost = false;
canvas.addEventListener("webglcontextlost", (e) => {
  e.preventDefault();
  contextLost = true;
});
canvas.addEventListener("webglcontextrestored", () => (contextLost = false));
const scene = new T.Scene();
if (renderer) {
  renderer.setPixelRatio(Math.min(devicePixelRatio, 2));
  renderer.outputColorSpace = T.SRGBColorSpace;
  renderer.toneMapping = T.NeutralToneMapping;
  renderer.toneMappingExposure = 1;
  renderer.shadowMap.enabled = true;
  renderer.shadowMap.type = T.PCFSoftShadowMap;
  // Neutral studio until the HDRI arrives; the path tracer waits for the real one.
  scene.environment = new T.PMREMGenerator(renderer).fromScene(
    new RoomEnvironment(),
    0.04,
  ).texture;
}
let envReady = false;
new HDRLoader()
  .loadAsync(`${import.meta.env.BASE_URL}hdri/studio_small_09.hdr`)
  .then((hdr) => {
    hdr.mapping = T.EquirectangularReflectionMapping;
    scene.environment = hdr;
    envReady = true;
    sceneChanged = true;
  })
  .catch((error) =>
    console.warn("HDRI unavailable, keeping the room light", error),
  );
scene.environmentIntensity = 0.9;
scene.environmentRotation.y = 2.2;
const key = new T.DirectionalLight("#fff4e4", 1.6);
key.position.set(-0.45, 0.6, 0.5);
key.castShadow = true;
key.shadow.mapSize.set(2048, 2048);
Object.assign(key.shadow.camera, {
  left: -0.25,
  right: 0.25,
  top: 0.25,
  bottom: -0.25,
  near: 0.1,
  far: 2,
});
key.shadow.bias = -0.0002;
key.shadow.normalBias = 0.0004;
const rim = new T.DirectionalLight("#dceaff", 1.1);
rim.position.set(0.6, 0.15, -0.7);
scene.add(key, rim);
const camera = new T.PerspectiveCamera(28, 1, 0.005, 5);

// Tool axis points down: holder maps tool +Z onto world -Y, flange at the origin.
const holder = new T.Group();
holder.rotation.x = Math.PI / 2;
scene.add(holder);
const r11 = makeCompactGripper(SPEC, "r11");
const r10 = makeCompactGripper(SPEC, "c2");
holder.add(r11.root, r10.root);
r11.update({ time: HERO_T }, SPEC);
r10.update({ time: 0 }, SPEC);
const f11 = finishes(),
  f10 = finishes();
const cable = realize(r11.root, f11, {
  ...DESIGNS.r11.body,
  nose: DESIGNS.r11.nose,
})!;
realize(r10.root, f10);
const housing = r11.root.getObjectByName("structural-guide-housing") as T.Mesh;
const housingMat = housing.material as T.Material;

const materialsOf = (root: T.Object3D) => {
  const set = new Set<T.Material>();
  root.traverse((o) => {
    if (o instanceof T.Mesh) set.add(o.material as T.Material);
  });
  return [...set];
};
function fade(m: T.Material, o: number) {
  const see = o < 0.999;
  if (m.transparent !== see) {
    m.transparent = see;
    m.needsUpdate = true;
  }
  m.opacity = o;
  m.depthWrite = o > 0.5;
}

// Exploded-view offsets, computed once per mesh in its parent's frame.
type Piece = { mesh: T.Mesh; base: T.Vector3; off: T.Vector3; rank: number };
function piecesOf(
  root: T.Object3D,
  offset: (c: T.Vector3, name: string) => T.Vector3 | null,
) {
  root.updateMatrixWorld(true);
  const inv = root.matrixWorld.clone().invert();
  const out: Piece[] = [];
  root.traverse((o) => {
    if (!(o instanceof T.Mesh)) return;
    o.geometry.computeBoundingBox();
    const c = o.geometry
      .boundingBox!.getCenter(new T.Vector3())
      .applyMatrix4(o.matrixWorld)
      .applyMatrix4(inv);
    const off = offset(c, o.name);
    if (!off) return;
    const toParent = new T.Matrix3()
      .setFromMatrix4(inv.clone().multiply(o.parent!.matrixWorld))
      .invert();
    out.push({
      mesh: o,
      base: o.position.clone(),
      off: off.applyMatrix3(toParent),
      rank: off.length(),
    });
  });
  const far = Math.max(...out.map((p) => p.rank));
  for (const p of out) p.rank = 1 - p.rank / far; // short trips land first
  return out;
}
const pieces = piecesOf(r11.root, (c, name) => {
  if (/^harness-cable|^cable-tie/.test(name)) return null; // hidden while exploded
  const r = Math.hypot(c.x, c.y);
  const radial =
    r > 7
      ? new T.Vector3(c.x, c.y, 0).multiplyScalar(0.55 + 12 / r)
      : new T.Vector3();
  return radial.setZ((c.z + 42) * 0.75);
});
function explode(u: number) {
  const S = 0.6;
  for (const p of pieces)
    p.mesh.position
      .copy(p.base)
      .addScaledVector(p.off, ease(u * (1 + S) - p.rank * S));
}

// Held bolt, bin pile and workpiece live in the R11 tool frame (mm).
const phys = (color: string, metalness: number, roughness: number) =>
  new T.MeshPhysicalMaterial({ color, metalness, roughness });
const yellowZinc = phys("#cdb060", 1, 0.3),
  zinc = phys("#bcc4c9", 1, 0.32);
const bolt = makeRealBolt(SPEC, yellowZinc, 2);
const boltMount = new T.Group();
boltMount.matrixAutoUpdate = false;
boltMount.add(bolt);
const scaled = (o: T.Object3D) => {
  const g = new T.Group();
  g.scale.setScalar(1000);
  g.add(o);
  return g;
};
const shadowed = <O extends T.Mesh>(o: O) => {
  o.castShadow = o.receiveShadow = true;
  return o;
};
const pile = new T.Group();
{
  const floor = shadowed(
    new T.Mesh(
      new T.CylinderGeometry(82, 82, 3, 96),
      phys("#4f6470", 0.2, 0.55),
    ),
  );
  floor.rotation.x = Math.PI / 2;
  floor.position.z = 37.5;
  pile.add(floor);
  let seed = 11;
  const rand = () => (seed = (seed * 1664525 + 1013904223) >>> 0) / 2 ** 32;
  for (let i = 0; i < 14; i++) {
    const spec = PRESETS[i % 3];
    const x = (rand() < 0.5 ? -1 : 1) * (19 + rand() * 50),
      y = (rand() - 0.5) * 90;
    const b = scaled(makeRealBolt(spec, zinc, 1));
    b.position.set(x, y, 36 - (spec.headWidth * 1000) / Math.sqrt(3));
    b.quaternion
      .setFromAxisAngle(new T.Vector3(0, 0, 1), rand() * Math.PI * 2)
      .multiply(
        new T.Quaternion().setFromAxisAngle(
          new T.Vector3(1, 0, 0),
          Math.PI / 2,
        ),
      );
    pile.add(b);
  }
}
const plate = new T.Group();
{
  // Thick enough to swallow the neighbours' shanks.
  const slab = shadowed(
    new T.Mesh(
      new T.CylinderGeometry(64, 64, 40, 128),
      phys("#b4bdc3", 1, 0.36),
    ),
  );
  slab.rotation.x = Math.PI / 2;
  slab.position.z = 20;
  const hole = new T.Mesh(
    new T.CircleGeometry(SPEC.diameter * 500 + 0.15, 32),
    phys("#1a2026", 0.2, 0.8),
  );
  hole.rotation.x = Math.PI;
  hole.position.z = -0.02;
  plate.add(slab, hole);
  const pitch = minPitch(SPEC) + 0.5;
  for (let i = 0; i < 6; i++) {
    const n = scaled(makeRealBolt(SPEC, zinc, 0));
    n.position.set(
      pitch * Math.cos((i * Math.PI) / 3),
      pitch * Math.sin((i * Math.PI) / 3),
      0,
    );
    plate.add(n);
  }
}
const r11Mats = materialsOf(r11.root);
r11.root.add(boltMount, pile, plate);
const r10Mats = materialsOf(r10.root);

/** Bolt, pile and workpiece for robot-cycle time t, seen from the tool. */
function placeProps(t: number, show: boolean) {
  const L = SPEC.length * 1000;
  const approach = 50 * (1 - ease(ramp(t, 0, 2.6)));
  const plateZ = (u: number) =>
    L * (1 - compactPose(u, SPEC, "r11").inserted) +
    150 * (1 - ease(ramp(u, 25, 33))) +
    150 * ease(ramp(u, 65, 70));
  const held = Math.min(t, 63);
  const m = new T.Matrix4()
    .makeTranslation(
      0,
      0,
      t < 3 ? approach : t > 63 ? plateZ(t) - plateZ(63) : 0,
    )
    .multiply(boltToolMatrix(compactPose(held, SPEC, "r11")))
    .multiply(new T.Matrix4().makeScale(1000, 1000, 1000));
  boltMount.matrix.copy(m);
  boltMount.matrixWorldNeedsUpdate = true;
  boltMount.visible = show;
  pile.visible = show && t < 8.4;
  pile.position.z = approach + 140 * ease(ramp(t, 5, 8));
  plate.visible = show && t > 24 && t < 69.8;
  plate.position.z = plateZ(t);
}

// The tool hangs from the real FR3 wrist (links 6 and 7) whenever it is shown at work.
let wrist: T.Object3D | null = null;
loadWrist(0.55)
  .then((w) => {
    wrist = w;
    holder.add(w);
    sceneChanged = true;
  })
  .catch((error) => console.warn("FR3 wrist unavailable", error));

// R10 parts that R11 no longer has; each leaves in turn in the "R10 대비" chapter.
const CUTS = [
  { name: "cover-screw", at: 0.12, back: 0, out: 26 },
  { name: "cover-sleeve", at: 0.2, back: 115, out: 0 },
  { name: "tie-rod", at: 0.36, back: 0, out: 42 },
  { name: "rear-bulkhead", at: 0.44, back: 70, out: 0 },
  { name: "tweezer-spread-cam", at: 0.56, back: 0, out: 34 },
].map((cut) => {
  const glow = new T.MeshStandardMaterial({
    color: "#4a80be",
    emissive: "#2d5d96",
    emissiveIntensity: 0.9,
    metalness: 0.3,
    roughness: 0.4,
  });
  const parts = piecesOf(r10.root, (c, name) =>
    name === cut.name
      ? new T.Vector3(c.x, c.y, 0).setLength(cut.out).setZ(-cut.back)
      : null,
  ).map((p) => ({ ...p, original: p.mesh.material as T.Material }));
  return { ...cut, glow, parts };
});
function cutAway(p: number, r10Fade: number) {
  for (const cut of CUTS) {
    const q = clamp01((p - cut.at) / 0.16);
    const gone = 1 - clamp01((q - 0.5) / 0.5);
    fade(cut.glow, gone * r10Fade);
    for (const part of cut.parts) {
      part.mesh.material = q > 0 ? cut.glow : part.original;
      part.mesh.visible = gone > 0.01;
      part.mesh.position
        .copy(part.base)
        .addScaledVector(part.off, ease((q - 0.2) / 0.8));
    }
  }
}

// ---------- Drawing layer
const svg = $<SVGSVGElement>("#annot");
const NS = "http://www.w3.org/2000/svg";
function el<K extends keyof SVGElementTagNameMap>(
  tag: K,
  cls: string,
  parent: Element = svg,
) {
  const e = document.createElementNS(NS, tag);
  e.setAttribute("class", cls);
  parent.append(e);
  return e;
}
type P2 = { x: number; y: number };
const W = () => canvas.clientWidth,
  H = () => canvas.clientHeight;
const toScreen = (v: T.Vector3): P2 => {
  const p = v.clone().project(camera);
  return { x: (p.x * 0.5 + 0.5) * W(), y: (-p.y * 0.5 + 0.5) * H() };
};
const f = (n: number) => n.toFixed(1);

/** A dimension: extension lines, a line that grows from its middle, arrowheads, value. */
function makeDim(cls: string, label: string) {
  const g = el("g", `dim ${cls}`);
  const ext = el("path", "ext", g),
    line = el("path", "line", g),
    arrows = el("path", "arrow", g),
    text = el("text", "val", g);
  text.textContent = label;
  return (a: P2, b: P2, centre: P2, gap: number, draw: number) => {
    g.style.opacity = draw > 0 ? "1" : "0";
    if (draw <= 0) return;
    const dx = b.x - a.x,
      dy = b.y - a.y,
      len = Math.hypot(dx, dy) || 1;
    let nx = -dy / len,
      ny = dx / len;
    if (
      ((a.x + b.x) / 2 - centre.x) * nx + ((a.y + b.y) / 2 - centre.y) * ny <
      0
    ) {
      nx = -nx;
      ny = -ny;
    }
    const A = { x: a.x + nx * gap, y: a.y + ny * gap },
      B = { x: b.x + nx * gap, y: b.y + ny * gap };
    const e = ease(draw / 0.35);
    const ext1 = (p: P2, q: P2) =>
      `M${f(p.x + nx * 5)} ${f(p.y + ny * 5)}L${f(mix(p.x + nx * 5, q.x + nx * 7, e))} ${f(mix(p.y + ny * 5, q.y + ny * 7, e))}`;
    ext.setAttribute("d", ext1(a, A) + ext1(b, B));
    const q = ease((draw - 0.25) / 0.5),
      mx = (A.x + B.x) / 2,
      my = (A.y + B.y) / 2;
    const ux = dx / len,
      uy = dy / len;
    const end1 = { x: mix(mx, A.x, q), y: mix(my, A.y, q) },
      end2 = { x: mix(mx, B.x, q), y: mix(my, B.y, q) };
    line.setAttribute(
      "d",
      q > 0 ? `M${f(end1.x)} ${f(end1.y)}L${f(end2.x)} ${f(end2.y)}` : "",
    );
    const head = (p: P2, s: number) =>
      `M${f(p.x)} ${f(p.y)}L${f(p.x + s * ux * 8 + nx * 2.6)} ${f(p.y + s * uy * 8 + ny * 2.6)}L${f(p.x + s * ux * 8 - nx * 2.6)} ${f(p.y + s * uy * 8 - ny * 2.6)}Z`;
    arrows.setAttribute("d", q > 0.97 ? head(A, 1) + head(B, -1) : "");
    let angle = (Math.atan2(dy, dx) * 180) / Math.PI;
    // Aligned dimensioning: values read from the bottom or from the right.
    // Kept in (-120, 60] so near-vertical values never flip while the camera moves.
    if (angle > 60) angle -= 180;
    if (angle <= -120) angle += 180;
    text.setAttribute(
      "transform",
      `translate(${f(mx + nx * 13)} ${f(my + ny * 13)}) rotate(${f(angle)})`,
    );
    text.style.opacity = String(clamp01((draw - 0.7) / 0.3));
  };
}

/** Body diameter and length dimensions for a gripper, drawn on its silhouette. */
function bodyDims(cls: string, body: { width: number; length: number }) {
  const dia = makeDim(cls, `Ø${body.width}`),
    len = makeDim(cls, `${body.length}`);
  return (draw: number, gap: number) => {
    const R = body.width / 2000,
      L = body.length / 1000;
    const axisPoint = (depth: number) => new T.Vector3(0, -depth, 0);
    const side = new T.Vector3()
      .crossVectors(
        new T.Vector3(0, -1, 0),
        camera.position.clone().sub(axisPoint(L / 2)),
      )
      .normalize()
      .multiplyScalar(R);
    const centre = toScreen(axisPoint(L / 2));
    const top = axisPoint(0.006);
    dia(
      toScreen(top.clone().sub(side)),
      toScreen(top.clone().add(side)),
      centre,
      gap,
      draw,
    );
    len(
      toScreen(axisPoint(0).add(side)),
      toScreen(axisPoint(L).add(side)),
      centre,
      gap,
      draw,
    );
  };
}
const heroDims = bodyDims("r11 hero", DESIGNS.r11.body);
const r10Dims = bodyDims("r10", DESIGNS.c2.body);
const r11Dims = bodyDims("r11", DESIGNS.r11.body);

// Item balloons for the exploded view, set in two columns like a drawing's callouts.
const hot = new T.MeshStandardMaterial({
  color: "#c9952e",
  emissive: "#7a5310",
  emissiveIntensity: 0.8,
  metalness: 0.5,
  roughness: 0.35,
});
let hotIndex = -1;
const hotMeshes = PARTS.map(([, prefix]) => {
  const list: { mesh: T.Mesh; original: T.Material }[] = [];
  r11.root.traverse((o) => {
    if (o instanceof T.Mesh && o.name.startsWith(prefix))
      list.push({ mesh: o, original: o.material as T.Material });
  });
  return list;
});
const balloons = PARTS.map(([anchor], i) => {
  const g = el("g", "balloon");
  const leader = el("path", "leader", g),
    dot = el("circle", "dot", g),
    ring = el("circle", "ring", g),
    no = el("text", "no", g);
  dot.setAttribute("r", "2.6");
  ring.setAttribute("r", "13");
  no.textContent = String(i + 1);
  return {
    mesh: r11.root.getObjectByName(anchor) as T.Mesh,
    g,
    leader,
    dot,
    ring,
    no,
  };
});
function setHot(i: number) {
  if (i === hotIndex) return;
  hotIndex = i;
  sceneChanged = true;
  hotMeshes.forEach((list, k) =>
    list.forEach((h) => (h.mesh.material = k === i ? hot : h.original)),
  );
  balloons.forEach((b, k) => b.g.classList.toggle("hot", k === i));
  partButtons.forEach((b, k) => b.classList.toggle("hot", k === i));
}
const meshCentre = (m: T.Object3D) => {
  const mesh = m as T.Mesh;
  if (!mesh.geometry.boundingBox) mesh.geometry.computeBoundingBox();
  return mesh.localToWorld(
    mesh.geometry.boundingBox!.getCenter(new T.Vector3()),
  );
};
function drawBalloons(show: number) {
  svg.classList.toggle("balloons-on", show > 0.01);
  if (show <= 0.01) return;
  const c = toScreen(new T.Vector3(0, -0.045, 0));
  const spots = balloons.map((b, i) => ({
    b,
    i,
    a: toScreen(meshCentre(b.mesh)),
  }));
  const column = Math.min(250, W() * 0.2);
  for (const sideLeft of [true, false]) {
    const list = spots
      .filter((s) => s.a.x < c.x === sideLeft)
      .sort((p, q) => p.a.y - q.a.y);
    // Spread vertically so balloons never overlap, centred on their anchors.
    const ys = list.map((s) => s.a.y);
    for (let k = 1; k < ys.length; k++) ys[k] = Math.max(ys[k], ys[k - 1] + 38);
    const shift = Math.max(0, (ys.at(-1) ?? 0) - (list.at(-1)?.a.y ?? 0)) / 2;
    list.forEach((s, k) => {
      const bx = c.x + (sideLeft ? -column : column),
        by = ys[k] - shift;
      const dx = bx - s.a.x,
        dy = by - s.a.y,
        d = Math.hypot(dx, dy) || 1;
      const ex = bx - (dx / d) * 13,
        ey = by - (dy / d) * 13;
      const grow = ease(show * 1.4 - s.i * 0.05);
      s.b.leader.setAttribute(
        "d",
        `M${f(s.a.x)} ${f(s.a.y)}L${f(mix(s.a.x, ex, grow))} ${f(mix(s.a.y, ey, grow))}`,
      );
      s.b.dot.setAttribute("cx", f(s.a.x));
      s.b.dot.setAttribute("cy", f(s.a.y));
      s.b.ring.setAttribute("cx", f(bx));
      s.b.ring.setAttribute("cy", f(by));
      s.b.no.setAttribute("x", f(bx));
      s.b.no.setAttribute("y", f(by));
      s.b.g.style.opacity = String(clamp01(grow * 1.5 - 0.3));
    });
  }
}

// Cycle chapter: one leader that follows whatever part is working in this stage.
const leader = el("g", "follow");
const leaderLine = el("path", "leader", leader),
  leaderDot = el("circle", "dot", leader);
leaderDot.setAttribute("r", "3.4");
const byName = (n: string) => () => meshCentre(r11.root.getObjectByName(n)!);
const tip = () =>
  r11.root.localToWorld(
    tweezerPoints(compactPose(state.time, SPEC, "r11"), -1, "r11").tip,
  );
// Index = stage; each points at the part its tag names ("FR3" = the robot interface).
const ANCHORS: (() => T.Vector3)[] = [
  tip,
  tip,
  byName("robot-adapter-ring"),
  byName("bolt-roller"),
  byName("bolt-roller"),
  byName("thumb-joint-2"),
  byName("feed-yoke"),
  byName("robot-adapter-ring"),
  byName("head-jaw-1"),
  byName("chuck-release-rod"),
  byName("feed-yoke"),
];
function drawLeader(show: number, stage: number) {
  leader.style.opacity = String(show);
  tag.style.opacity = String(show);
  if (show <= 0.01) return;
  const a = toScreen(ANCHORS[stage]());
  const wide = W() > 900;
  const bx = Math.min(W() - 220, a.x + (wide ? 110 : 60)),
    by = Math.max(90, a.y - (wide ? 90 : 70));
  leaderLine.setAttribute(
    "d",
    `M${f(a.x)} ${f(a.y)}L${f(bx)} ${f(by + 16)}L${f(bx + 18)} ${f(by + 16)}`,
  );
  leaderDot.setAttribute("cx", f(a.x));
  leaderDot.setAttribute("cy", f(a.y));
  tag.style.transform = `translate(${f(bx + 22)}px, ${f(by)}px)`;
}

// ---------- Chapters
type Shot = [az: number, el: number, dist: number, ty: number];
const HERO: Shot = [0.62, 0.12, 0.56, -0.045];
const ANATOMY: Shot = [0.75, 0.22, 0.62, -0.075];
const DIET: Shot = [0.95, 0.18, 0.5, -0.058];
const CYCLE: Shot[] = [
  [2.75, 0.16, 0.36, -0.1],
  [2.85, 0.1, 0.31, -0.104],
  [2.55, 0.22, 0.46, -0.07],
  [4.55, 0.1, 0.36, -0.1],
  [4.65, 0.05, 0.34, -0.1],
  [5.0, 0.18, 0.4, -0.09],
  [5.6, 0.26, 0.42, -0.072],
  [6.75, 0.3, 0.6, -0.08],
  [7.05, 0.46, 0.42, -0.11],
  [7.3, 0.4, 0.44, -0.105],
  [7.85, 0.28, 0.56, -0.07],
];
const chapters = [...document.querySelectorAll<HTMLElement>("[data-chapter]")];
function chapterNow() {
  const h = innerHeight;
  let active = chapters[0];
  for (const c of chapters)
    if (c.getBoundingClientRect().top <= h * 0.5) active = c;
  const r = active.getBoundingClientRect();
  const span = r.height - h > 1 ? r.height - h : r.height;
  return { name: active.dataset.chapter!, p: clamp01(-r.top / span) };
}
const cycleAt = (p: number) => {
  const x = p * STAGES.length,
    i = Math.min(STAGES.length - 1, Math.floor(x));
  return {
    i,
    u: x - i,
    time: mix(STAGES[i].start, STAGES[i].end, Math.min(1, x - i)),
  };
};

const state = {
  az: HERO[0],
  el: HERO[1],
  dist: HERO[2],
  ty: HERO[3],
  time: HERO_T,
  explode: reduced ? 0 : 1,
  xray: 1,
  r11: 1,
  r10: 0,
  hero: 0,
  balloons: 0,
  leader: 0,
  dim10: 0,
  dim11: 0,
  props: 1,
  wrist: 1,
  lift: 0,
  show: 1,
};
type State = typeof state;
// Keys whose change alters the rendered 3D image (the rest only drive the SVG layer).
const SCENE_KEYS: (keyof State)[] = [
  "az",
  "el",
  "dist",
  "ty",
  "time",
  "explode",
  "xray",
  "r11",
  "r10",
  "props",
  "wrist",
  "lift",
  "show",
];
const t0 = performance.now();
let diet = 0;
let sceneChanged = false;
const heroCopy = $(".hero-copy");

/** Phone hero: centre the model in the space left under the headline and buttons. */
function phoneHero(goal: State) {
  const h = H(),
    free = h - heroCopy.getBoundingClientRect().bottom - 16;
  const centre = h - free / 2;
  goal.lift = -(centre - h / 2) / h;
  // 0.17 m of tool, wrist and dimension marks must fit in the free height.
  goal.dist = Math.max(
    HERO[2],
    (0.17 * h) / (Math.max(160, free) * 0.4986 * 1.35),
  );
}

function target(now: number): State {
  const { name, p } = chapterNow();
  const goal: State = {
    ...state,
    explode: 0,
    xray: 1,
    r11: 1,
    r10: 0,
    hero: 0,
    balloons: 0,
    leader: 0,
    dim10: 0,
    dim11: 0,
    props: 1,
    wrist: 1,
    lift: 0.15,
    show: 1,
  };
  const shot = (s: Shot) => ([goal.az, goal.el, goal.dist, goal.ty] = s);
  const since = (now - t0) / 1000;
  if (name === "hero") {
    shot(HERO);
    goal.time = HERO_T;
    goal.explode = reduced ? 0 : 1 - clamp01((since - 0.25) / 1.9);
    goal.hero = reduced ? 1 : clamp01((since - 2) / 1.1);
    if (W() < 900) phoneHero(goal);
  } else if (name === "anatomy") {
    shot(ANATOMY);
    goal.time = HERO_T;
    goal.explode = ease(p / 0.3) * (1 - ease((p - 0.86) / 0.14));
    goal.xray = 1 - 0.8 * goal.explode;
    goal.balloons = clamp01((goal.explode - 0.75) / 0.25);
    goal.wrist = 0;
  } else if (name === "cycle") {
    const { i, u, time } = cycleAt(p);
    const a = CYCLE[i],
      b = CYCLE[Math.min(CYCLE.length - 1, i + 1)],
      w = ease((u - 0.55) / 0.45);
    shot(a.map((v, k) => mix(v, b[k], w)) as Shot);
    goal.time = time;
    goal.xray = time > 15.2 && time < 68.8 ? 0.18 : 1;
    goal.leader = 1;
    rail.style.setProperty("--p", p.toFixed(4));
    setStage(i, time);
  } else if (name === "diet") {
    shot(DIET);
    diet = p;
    goal.time = 0;
    goal.r10 = 1 - clamp01((p - 0.74) / 0.12);
    goal.r11 = clamp01((p - 0.7) / 0.14);
    goal.dim10 = clamp01(p / 0.08);
    goal.dim11 = clamp01((p - 0.76) / 0.16);
    goal.props = 0;
    goal.wrist = 0;
    setSteps(p);
  } else goal.show = 0;
  return goal;
}

// ---------- Path tracing while the stage holds still (desktop pointers; phones keep raster).
let tracer: WebGLPathTracer | null = null;
const traceStatus = $("#trace-status");
let tracing = false,
  still = 0;
// Automated browsers (software GL) would stall on the tracer's shader; #trace forces it on.
const canTrace =
  !!renderer &&
  matchMedia("(pointer: fine)").matches &&
  (!navigator.webdriver || location.hash === "#trace");
function startTracing() {
  if (!renderer) return;
  if (!tracer) {
    tracer = new WebGLPathTracer(renderer);
    tracer.tiles.set(3, 3);
    tracer.minSamples = 3;
    tracer.fadeDuration = 900;
    tracer.renderDelay = 0;
    tracer.bounces = 6;
    tracer.filterGlossyFactor = 0.6;
  }
  tracer.renderScale = Math.min(1, 1.25 / renderer.getPixelRatio());
  renderer.shadowMap.needsUpdate = true;
  tracer.setScene(scene, camera);
  tracing = true;
  document.body.classList.add("tracing");
}
function stopTracing() {
  tracing = false;
  traceStatus.textContent = "";
  document.body.classList.remove("tracing");
}

// ---------- Cell: the existing FR3 viewer, mounted when the section comes near.
const cellHost = $("#cell-view");
const cellLoading = $("#cell-loading");
const cellPlay = $<HTMLButtonElement>("#cell-play");
const cellTime = $<HTMLInputElement>("#cell-time");
const cellSpeed = $<HTMLSelectElement>("#cell-speed");
const cellClock = $("#cell-clock");
const cellStage = $("#cell-stage");
const cell = {
  viewer: null as Viewer | null,
  time: 0,
  playing: false,
  userPaused: false,
  visible: false,
  started: false,
};
function setCellPlaying(on: boolean) {
  cell.playing = on;
  cellPlay.textContent = on ? "일시정지" : "재생";
}
function seekCell(t: number) {
  cell.time = Math.max(0, Math.min(70, t));
  cellTime.value = cell.time.toFixed(1);
  cellClock.textContent = `${cell.time.toFixed(1)}초`;
  const found = STAGES.findIndex((s) => cell.time < s.end);
  const i = found < 0 ? STAGES.length - 1 : found;
  const text = `${pad(i)} ${STAGES[i].name}`;
  if (cellStage.textContent !== text) cellStage.textContent = text;
  cell.viewer?.update(cell.time);
}
async function startCell() {
  cell.started = true;
  try {
    const { Viewer } = await import("./viewer");
    const viewer = new Viewer(cellHost, $("#inset-label"), {
      makeGripper: () => {
        const g = makeCompactGripper(undefined, "r11");
        realize(g.root, finishes(), {
          ...DESIGNS.r11.body,
          nose: DESIGNS.r11.nose,
        });
        return g;
      },
      joints: (t, id) => compactJoints(t, id, "r11"),
      boltWorld: (t, spec) => compactBoltWorld(t, spec, "r11"),
      focusZ: DESIGNS.r11.body.length / 2000,
      keyways: false,
      neighbourPitch: (spec) => (minPitch(spec) + 0.5) / 1000,
      detailLift: 0.16,
    });
    // The page scrolls: never let the wheel or a touch drag get trapped by the 3D view.
    viewer.controls.enableZoom = false;
    viewer.renderer.domElement.style.touchAction = "pan-y";
    if (matchMedia("(pointer: coarse)").matches)
      viewer.controls.enabled = false;
    viewer.renderer.toneMapping = T.NeutralToneMapping;
    if (envReady) viewer.scene.environment = scene.environment;
    viewer.setOptions({ labels: false });
    await viewer.load(
      (n) =>
        (cellLoading.textContent = `FR3 모델을 불러오는 중입니다. 링크 ${n} / 8`),
    );
    cell.viewer = viewer;
    cellLoading.hidden = true;
    document
      .querySelectorAll<HTMLButtonElement>(
        "#cell button, #cell input, #cell select",
      )
      .forEach((b) => (b.disabled = false));
    seekCell(0);
    if (!reduced && cell.visible) setCellPlaying(true);
  } catch (error) {
    console.error(error);
    cellLoading.textContent =
      "3D 화면을 띄우지 못했습니다. WebGL을 켠 브라우저에서 페이지를 다시 불러오세요.";
  }
}
cellHost.addEventListener("viewer-error", (e) => {
  cellLoading.hidden = false;
  cellLoading.textContent = (e as CustomEvent<string>).detail;
});
cellPlay.addEventListener("click", () => {
  if (!cell.playing && cell.time >= 70) seekCell(0);
  cell.userPaused = cell.playing;
  setCellPlaying(!cell.playing);
});
cellTime.addEventListener("input", () => {
  seekCell(Number(cellTime.value));
  if (cell.playing) {
    cell.userPaused = true;
    setCellPlaying(false);
  }
});
const specBox = $("#cell-spec");
for (const spec of PRESETS) {
  const b = document.createElement("button");
  b.type = "button";
  b.textContent = spec.label;
  b.disabled = true;
  b.setAttribute("aria-pressed", String(spec.id === SPEC.id));
  b.addEventListener("click", () => {
    cell.viewer?.setSpec(spec as BoltSpec);
    specBox
      .querySelectorAll("button")
      .forEach((x) => x.setAttribute("aria-pressed", String(x === b)));
    seekCell(cell.time);
  });
  specBox.append(b);
}
document
  .querySelectorAll<HTMLButtonElement>("#cell-views button")
  .forEach((b) =>
    b.addEventListener("click", () => {
      cell.viewer?.setView(b.dataset.view as "whole" | "detail" | "side");
      document
        .querySelectorAll("#cell-views button")
        .forEach((x) => x.setAttribute("aria-pressed", String(x === b)));
    }),
  );
new IntersectionObserver(
  ([e]) => {
    if (e.isIntersecting && !cell.started && renderer) void startCell();
  },
  { rootMargin: "600px 0px" },
).observe(cellHost);
new IntersectionObserver(
  ([e]) => {
    cell.visible = e.isIntersecting;
    if (
      cell.visible &&
      cell.viewer &&
      !cell.playing &&
      !cell.userPaused &&
      !reduced
    )
      setCellPlaying(true);
  },
  { threshold: 0.4 },
).observe(cellHost);
if (!renderer)
  cellLoading.textContent =
    "이 브라우저에서는 3D를 표시할 수 없습니다. WebGL을 켠 브라우저에서 열어 주세요.";

// ---------- Frame loop
let last = performance.now();
let lastSize = "";
function frame(now: number) {
  const dt = Math.min(0.1, (now - last) / 1000);
  last = now;
  const goal = target(now);
  const k = reduced ? 1 : 1 - Math.exp(-dt * 5);
  const kt = reduced ? 1 : 1 - Math.exp(-dt * 7);
  // Shortest way round, so leaving the cycle does not unwind the camera.
  goal.az =
    state.az +
    Math.atan2(Math.sin(goal.az - state.az), Math.cos(goal.az - state.az));
  for (const key of Object.keys(state) as (keyof State)[]) {
    if (key === "time") continue;
    const step =
      (goal[key] - state[key]) *
      (key === "explode" && goal.explode > state.explode ? kt : k);
    // Settle exactly, so the still-frame test below can fire.
    state[key] =
      Math.abs(goal[key] - state[key]) < 2e-5 ? goal[key] : state[key] + step;
  }
  // The cycle returns to its start pose at 70 s, so long jumps snap instead of rewinding.
  const dtime = goal.time - state.time;
  state.time =
    Math.abs(dtime) > 20 || Math.abs(dtime) < 1e-3
      ? goal.time
      : state.time + dtime * kt;
  const moving =
    sceneChanged ||
    SCENE_KEYS.some(
      (key) =>
        Math.abs(goal[key] - state[key]) > 1e-4 ||
        (key === "time" && dtime !== 0),
    );
  sceneChanged = false;
  canvas.style.opacity = String(state.show);
  svg.style.opacity = String(state.show);
  tags.style.opacity = String(state.show);
  if (renderer && !contextLost && state.show > 0.01 && !document.hidden)
    renderStage(dt, moving);
  if (cell.viewer && cell.visible) {
    if (cell.playing) {
      const next = cell.time + dt * Number(cellSpeed.value);
      seekCell(next >= 70 ? 0 : next);
    }
    cell.viewer.render();
  }
  requestAnimationFrame(frame);
}

function renderStage(dt: number, moving: boolean) {
  const r = renderer!;
  const w = W(),
    h = H();
  const size = `${w}x${h}x${r.getPixelRatio()}`;
  if (size !== lastSize) {
    lastSize = size;
    r.setSize(w, h, false);
    svg.setAttribute("viewBox", `0 0 ${w} ${h}`);
    moving = true;
  }
  const narrow = w < 900;
  camera.aspect = w / h;
  const dist = state.dist * (w / h < 1 ? 1.35 : 1);
  camera.position.set(
    Math.sin(state.az) * Math.cos(state.el) * dist,
    state.ty + Math.sin(state.el) * dist,
    Math.cos(state.az) * Math.cos(state.el) * dist,
  );
  camera.lookAt(0, state.ty, 0);
  // Desktop: model sits right of the text column. Phone: above or below the copy.
  camera.setViewOffset(
    w,
    h,
    narrow ? 0 : -0.17 * w,
    narrow ? state.lift * h : 0,
    w,
    h,
  );
  camera.updateProjectionMatrix();

  r11.update({ time: state.time }, SPEC);
  explode(state.explode);
  placeProps(state.time, state.props > 0.5);
  const attached = state.wrist > 0.5;
  if (wrist) wrist.visible = attached;
  cable.visible = attached;
  r11.root.visible = state.r11 > 0.01;
  r10.root.visible = state.r10 > 0.01;
  for (const m of r11Mats)
    fade(m, state.r11 * (m === housingMat ? state.xray : 1));
  for (const m of r10Mats) fade(m, state.r10);
  if (state.r10 > 0.01) cutAway(diet, state.r10);

  if (moving) {
    still = 0;
    if (tracing) stopTracing();
  } else still += dt;
  if (!tracing && canTrace && envReady && still > 0.45 && state.show > 0.99)
    startTracing();
  if (tracing) {
    tracer!.renderSample();
    traceStatus.textContent = `광선 추적 렌더 ${Math.floor(tracer!.samples)} 샘플`;
  } else r.render(scene, camera);

  heroDims(state.hero * state.show, 30);
  r10Dims(state.dim10, 28);
  r11Dims(state.dim11, 58);
  drawBalloons(narrow ? 0 : state.balloons);
  drawLeader(state.leader > 0.02 ? state.leader : 0, Math.max(0, stageIndex));
}

requestAnimationFrame(frame);
