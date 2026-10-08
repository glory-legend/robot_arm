import "./engineering.css";
import "./integrated.css";
import * as T from "three";
import { OrbitControls } from "three/addons/controls/OrbitControls.js";
import { GLTFExporter } from "three/addons/exporters/GLTFExporter.js";
import { makeIntegratedAssembly, INTEGRATED_BOM } from "./integrated-model";
import { integratedPose } from "./integrated-kinematics";
import { PRESETS, type BoltSpec } from "./timeline";

const app = document.querySelector<HTMLDivElement>("#app")!;
app.innerHTML = `<header class="top"><div class="identity">볼트 그리퍼 <small>INTEGRATED TOOL / R08</small></div><span class="review-tag">배치 검토 · 제작 미승인</span></header>
<main class="layout"><section class="drawing" aria-label="일체형 그리퍼 모델"><div class="heading"><p class="eyebrow">ONE BODY / PICK · ALIGN · FASTEN</p><h1>하나의 몸체, 안에서 이어지는 동작</h1><p>중앙 회전 척 · 양옆 집게 수납 · 후면 보조 엄지</p></div><div class="canvas" id="canvas"><div class="view-tools"><button data-view="whole" aria-pressed="true">전체 형태</button><button data-view="detail" aria-pressed="false">손끝 확대</button><button data-view="side" aria-pressed="false">측면</button><button data-view="front" aria-pressed="false">정면</button></div><span class="guide">드래그 회전 · 스크롤 확대</span></div><div class="transport"><div class="transport-row"><button class="primary" id="play">▶ 동작 보기</button><button id="reset">처음으로</button><output id="progress">0 / 100</output></div><label for="motion" class="sr-only">통합 동작 진행률</label><input id="motion" type="range" min="0" max="100" step="0.1" value="0"><div class="steps">${[
  [8, "파지"],
  [25, "세우기"],
  [45, "인입"],
  [60, "헤드 고정"],
  [77, "접기"],
  [90, "수납"],
  [97, "체결 회전"],
]
  .map(
    ([t, n]) => `<button data-step="${t}" aria-pressed="false">${n}</button>`,
  )
  .join("")}</div></div></section>
<aside class="sidebar" aria-label="통합 구조와 동작"><section class="side-section"><h2>R08 · 공통 몸체 통합형</h2><p class="desc">파지부와 체결부를 하나의 프레임에 지지합니다. 얇은 손끝으로 집고, 내부 척으로 넘긴 뒤 몸체 안에 수납합니다.</p><div class="integration-map"><span>중앙<em>체결 구동부 · 회전 척</em></span><span>양옆<em>주집게 · 수납 가이드</em></span><span>후면<em>정렬 엄지 · 인입 구동</em></span></div></section>
<section class="side-section"><h2>현재 동작</h2><h3 class="phase-title" id="phase-title"></h3><p class="desc" id="phase-description"></p><div class="part-note" id="constraint"></div></section>
<section class="side-section"><h2>내부 살펴보기</h2><label class="toggle">외장 투명하게<input id="transparent" type="checkbox"></label><label class="toggle">외장 벗기기<input id="explode" type="checkbox"></label><label class="toggle">부품 이름표<input id="labels" type="checkbox"></label><p class="footnote">외장을 벗겨도 부품은 실제 배치 위치를 유지합니다.</p></section>
<section class="side-section"><h2>검토 조건</h2><label class="sr-only" for="bolt">볼트 규격</label><select class="field" id="bolt">${PRESETS.map((s) => `<option value="${s.id}" ${s.id === "m8" ? "selected" : ""}>${s.label} · 육각 헤드</option>`).join("")}</select><table class="data-table"><tbody><tr><td>몸체 외형 · mm</td><td>152 × 144 × 250</td></tr><tr><td>척 축방향 이동</td><td>0 mm</td></tr><tr><td>인입 / 추가 수납</td><td>50 / 70 mm</td></tr><tr><td>집게 접힘</td><td>90°</td></tr><tr><td>제어 기능 · 도구만</td><td>7축</td></tr><tr><td>토크 · 질량</td><td>미확정</td></tr></tbody></table></section>
<section class="side-section"><h2>검토 상태</h2><div class="status-note">치수는 내부 공간 검토값입니다. 모터·감속기 선정, 척 잠금, 공차·강도·전체 충돌 검증이 남아 있습니다.</div><p class="footnote">로봇의 빈 인출과 나사 삽입은 생략한 도구 동작 모델입니다. 체결 회전은 구동 경로를 설명합니다.</p></section>
<section><div class="downloads"><button id="export-model">조립 GLB 저장</button><button id="export-bom">부품 검토표 CSV</button></div><p id="export-status" class="footnote" role="status"></p><div class="doc-links"><a href="./integrated-review.md" target="_blank" rel="noopener">R08 설계 기록 ↗</a><a href="./engineering.html" target="_blank" rel="noopener">이전 R07 · A/B 비교 ↗</a><a href="https://app.notion.com/p/3ebbf0105ac981379e65c20e9e332bcb" target="_blank" rel="noopener">Notion · 버전별 기록 ↗</a></div></section></aside></main>`;
const $ = <E extends HTMLElement = HTMLElement>(id: string) =>
  document.getElementById(id) as E;
