import "./engineering.css";
import * as T from "three";
import { OrbitControls } from "three/addons/controls/OrbitControls.js";
import { GLTFExporter } from "three/addons/exporters/GLTFExporter.js";
import { makeEngineeringAssembly, ASSEMBLY_BOM } from "./engineering-model";
import { DESIGN, assemblyPose, gripTransform } from "./engineering-kinematics";
import { PRESETS, type BoltSpec } from "./timeline";
import type { Variant } from "./variants";

const app = document.querySelector<HTMLDivElement>("#app")!;
app.innerHTML = `<header class="top"><div class="identity">볼트 그리퍼 <small>MECHANICAL ASSEMBLY / R07</small></div><span class="review-tag">조립 검토 · 제작 미승인</span></header>
<main class="layout"><section class="drawing" aria-label="그리퍼 조립 모델"><div class="heading"><p class="eyebrow">BIN PICKING / INTERNAL FASTENING</p><h1 id="drawing-title">A · 기능을 분리한 구조</h1><p>실제 축을 중심으로 움직이는 조립 배치 · 단위 mm</p></div><div class="canvas" id="canvas"><div class="view-tools"><button data-view="detail" aria-pressed="true">기구 확대</button><button data-view="whole" aria-pressed="false">전체 길이</button><button data-view="side" aria-pressed="false">측면</button><button data-view="front" aria-pressed="false">정면</button></div><span class="guide">DRAG TO ORBIT · SCROLL TO ZOOM</span></div><div class="transport"><div class="transport-row"><button class="primary" id="play">▶ 동작 보기</button><button id="reset">처음으로</button><output id="progress">0 / 100</output></div><label for="motion" class="sr-only">조립 동작 진행률</label><input id="motion" type="range" min="0" max="100" step="0.1" value="0"><div class="steps">${[
  [0, "몸통 파지"],
  [15, "세우기"],
  [42, "헤드 인계"],
  [59, "집게 수납"],
  [78, "내부 회전"],
]
  .map(
    ([t, n]) => `<button data-step="${t}" aria-pressed="false">${n}</button>`,
  )
  .join("")}</div></div></section>
<aside class="sidebar" aria-label="설계 비교와 조립 정보"><section class="side-section"><h2>설계안</h2><div class="variants"><button id="variant-a" aria-pressed="true">A · 분리형<small>2관절 엄지로 세우기</small></button><button id="variant-b" aria-pressed="false">B · 구동축 축소<small>픽업부 전체 1축 회전</small></button></div><p class="desc" id="variant-description"></p></section><section class="side-section"><h2>현재 동작</h2><h3 class="phase-title" id="phase-title"></h3><p class="desc" id="phase-description"></p><div class="part-note" id="constraint"></div></section><section class="side-section"><h2>검토 조건</h2><label class="sr-only" for="bolt">볼트 규격</label><select class="field" id="bolt">${PRESETS.map((s) => `<option value="${s.id}" ${s.id === "m8" ? "selected" : ""}>${s.label} · 육각 헤드</option>`).join("")}</select><p class="desc">노출된 육각 헤드 / 체결 토크 미정</p><table class="data-table"><tbody><tr><td>헤드 척 축방향 돌출</td><td>0 mm</td></tr><tr><td>직선 수납 행정</td><td>69.5 mm</td></tr><tr><td>팁 단면 → 뿌리 단면</td><td>3×4 → 12×10</td></tr><tr><td>손가락 중심선 길이</td><td>113.1 mm</td></tr><tr><td>독립 제어축 · 도구만</td><td id="axis-count">6</td></tr><tr><td>전체 도구 질량·정격</td><td>미확정</td></tr></tbody></table></section><section class="side-section"><h2>조립 살펴보기</h2><label class="toggle">외장 투명하게<input id="transparent" type="checkbox"></label><label class="toggle">부품 이름표<input id="labels" type="checkbox" checked></label><label class="toggle">분해 배치<input id="explode" type="checkbox"></label><p class="footnote">분해 배치는 부품 관계를 보기 위한 보기 기능입니다.</p></section><section class="side-section"><h2>검토 상태</h2><div class="status-note">장착부·가이드·지지 베어링의 배치를 표현했습니다. 척 내부의 쐐기·잠금, 구매 구동기, 공차·강도는 미확정입니다. 이 모델로 바로 가공을 발주할 수는 없습니다.</div><p class="footnote">회전 단계는 척 내부 회전 경로를 보여줍니다. 로봇의 나사 삽입·토크 제어 시뮬레이션은 포함하지 않습니다.</p></section><section><h2 class="desc">모델과 기록</h2><div class="downloads"><button id="export-model">조립 GLB 저장</button><button id="export-bom">부품 검토표 CSV</button></div><p id="export-status" class="footnote" role="status"></p><div class="doc-links"><a href="./mechanical-review.md" target="_blank" rel="noopener">구조·하중 검토 기록 ↗</a><a href="./concept.html" target="_blank" rel="noopener">이전 R06 동작 개념 ↗</a><a href="https://app.notion.com/p/3ebbf0105ac981379e65c20e9e332bcb" target="_blank" rel="noopener">Notion · 버전별 기록 ↗</a></div></section></aside></main>`;
const $ = <E extends HTMLElement = HTMLElement>(id: string) =>
  document.getElementById(id) as E;
const params = new URLSearchParams(location.search);
let variant: Variant = params.get("variant") === "b" ? "b" : "a",
  spec: BoltSpec = PRESETS[1],
  t = Math.max(0, Math.min(100, Number(params.get("progress") ?? "0") || 0)),
  playing = false;
const container = $("canvas"),
  scene = new T.Scene();
