import "./style.css";
import { DURATION, PRESETS, STAGES, sampleCycle } from "./timeline";
import { Viewer, type ViewName } from "./viewer";
import { VARIANTS, type Variant } from "./variants";
import {
  DESIGNS,
  designOf,
  stagesFor,
  type DesignId,
  DRAW_IN,
  THUMB,
  NOSE,
  TWEEZER,
  minPitch,
  compactBoltWorld,
  compactJoints,
} from "./compact-kinematics";
import { makeCompactGripper } from "./compact-model";
// concept.html = R06 A/B comparison; index.html / compact.html = R09 compact tool on the same cell.
const R09 = document.body.dataset.tool === "r09";
const designParam = new URLSearchParams(location.search).get("design") ?? "c2"; // R10 = 시안 2
const design = (designParam in DESIGNS ? designParam : "r09") as DesignId;
const D = designOf(design),
  BODY = D.body,
  STOW = D.stow;
const stages = R09 ? stagesFor(design) : STAGES;
const stageAt = (t: number) => {
  const i = stages.findIndex((s) => t < s.end);
  return i < 0 ? stages.length - 1 : i;
};
const r08Volume = 152 * 144 * 250,
  r09Volume = BODY.width * BODY.height * BODY.length;
const designNotes: Record<DesignId, string> = {
  r09: "R09 현재안. 상자형 몸체, 가이드 2개·이송나사.",
  c1: "원통 몸체. 가이드·이송나사·후방 이송모터 대신 링 모터가 스핀들을 감싼 나사 슬리브를 돌리고 요크의 링 너트가 따라갑니다.",
  c2: "시안 1 + 스프링 척과 캠. 요크가 한 번 물러나면 인입·척 닫힘·핀셋 벌림·수납이 이어지고, 3mm 초과행정이 척을 엽니다. 척 폐쇄 구동부 없음, 11단계.",
  c3: "노즈 22mm, 몸체 모서리 10mm 모따기(팔각 단면). 노즈가 길어진 만큼 수납 행정 42mm, 공구 길이 112mm.",
};
const noteFirst: Record<DesignId, string> = {
  r09: "헤드 고정 → 몸통 해제 → 수납 → 회전 순서는 R08과 같습니다. 엄지는 세운 뒤 인입 전에 접고, 세운 볼트는 핀셋 끝 패드에 매달린 채 척으로 들어갑니다.",
  c1: "시안 1은 R09와 같은 순서에 이송 방식만 바뀝니다. 링 모터가 나사 슬리브를 돌리고 요크 링 너트가 따라가며, 타이로드 3개가 요크의 회전을 막습니다.",
  c2: "요크가 한 번 물러나는 동안 인입 → 척 닫힘 → 핀셋 벌림 → 수납이 이어집니다. 척은 스프링으로 닫혀 있고 단방향 트리거가 걸리며, 캠이 수납 첫 0.6mm에서 핀셋을 벌립니다. 체결이 끝나면 3mm 초과행정이 해제 로드로 척을 엽니다. 엄지는 세운 뒤 인입 전에 접습니다.",
  c3: "시안 3은 노즈를 22mm로 늘리고 몸체 모서리를 10mm 모따기한 팔각 단면입니다. 순서는 R09와 같고 수납 행정만 42mm입니다.",
};
const designTabs = `<div class="variant-tabs" role="group" aria-label="R10 검토 시안">${(["r09", "c1", "c2", "c3"] as DesignId[]).map((id) => `<a class="compare-jump" href="?design=${id}" aria-current="${id === design}">${id === "r09" ? "R09" : id === "c2" ? "R10(시안 2)" : designOf(id).label.split(" · ")[0]}</a>`).join("")}</div>`;
const r09Panel = `<section class="settings variant-settings"><h3>${design === "r09" ? "R09 · 핀셋형 · 가는 노즈" : design === "c2" ? D.label : `R10 검토 · ${D.label}`}</h3>${designTabs}<strong>${designNotes[design]} 몸체는 R08 부피의 ${Math.round((r09Volume / r08Volume) * 1000) / 10}%(외접 상자 기준).</strong><dl class="dimensions"><div><dt>몸체 외형</dt><dd>${D.shape === "cyl" ? `Ø${BODY.width}` : `${BODY.width}×${BODY.height}`}×${BODY.length} <span>mm</span></dd></div><div><dt>R08</dt><dd>152×144×250 <span>mm</span></dd></div><div><dt>노즈</dt><dd>Ø${NOSE.radius * 2}×${D.nose} <span>mm</span></dd></div><div><dt>공정 단계</dt><dd>${stages.length} <span>단계</span></dd></div><div><dt>최소 볼트 간격</dt><dd>${PRESETS.map((p) => Math.ceil(minPitch(p))).join("/")} <span>mm</span></dd></div><div><dt>핀셋 끝</dt><dd>${TWEEZER.tipWidth * 2}×${TWEEZER.tipThick * 2} <span>mm</span></dd></div><div><dt>인입 / 수납</dt><dd>${DRAW_IN} / ${STOW} <span>mm</span></dd></div></dl><p class="field-note">최소 간격은 M6/M8/M10 기준입니다. 체결 중 이웃 볼트 머리 높이에는 노즈만 있고, 몸체는 노즈 길이만큼 뒤에 있습니다. 파지 중 엄지는 핀셋 끝보다 위에 있습니다.</p><a class="compare-jump" href="./integrated.html">이전 R08 조립 보기 →</a><a class="compare-jump" href="./concept.html">R06 A/B 시연 →</a></section>`;
const app = document.querySelector<HTMLDivElement>("#app")!;
app.innerHTML = `
<header class="topbar"><a class="brand" href="./" aria-label="동작 연구실 처음으로"><span class="brand-mark">◎</span><span>동작 연구실<small>ADAPTIVE HEAD / TAPERED FINGERS</small></span></a><div class="top-meta"><span class="status-dot"></span> FR3 · 7축 로봇팔<span class="concept-tag">${R09 ? `${design === "c2" ? "R10" : design.toUpperCase()} · 빈피킹 시뮬레이션` : "개념 시연"}</span></div></header>
<main class="workspace">
 <section class="stage-area" aria-label="3D 동작 시연">
  <div class="scene-heading"><div><p class="eyebrow">BIN PICKING → FASTENING</p><h1>볼트, 집기에서 체결까지.</h1><p class="subtitle">${R09 ? `핀셋으로 집고 몸체 안에서 세워, 가는 노즈로 촘촘한 볼트 사이에 체결. 지그 불필요.` : "더 날카로운 팁. 본체 안에서 회전하는 두 가지 구조."}</p></div><span class="scene-id">ASSEMBLY<br><b>FR3—${R09 ? (design === "c2" ? "R10" : design.toUpperCase()) : "R06"}</b></span></div>
  <div class="viewport" id="viewport">
   <div class="view-tabs" aria-label="시점 선택">${[
     ["whole", "전체"],
     ["detail", "그리퍼 확대"],
     ["front", "정면"],
     ["side", "측면"],
   ]
     .map(
       ([v, l]) =>
         `<button disabled data-view="${v}" aria-pressed="${v === "whole"}">${l}</button>`,
     )
     .join("")}</div>
   <div id="inset-label" class="inset-label" hidden><span>파지 인계 확대 <b>LIVE VIEW</b></span></div>
   <div class="scene-legend"><span><i class="swatch blue"></i>주집게 2개</span><span><i class="swatch rod"></i>보조 엄지</span><span><i class="swatch orange"></i>헤드 척</span><span><i class="swatch gold"></i>대상 볼트</span></div>
   <div class="camera-buttons" aria-label="카메라 조작"><button disabled id="rotate-left" aria-label="시점 왼쪽으로 회전">↶</button><button disabled id="rotate-right" aria-label="시점 오른쪽으로 회전">↷</button><button disabled id="zoom-in" aria-label="확대">＋</button><button disabled id="zoom-out" aria-label="축소">−</button></div>
   <span class="orbit-hint">드래그로 회전 · 스크롤로 확대</span>
   <div id="loading" class="loading" role="status"><span class="loader"></span><strong>로봇 모델을 준비하고 있습니다</strong><span id="load-progress">FR3 링크 0 / 8</span></div>
  </div>
  <section class="transport" aria-label="재생 제어">
   <div class="transport-top"><div class="play-actions"><button class="play-button" id="play" disabled>▶ <span>재생</span></button><button class="icon-button" id="reset" aria-label="처음으로" disabled>↺</button><div class="time-readout"><output id="current-time">00.0</output><span>/ ${DURATION.toFixed(1)} s</span></div></div><div class="speed-control"><label for="speed">재생 속도</label><select id="speed"><option value="0.25">0.25×</option><option value="0.5">0.5×</option><option value="1" selected>1×</option><option value="2">2×</option></select></div></div>
   <label class="sr-only" for="timeline">동작 시간</label><input id="timeline" type="range" min="0" max="${DURATION}" step="0.01" value="0" disabled/>
   <div class="phase-track" aria-label="동작 단계" style="--phases:${stages.length}">${stages.map((s, i) => `<button class="phase" data-stage="${i}" title="${s.name}" disabled><span>${String(i + 1).padStart(2, "0")}</span>${s.short}</button>`).join("")}</div>
  </section>
 </section>
 <aside class="sidebar" aria-label="동작 설명과 보기 설정">
  ${R09 ? r09Panel : `<section class="settings variant-settings"><h3>설계안 비교</h3><div class="variant-tabs" role="group" aria-label="그리퍼 설계안"><button id="variant-a" data-variant="a" aria-pressed="true">A · 분리 수납형</button><button id="variant-b" data-variant="b" aria-pressed="false">B · 통합 구조</button></div><strong id="variant-structure">${VARIANTS.a.structure}</strong><p id="variant-motion" class="field-note">${VARIANTS.a.motion}</p><p id="variant-tradeoff" class="field-note">${VARIANTS.a.tradeoff}</p><button id="compare-handoff" class="compare-jump">인계·수납 단계 비교 →</button><button id="compare-drive" class="compare-jump">내부 회전 비교 →</button></section>`}
  <section class="explanation"><div class="section-kicker"><span>동작 해설</span><output id="step-count">01 / ${stages.length}</output></div><h2 id="phase-title">볼트 접근</h2><p id="phase-description">${stages[0].text}</p><div class="active-part"><span>현재 동작 부품</span><strong id="active-part">${stages[0].part}</strong></div><p class="grip-state" id="grip-state" aria-live="off"></p><div class="phase-nav"><button id="prev" disabled>← 이전 단계</button><button id="next" disabled>다음 단계 →</button></div></section>
  <section class="settings"><h3>대상 볼트</h3><label class="sr-only" for="bolt">볼트 규격</label><select id="bolt">${PRESETS.map((s) => `<option value="${s.id}" ${s.id === "m8" ? "selected" : ""}>${s.label}</option>`).join("")}</select><p class="field-note">M6~M10 모두 같은 설계안에서 간격만 조절합니다.</p><dl class="dimensions"><div><dt>몸통 지름</dt><dd id="bolt-diameter">8 <span>mm</span></dd></div><div><dt>몸통 길이</dt><dd id="bolt-length">35 <span>mm</span></dd></div></dl></section>
  <section class="settings view-settings"><h3>내부 살펴보기</h3><label class="toggle-row"><span>외장 투명하게</span><input type="checkbox" id="transparent"/><span class="switch" aria-hidden="true"></span></label><label class="toggle-row"><span>부품 이름표 <small>확대 시</small></span><input type="checkbox" id="labels" checked/><span class="switch" aria-hidden="true"></span></label><label class="toggle-row"><span>확대창 표시</span><input type="checkbox" id="inset" checked/><span class="switch" aria-hidden="true"></span></label><label class="toggle-row"><span>부품 분해 보기</span><input type="checkbox" id="exploded"/><span class="switch" aria-hidden="true"></span></label><p id="explode-note" class="field-note">분해 보기에서는 재생이 일시정지됩니다.</p></section>
  ${R09 ? `<div class="concept-note"><span>${design === "r09" ? "R09" : design === "c2" ? "R10" : "R10 시안"} · 검토 범위</span><p>${noteFirst[design]}</p><p>${design === "c2" ? "스프링 척의 파지력, 트리거·래치 신뢰성, 캠 마모는 실물 검증이 필요합니다. " : ""}지그·키홈 없이 체결하므로 반력은 로봇팔이 받습니다. FR3 손목 관절 정격(약 12Nm)으로는 M8·M10 예시 토크를 감당하지 못하므로 더 큰 팔이 필요합니다. 구동부는 미선정이고 질량·강도·무더기 충돌은 검증하지 않았습니다. 제작 승인 도면이 아닙니다.</p><a href="./fr3/NOTICE" target="_blank" rel="noopener">FR3 모델 출처 ↗</a></div>` : `<div class="concept-note"><span>R06 · 내부 회전 구조</span><p>팁을 뿌리 6×5mm에서 끝 1.6×2.4mm로 날렵하게 다듬었습니다. A는 내부 6조 척, B는 두 집게 카세트의 2단 접촉면으로 파지와 체결을 통합합니다. 체결부의 축방향 돌출은 두 안 모두 0mm입니다.</p><p>A는 소형 평행 모듈과 별도 척을, B는 자체 2조 회전 카세트를 사용합니다. 체결 스핀들 설치 공간은 공통입니다. B의 공통 캠·잠금은 구조 축소를 위한 설계안이며 실물 부품 수·질량·구동력은 미확정입니다.</p><p>척 구동·잠금과 팁은 자체 설계안입니다. 지그가 체결 반력을 받습니다. 위상이 맞은 육각 헤드를 전제로 하며, 실제 마찰·잠금 강도·토크와 무더기 충돌은 검증하지 않은 동작 모델입니다.</p><a href="./design-notes.md" target="_blank" rel="noopener">설계 근거·가정·검증 범위 ↗</a><a href="https://www.zimmer-group.com/en-us/products/components/handling-technology/2-jaw-parallel-grippers/series-gep2000" target="_blank" rel="noopener">기준 파지 모듈 ↗</a><a href="https://kolver.com/en/products/ca-series" target="_blank" rel="noopener">기준 체결 스핀들 ↗</a><a href="./fr3/NOTICE" target="_blank" rel="noopener">FR3 모델 출처 ↗</a></div>`}
 </aside>
</main>
<footer class="footer"><span><i class="status-dot"></i><span id="app-status" role="status">모델 불러오는 중</span></span><span>IN-HAND ALIGNMENT · VARIABLE HEAD CHUCK</span></footer>`;
const $ = <T extends HTMLElement = HTMLElement>(id: string) =>
  document.getElementById(id) as T;