const params = new URLSearchParams(location.search);
let spec: BoltSpec = PRESETS[1],
  t = Math.max(0, Math.min(100, Number(params.get("progress") ?? "0") || 0)),
  playing = false;
const container = $("canvas"),
  scene = new T.Scene();
scene.background = new T.Color("#e3e9e6");
const camera = new T.OrthographicCamera(-300, 300, 300, -300, 0.1, 4000);
camera.up.set(0, 0, 1);
let renderer: T.WebGLRenderer,
  controls: OrbitControls,
  assembly: ReturnType<typeof makeIntegratedAssembly>;
const stage = new T.Group();
stage.rotation.x = Math.PI;
scene.add(stage);
const labels: HTMLDivElement[] = [];
let currentView = "whole";
function setView(view: string) {
  currentView = view;
  const target =
    view === "whole" ? new T.Vector3(0, 0, 100) : new T.Vector3(0, 0, -2);
  const offsets: Record<string, T.Vector3> = {
    whole: new T.Vector3(-420, -550, 160),
    detail: new T.Vector3(-400, -500, -65),
    side: new T.Vector3(-700, 0, 0),
    front: new T.Vector3(0, -700, 30),
  };
  camera.position.copy(target).add(offsets[view] ?? offsets.detail);
  controls.target.copy(target);
  camera.zoom = view === "whole" ? 1.1 : 1.65;
  camera.updateProjectionMatrix();
  controls.update();
  document
    .querySelectorAll<HTMLElement>("[data-view]")
    .forEach((b) =>
      b.setAttribute("aria-pressed", String(b.dataset.view === view)),
    );
}
function updateUI() {
  const s = integratedPose(t);
  const phases =
    t < 16
      ? [
          "얇은 손끝으로 몸통 파지",
          "집게와 보조 엄지가 몸체 끝에서 나옵니다. 빈에서 들어 올린 뒤 정렬하는 구간을 보여줍니다.",
        ]
      : t < 36
        ? [
            "몸체 앞에서 볼트 세우기",
            "접촉 패드는 자세를 따라 회전하고, 후면의 2관절 엄지가 볼트 끝부분을 눌러 세웁니다.",
          ]
        : t < 54
          ? [
              "고정 척으로 50 mm 인입",
              "공통 캐리지가 몸체 안으로 들어갑니다. 볼트 헤드를 중앙 척에 넣는 동안 몸통 파지를 유지합니다.",
            ]
          : t < 69
            ? [
                "헤드 고정 · 엄지 접기",
                "6개 턱이 헤드를 잡은 뒤 보조 엄지를 접습니다. 실물에는 착좌와 잠금 확인이 필요합니다.",
              ]
            : t < 83
              ? [
                  "주집게 열기 · 90° 접기",
                  "몸통 파지를 푼 뒤 두 손가락을 바깥쪽으로 접어 중앙 척을 비웁니다. 이 동안 캐리지는 멈춰 있습니다.",
                ]
              : t < 94
                ? [
                    "양옆 공간에 수납",
                    "접힌 손가락과 보조 엄지를 70 mm 당겨 공통 몸체 안에 수납합니다.",
                  ]
                : [
                    "몸체 안에서 체결 회전",
                    "외장은 고정되고 내부 척과 볼트만 회전합니다. 집게는 작업면에서 빠져 있습니다.",
                  ];
  $("phase-title").textContent = phases[0];
  $("phase-description").textContent = phases[1];
  $("constraint").textContent =
    s.clamp === 1
      ? "헤드 고정 → 집게 접힘 → 수납 → 내부 회전"
      : "몸통 파지 유지 · 척 위치 고정";
  $("progress").textContent = `${t.toFixed(1)} / 100`;
  $<HTMLInputElement>("motion").value = String(t);
  $("play").textContent = playing ? "Ⅱ 일시정지" : "▶ 동작 보기";
  const start =
    t < 16
      ? 8
      : t < 36
        ? 25
        : t < 54
          ? 45
          : t < 69
            ? 60
            : t < 83
              ? 77
              : t < 94
                ? 90
                : 97;
  document
    .querySelectorAll<HTMLElement>("[data-step]")
    .forEach((b) =>
      b.setAttribute(
        "aria-pressed",
        Number(b.dataset.step) === start ? "true" : "false",
      ),
    );
}
function update() {
  assembly?.update(
    t,
    $<HTMLInputElement>("transparent").checked,
    $<HTMLInputElement>("explode").checked,
  );
  updateUI();
}
function rebuild() {
  if (assembly) {
    stage.remove(assembly.root);
    const gs = new Set<T.BufferGeometry>(),
      ms = new Set<T.Material>();
    assembly.root.traverse((o) => {
      if (o instanceof T.Mesh || o instanceof T.Line) {
        gs.add(o.geometry);
        for (const m of Array.isArray(o.material) ? o.material : [o.material])
          ms.add(m);
      }
    });
    gs.forEach((g) => g.dispose());
    ms.forEach((m) => m.dispose());
  }
  labels.forEach((l) => l.remove());
  labels.length = 0;
  assembly = makeIntegratedAssembly(spec);
  stage.add(assembly.root);
  for (const l of assembly.labels) {
    const el = document.createElement("div");
    el.className = "label";
    el.textContent = l.name;
    container.append(el);
    labels.push(el);
  }
  update();
}
function save(data: Blob, name: string) {
  const u = URL.createObjectURL(data);
  const a = document.createElement("a");
  a.href = u;
  a.download = name;
  a.click();
  setTimeout(() => URL.revokeObjectURL(u), 1000);
}
try {
  renderer = new T.WebGLRenderer({
    antialias: true,
    preserveDrawingBuffer: true,
  });
  renderer.setPixelRatio(Math.min(devicePixelRatio, 2));
  renderer.outputColorSpace = T.SRGBColorSpace;
  renderer.shadowMap.enabled = true;
  renderer.shadowMap.type = T.PCFSoftShadowMap;
  renderer.domElement.setAttribute("aria-label", "R08 일체형 그리퍼 3D 화면");
  container.prepend(renderer.domElement);
  controls = new OrbitControls(camera, renderer.domElement);
  controls.enableDamping = true;
  controls.minZoom = 0.35;
  controls.maxZoom = 4;
  scene.add(new T.HemisphereLight(0xffffff, 0x7f9890, 2.5));
  const light = new T.DirectionalLight(0xffffff, 3);
  light.position.set(-250, -300, 700);
  scene.add(light);
  const fill = new T.DirectionalLight(0xcce3ed, 1.5);
  fill.position.set(350, 150, 200);
  scene.add(fill);
  const grid = new T.GridHelper(700, 35, 0x9ab7ad, 0xc9d5cf);
  grid.rotation.x = Math.PI / 2;
  grid.position.set(0, 0, -108);
  scene.add(grid);
  const resize = () => {
    const w = container.clientWidth,
      h = container.clientHeight;
    renderer.setSize(w, h);
    const half = 250;
    camera.left = (-half * w) / h;
    camera.right = (half * w) / h;
    camera.top = half;
    camera.bottom = -half;
    camera.updateProjectionMatrix();
  };
  new ResizeObserver(resize).observe(container);
  resize();
  rebuild();
  setView(params.get("view") === "detail" ? "detail" : "whole");
  let last = performance.now();
  function frame(now: number) {
    const dt = Math.min(0.1, (now - last) / 1000);
    last = now;
    if (playing) {
      t = Math.min(100, t + dt * 6);
      if (t >= 100) playing = false;
      update();
    }
    controls.update();
    stage.updateMatrixWorld(true);
    const s = integratedPose(t);
    for (let i = 0; i < labels.length; i++) {
      const l = assembly.labels[i];
      let p = l.point.clone();
      p.applyMatrix4(stage.matrixWorld).project(camera);
      const el = labels[i];
      el.hidden =
        !$<HTMLInputElement>("labels").checked ||
        Math.abs(p.x) > 1 ||
        Math.abs(p.y) > 1 ||
        p.z > 1 ||
        $<HTMLInputElement>("explode").checked;
      el.style.transform = `translate(${((p.x + 1) / 2) * container.clientWidth + 10}px,${((1 - p.y) / 2) * container.clientHeight + (i % 2) * 12}px)`;
    }
    renderer.render(scene, camera);
    requestAnimationFrame(frame);
  }
  requestAnimationFrame(frame);
  $("play").onclick = () => {
    playing = !playing;
    if (playing) {
      if (t >= 100) t = 0;
    }
    update();
  };
  $("reset").onclick = () => {
    playing = false;
    t = 0;
    update();
  };
  $("motion").oninput = () => {
    playing = false;
    t = Number($<HTMLInputElement>("motion").value);
    update();
  };
  $("bolt").onchange = () => {
    spec = PRESETS.find((s) => s.id === $<HTMLSelectElement>("bolt").value)!;
    playing = false;
    rebuild();
  };
  for (const id of ["transparent", "labels", "explode"])
    $(id).onchange = () => {
      if (id === "explode") playing = false;
      update();
    };
  document.querySelectorAll<HTMLButtonElement>("[data-step]").forEach(
    (b) =>
      (b.onclick = () => {
        playing = false;
        t = Number(b.dataset.step);
        update();
      }),
  );
  document
    .querySelectorAll<HTMLButtonElement>("[data-view]")
    .forEach((b) => (b.onclick = () => setView(b.dataset.view!)));
  document.addEventListener("visibilitychange", () => {
    if (document.hidden) {
      playing = false;
      updateUI();
    }
  });
  $("export-model").onclick = async () => {
    const b = $<HTMLButtonElement>("export-model");
    b.disabled = true;
    playing = false;
    updateUI();
    try {
      const exported = new T.Group();
      exported.name = "R08-REVIEW-METRES";
      exported.userData = {
        status: "assembly review, not manufacturing release",
        units: "metres",
        version: "R08",
        progress: t,
      };
      const copy = assembly.root.clone(true);
      copy.scale.setScalar(0.001);
      exported.add(copy);
      const result = await new GLTFExporter().parseAsync(exported, {
        binary: true,
        onlyVisible: true,
      });
      save(
        new Blob([result as ArrayBuffer], { type: "model/gltf-binary" }),
        `R08-${spec.id}-integrated-review.glb`,
      );
      $("export-status").textContent =
        "현재 조립 배치를 저장했습니다. 가공용 CAD 도면은 아닙니다.";
    } catch {
      $("export-status").textContent =
        "모델 저장에 실패했습니다. 다시 시도해 주세요.";
    } finally {
      b.disabled = false;
    }
  };
  $("export-bom").onclick = () => {
    const rows = [
      ["번호", "부품군", "수량", "배치 치수 mm", "선정 상태"],
      ...INTEGRATED_BOM,
    ];
    const csv =
      "\uFEFF" +
      rows
        .map((r) => r.map((v) => '"' + v.replaceAll('"', '""') + '"').join(","))
        .join("\r\n");
    save(
      new Blob([csv], { type: "text/csv;charset=utf-8" }),
      "R08-component-review.csv",
    );
  };
  renderer.domElement.addEventListener("webglcontextlost", (e) => {
    e.preventDefault();
    playing = false;
    $("export-status").textContent =
      "3D 연결이 중단되었습니다. 페이지를 새로고침해 주세요.";
  });
} catch (error) {
  console.error(error);
  const el = document.createElement("div");
  el.className = "error";
  el.setAttribute("role", "alert");
  el.textContent =
    "3D 화면을 열 수 없습니다. WebGL 지원을 확인하고 새로고침해 주세요.";
  container.append(el);
  document
    .querySelectorAll<HTMLButtonElement | HTMLInputElement | HTMLSelectElement>(
      "button,input,select",
    )
    .forEach((b) => (b.disabled = true));
}