scene.background = new T.Color("#e3e9e6");
const camera = new T.OrthographicCamera(-300, 300, 300, -300, 0.1, 4000);
camera.up.set(0, 0, 1);
let renderer: T.WebGLRenderer,
  controls: OrbitControls,
  assembly: ReturnType<typeof makeEngineeringAssembly>;
const stage = new T.Group();
stage.rotation.x = Math.PI;
scene.add(stage);
const labels: HTMLDivElement[] = [];
let currentView = "detail";
function setView(view: string) {
  currentView = view;
  const target =
    view === "whole" ? new T.Vector3(0, -35, 180) : new T.Vector3(0, -60, 65);
  const offsets: Record<string, T.Vector3> = {
    whole: new T.Vector3(-550, -650, 350),
    detail: new T.Vector3(-400, -500, 230),
    side: new T.Vector3(-700, 0, 0),
    front: new T.Vector3(0, -700, 30),
  };
  camera.position.copy(target).add(offsets[view] ?? offsets.detail);
  controls.target.copy(target);
  camera.zoom = view === "whole" ? 0.82 : 1.15;
  camera.updateProjectionMatrix();
  controls.update();
  document
    .querySelectorAll<HTMLElement>("[data-view]")
    .forEach((b) =>
      b.setAttribute("aria-pressed", String(b.dataset.view === view)),
    );
}
function updateUI() {
  const s = assemblyPose(t);
  $("drawing-title").textContent =
    variant === "a"
      ? "A · 기능을 분리한 구조"
      : "B · 픽업부 전체를 돌리는 구조";
  $("variant-description").textContent =
    variant === "a"
      ? "두 주집게와 보조 엄지가 몸통을 유지하며 세웁니다. 헤드를 척에 넘긴 뒤 픽업 모듈 전체를 수납합니다."
      : "별도 엄지를 제거하고 파지한 카세트 전체를 90° 돌립니다. 한 제어축을 줄이는 대신 큰 회전 공간이 필요합니다.";
  $("axis-count").textContent = variant === "a" ? "6" : "5";
  for (const v of ["a", "b"])
    $("variant-" + v).setAttribute("aria-pressed", String(v === variant));
  const phases =
    t < 15
      ? [
          "몸통 파지",
          variant === "a"
            ? "가느다란 끝부분으로 몸통을 잡습니다. A의 접촉 패드는 자세 변화를 따라 회전합니다."
            : "일자 손가락이 몸통을 잡습니다. 볼트는 카세트에 고정된 채 회전합니다.",
        ]
      : t < 42
        ? [
            "헤드가 위로 향하도록 세우기",
            variant === "a"
              ? "25+25mm 보조 엄지가 끝부분을 누릅니다. 몸통 접촉점은 유지합니다."
              : "측면 베어링이 지지하는 실제 회전축을 중심으로 카세트와 볼트가 함께 원호를 그립니다.",
          ]
        : t < 59
          ? [
              "내부 척으로 인계",
              "헤드 접촉면이 닫힌 다음 몸통 집게를 엽니다. 실기에는 착좌·잠금 확인이 필요합니다.",
            ]
          : t < 78
            ? [
                "작업면에서 픽업부 치우기",
                "가이드 두 개와 나사 구동축을 따라 뒤로 60mm, 위로 35mm 이동합니다.",
              ]
            : [
                "고정 외장 안에서 회전",
                "회전축과 헤드 척만 회전합니다. 픽업부는 작업면에서 빠져 있고 척은 축방향으로 나오지 않습니다.",
              ];
  $("phase-title").textContent = phases[0];
  $("phase-description").textContent = phases[1];
  $("constraint").textContent =
    s.release > 0
      ? "헤드 척 유지 → 몸통 해제 → 수납 → 회전"
      : variant === "b"
        ? "몸통 파지를 유지한 카세트 전체의 강체 회전"
        : "몸통 유지 + 엄지 접촉 · 회전 패드는 수동";
  $("progress").textContent = `${t.toFixed(1)} / 100`;
  $<HTMLInputElement>("motion").value = String(t);
  $("play").textContent = playing ? "Ⅱ 일시정지" : "▶ 동작 보기";
  const start = t < 15 ? 0 : t < 42 ? 15 : t < 59 ? 42 : t < 78 ? 59 : 78;
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
  assembly = makeEngineeringAssembly(variant, spec);
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
  renderer.domElement.setAttribute("aria-label", "R07 그리퍼 조립 3D 화면");
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
  grid.position.set(0, -30, -100);
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
  setView(params.get("view") === "whole" ? "whole" : "detail");
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
    const s = assemblyPose(t);
    for (let i = 0; i < labels.length; i++) {
      const l = assembly.labels[i];
      let p = l.point.clone();
      if (i === 4) p.applyMatrix4(gripTransform(variant, s));
      if (i === 2) p.addScaledVector(DESIGN.retract, s.retract);
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
      $<HTMLInputElement>("explode").checked = false;
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
  for (const v of ["a", "b"] as const)
    $("variant-" + v).onclick = () => {
      variant = v;
      playing = false;
      rebuild();
      const u = new URL(location.href);
      u.searchParams.set("variant", v);
      history.replaceState(null, "", u);
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
      exported.name = "R07-REVIEW-METRES";
      exported.userData = {
        status: "assembly review, not manufacturing release",
        units: "metres",
        variant,
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
        `R07-${variant}-${spec.id}-assembly-review.glb`,
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
      ...ASSEMBLY_BOM,
    ];
    const csv =
      "\uFEFF" +
      rows
        .map((r) => r.map((v) => '"' + v.replaceAll('"', '""') + '"').join(","))
        .join("\r\n");
    save(
      new Blob([csv], { type: "text/csv;charset=utf-8" }),
      "R07-component-review.csv",
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