let viewer: Viewer | undefined,
  time = 0,
  playing = false,
  ready = false,
  failed = false,
  animationId = 0,
  last = performance.now(),
  currentStage = -1;
let variant: Variant = "a";
const play = $<HTMLButtonElement>("play"),
  timeline = $<HTMLInputElement>("timeline");
function updateUI() {
  const spec = PRESETS.find(
    (p) => p.id === $<HTMLSelectElement>("bolt").value,
  )!;
  const s = sampleCycle(time, spec);
  const stage = stageAt(time);
  $("grip-state").textContent = R09
    ? time < 5
      ? "파지 준비 · 핀셋 끝만 앞으로"
      : time < 14
        ? "핀셋 파지 · 엄지로 세움"
        : time < 20.5
          ? "엄지 접기 · 인입 · 헤드 척 닫힘"
          : time < 25
            ? "헤드 유지 · 핀셋 벌려 수납"
            : time < 61
              ? `척과 볼트만 회전 · 피치 ${spec.pitch * 1000}mm`
              : time < 63
                ? `최종 체결 · 예시 목표 ${spec.exampleTorque}Nm (측정 아님)`
                : "체결 완료 위치 · 재장전"
    : s.time < 5
      ? "파지 준비"
      : s.time < 14
        ? "몸통 유지 · 회전 패드와 엄지로 세움"
        : s.time < 16
          ? "몸통 파지 유지 · 헤드 척 닫힘"
          : s.time < 23
            ? "헤드 유지 · 몸통 팁 수납"
            : s.time < 61
              ? `${variant.toUpperCase()} · 본체 내부 회전 · 피치 ${spec.pitch * 1000}mm`
              : s.time < 63
                ? `최종 체결 · 예시 목표 ${spec.exampleTorque}Nm (측정 아님)`
                : "체결 완료 위치 · 헤드 해제";
  timeline.value = String(time);
  timeline.style.setProperty("--progress", `${(time / DURATION) * 100}%`);
  $("current-time").textContent = time.toFixed(1).padStart(4, "0");
  play.innerHTML = playing ? "Ⅱ <span>일시정지</span>" : "▶ <span>재생</span>";
  play.setAttribute("aria-label", playing ? "일시정지" : "재생");
  if (stage !== currentStage) {
    currentStage = stage;
    const phase = stages[stage];
    $("phase-title").textContent = phase.name;
    $("phase-description").textContent = phase.text;
    $("active-part").textContent = phase.part;
    $("step-count").textContent =
      `${String(stage + 1).padStart(2, "0")} / ${stages.length}`;
    document
      .querySelectorAll<HTMLButtonElement>("[data-stage]")
      .forEach((b, i) => {
        b.classList.toggle("active", i === stage);
        b.classList.toggle("past", i < stage);
        if (i === stage) b.setAttribute("aria-current", "step");
        else b.removeAttribute("aria-current");
      });
  }
  $<HTMLButtonElement>("prev").disabled = !ready || stage === 0;
  $<HTMLButtonElement>("next").disabled = !ready || stage === stages.length - 1;
  $("app-status").textContent = failed
    ? "3D 장면을 불러오지 못했습니다"
    : !ready
      ? "모델 불러오는 중"
      : playing
        ? "동작 재생 중"
        : s.finished
          ? "사이클 완료 · 처음으로 돌아가 다시 재생할 수 있습니다"
          : "일시정지 · 장면을 자유롭게 살펴보세요";
}
function seek(t: number) {
  time = Math.max(0, Math.min(DURATION, t));
  viewer?.update(time);
  updateUI();
}
function setPlaying(value: boolean) {
  playing = value;
  if (value) {
    $<HTMLInputElement>("exploded").checked = false;
    viewer?.setOptions({ exploded: false });
    if (time >= DURATION) time = 0;
  }
  seek(time);
}
function stopAndSeek(t: number) {
  playing = false;
  seek(t);
}
play.addEventListener("click", () => setPlaying(!playing));
$("reset").addEventListener("click", () => stopAndSeek(0));
timeline.addEventListener("input", () => stopAndSeek(Number(timeline.value)));
$("prev").addEventListener("click", () =>
  stopAndSeek(stages[Math.max(0, currentStage - 1)].start),
);
$("next").addEventListener("click", () =>
  stopAndSeek(stages[Math.min(stages.length - 1, currentStage + 1)].start),
);
document
  .querySelectorAll<HTMLButtonElement>("[data-stage]")
  .forEach((b) =>
    b.addEventListener("click", () =>
      stopAndSeek(stages[Number(b.dataset.stage)].start),
    ),
  );
function chooseVariant(value: Variant) {
  variant = value;
  playing = false;
  viewer?.setVariant(value);
  document
    .querySelectorAll<HTMLButtonElement>("[data-variant]")
    .forEach((b) =>
      b.setAttribute("aria-pressed", String(b.dataset.variant === value)),
    );
  $("variant-structure").textContent = VARIANTS[value].structure;
  $("variant-motion").textContent = VARIANTS[value].motion;
  $("variant-tradeoff").textContent = VARIANTS[value].tradeoff;
  currentStage = -1;
  updateUI();
  const url = new URL(location.href);
  url.searchParams.set("variant", value);
  history.replaceState(null, "", url);
}
for (const value of ["a", "b"] as const)
  $("variant-" + value)?.addEventListener("click", () => chooseVariant(value));
$("compare-handoff")?.addEventListener("click", () => {
  stopAndSeek(17.8);
  view("detail");
});
$("compare-drive")?.addEventListener("click", () => {
  $<HTMLInputElement>("transparent").checked = true;
  viewer?.setOptions({ transparent: true });
  stopAndSeek(40);
  view("detail");
});
function view(name: ViewName) {
  viewer?.setView(name);
  document
    .querySelectorAll<HTMLButtonElement>("[data-view]")
    .forEach((b) =>
      b.setAttribute("aria-pressed", String(b.dataset.view === name)),
    );
}
document
  .querySelectorAll<HTMLButtonElement>("[data-view]")
  .forEach((b) =>
    b.addEventListener("click", () => view(b.dataset.view as ViewName)),
  );
$("bolt").addEventListener("change", () => {
  const spec = PRESETS.find(
    (p) => p.id === $<HTMLSelectElement>("bolt").value,
  )!;
  playing = false;
  time = 0;
  viewer?.setSpec(spec);
  $("bolt-diameter").innerHTML = `${spec.diameter * 1000} <span>mm</span>`;
  $("bolt-length").innerHTML = `${spec.length * 1000} <span>mm</span>`;
  seek(0);
});
for (const key of ["transparent", "labels", "inset", "exploded"] as const) {
  $(key).addEventListener("change", () => {
    const checked = $<HTMLInputElement>(key).checked;
    if (key === "exploded" && checked) {
      playing = false;
      view("detail");
    }
    viewer?.setOptions({ [key]: checked });
    updateUI();
  });
}
$("rotate-left").addEventListener("click", () => viewer?.nudgeCamera(1));
$("rotate-right").addEventListener("click", () => viewer?.nudgeCamera(-1));
$("zoom-in").addEventListener("click", () => viewer?.zoom(0.8));
$("zoom-out").addEventListener("click", () => viewer?.zoom(1.25));
function showError(message: string) {
  failed = true;
  ready = false;
  playing = false;
  $("loading").hidden = false;
  $("loading").setAttribute("role", "alert");
  $("loading").replaceChildren();
  const strong = document.createElement("strong");
  strong.textContent = "3D 화면을 열 수 없습니다";
  const p = document.createElement("p");
  p.textContent = message;
  const b = document.createElement("button");
  b.textContent = "다시 불러오기";
  b.onclick = () => location.reload();
  $("loading").append(strong, p, b);
  play.disabled = true;
  timeline.disabled = true;
  document
    .querySelectorAll<HTMLButtonElement | HTMLInputElement | HTMLSelectElement>(
      "[data-stage], #reset, #prev, #next, [data-view], .camera-buttons button, .sidebar input, .sidebar select, [data-variant], #compare-handoff, #compare-drive, #speed",
    )
    .forEach((b) => (b.disabled = true));
  updateUI();
}
$("viewport").addEventListener("viewer-error", (e) =>
  showError((e as CustomEvent<string>).detail),
);
async function start() {
  try {
    viewer = new Viewer(
      $("viewport"),
      $("inset-label"),
      R09
        ? {
            makeGripper: () => makeCompactGripper(undefined, design),
            joints: (t, id) => compactJoints(t, id, design),
            boltWorld: (t, spec) => compactBoltWorld(t, spec, design),
            focusZ: BODY.length / 1000 + 0.02,
            keyways: false,
            neighbourPitch: (spec) => (minPitch(spec) + 0.5) / 1000,
            detailLift: 0.16,
          }
        : undefined,
    );
    await viewer.load((n) => {
      const progress = document.getElementById("load-progress");
      if (progress)
        progress.textContent = `FR3 링크 ${n} / 8 · ${R09 ? "R09 소형 그리퍼" : "자동 조절 헤드 척"}`;
    });
    if (failed) return;
    ready = true;
    document
      .querySelectorAll<HTMLButtonElement>(
        ".camera-buttons button, [data-view]",
      )
      .forEach((b) => (b.disabled = false));
    $("loading").hidden = true;
    play.disabled = false;
    timeline.disabled = false;
    $<HTMLButtonElement>("reset").disabled = false;
    document
      .querySelectorAll<HTMLButtonElement>("[data-stage]")
      .forEach((b) => (b.disabled = false));
    const params = new URLSearchParams(location.search);
    if (!R09 && params.get("variant") === "b") chooseVariant("b");
    const initialTime = Number(params.get("time") ?? 0);
    seek(Number.isFinite(initialTime) ? initialTime : 0);
    const initialView = params.get("view");
    if (["whole", "detail", "front", "side"].includes(initialView ?? ""))
      view(initialView as ViewName);
  } catch (error) {
    console.error(error);
    showError("WebGL 지원 여부와 모델 파일 연결을 확인한 뒤 다시 불러오세요.");
  }
}
function frame(now: number) {
  // Wall-clock playback stays at the selected speed even on a low-FPS GPU.
  // visibilitychange resets the clock and pauses before a hidden-tab gap.
  const dt = Math.max(0, (now - last) / 1000);
  last = now;
  if (playing && ready) {
    time = Math.min(
      DURATION,
      time + dt * Number($<HTMLSelectElement>("speed").value),
    );
    if (time === DURATION) playing = false;
    seek(time);
  }
  if (!failed) viewer?.render();
  animationId = requestAnimationFrame(frame);
}
document.addEventListener("visibilitychange", () => {
  last = performance.now();
  if (document.hidden && playing) setPlaying(false);
});
window.addEventListener("pagehide", (event) => {
  if (event.persisted) return;
  cancelAnimationFrame(animationId);
  viewer?.dispose();
});
void start();
animationId = requestAnimationFrame(frame);
