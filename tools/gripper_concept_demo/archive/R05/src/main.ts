import "./style.css";
import { DURATION, PRESETS, STAGES, sampleCycle } from "./timeline";
import { Viewer, type ViewName } from "./viewer";
const app = document.querySelector<HTMLDivElement>("#app")!;
app.innerHTML = `
<header class="topbar"><a class="brand" href="./" aria-label="동작 연구실 처음으로"><span class="brand-mark">◎</span><span>동작 연구실<small>ADAPTIVE HEAD / TAPERED FINGERS</small></span></a><div class="top-meta"><span class="status-dot"></span> FR3 · 7축 로봇팔<span class="concept-tag">개념 시연</span></div></header>
<main class="workspace">
 <section class="stage-area" aria-label="3D 동작 시연">
  <div class="scene-heading"><div><p class="eyebrow">BIN PICKING → FASTENING</p><h1>볼트, 집기에서 체결까지.</h1><p class="subtitle">얇은 일자형 팁으로 집고, 같은 헤드 척으로 체결합니다.</p></div><span class="scene-id">ASSEMBLY<br><b>FR3—R05</b></span></div>
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
   <div class="phase-track" aria-label="동작 단계">${STAGES.map((s, i) => `<button class="phase" data-stage="${i}" title="${s.name}" disabled><span>${String(i + 1).padStart(2, "0")}</span>${s.short}</button>`).join("")}</div>
  </section>
 </section>
 <aside class="sidebar" aria-label="동작 설명과 보기 설정">
  <section class="explanation"><div class="section-kicker"><span>동작 해설</span><output id="step-count">01 / 11</output></div><h2 id="phase-title">볼트 접근</h2><p id="phase-description">${STAGES[0].text}</p><div class="active-part"><span>현재 동작 부품</span><strong id="active-part">${STAGES[0].part}</strong></div><p class="grip-state" id="grip-state" aria-live="off"></p><div class="phase-nav"><button id="prev" disabled>← 이전 단계</button><button id="next" disabled>다음 단계 →</button></div></section>
  <section class="settings"><h3>대상 볼트</h3><label class="sr-only" for="bolt">볼트 규격</label><select id="bolt">${PRESETS.map((s) => `<option value="${s.id}" ${s.id === "m8" ? "selected" : ""}>${s.label}</option>`).join("")}</select><p class="field-note">M6~M10 모두 같은 팁·같은 6조 척을 사용합니다.</p><dl class="dimensions"><div><dt>몸통 지름</dt><dd id="bolt-diameter">8 <span>mm</span></dd></div><div><dt>몸통 길이</dt><dd id="bolt-length">35 <span>mm</span></dd></div></dl></section>
  <section class="settings view-settings"><h3>내부 살펴보기</h3><label class="toggle-row"><span>외장 투명하게</span><input type="checkbox" id="transparent"/><span class="switch" aria-hidden="true"></span></label><label class="toggle-row"><span>부품 이름표 <small>확대 시</small></span><input type="checkbox" id="labels" checked/><span class="switch" aria-hidden="true"></span></label><label class="toggle-row"><span>확대창 표시</span><input type="checkbox" id="inset" checked/><span class="switch" aria-hidden="true"></span></label><label class="toggle-row"><span>부품 분해 보기</span><input type="checkbox" id="exploded"/><span class="switch" aria-hidden="true"></span></label><p id="explode-note" class="field-note">분해 보기에서는 재생이 일시정지됩니다.</p></section>
  <div class="concept-note"><span>R05 · 구조와 크기</span><p>일자형 팁은 뿌리 8×8mm에서 끝 3×4mm로 가늘어집니다. 보조 엄지는 25+25mm. 여섯 턱이 육각 헤드 대변 10~17mm에 맞춰 닫힙니다.</p><p>파지 모듈은 Zimmer GEP2006(180g)급, 체결부는 Kolver KDS-PL50CA(Ø57×322mm·1.8kg)의 설치 공간을 반영했습니다. 합계 1.98kg에 척·슬라이드·엄지·배선 무게가 추가됩니다.</p><p>척 구동·잠금과 팁은 자체 설계안입니다. 지그가 체결 반력을 받습니다. 위상이 맞은 육각 헤드를 전제로 하며, 실제 마찰·잠금 강도·토크와 무더기 충돌은 검증하지 않은 동작 모델입니다.</p><a href="./design-notes.md" target="_blank" rel="noopener">설계 근거·가정·검증 범위 ↗</a><a href="https://www.zimmer-group.com/en-us/products/components/handling-technology/2-jaw-parallel-grippers/series-gep2000" target="_blank" rel="noopener">기준 파지 모듈 ↗</a><a href="https://kolver.com/en/products/ca-series" target="_blank" rel="noopener">기준 체결 스핀들 ↗</a><a href="./fr3/NOTICE" target="_blank" rel="noopener">FR3 모델 출처 ↗</a></div>
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
const play = $<HTMLButtonElement>("play"),
  timeline = $<HTMLInputElement>("timeline");
function updateUI() {
  const spec = PRESETS.find(
    (p) => p.id === $<HTMLSelectElement>("bolt").value,
  )!;
  const s = sampleCycle(time, spec);
  $("grip-state").textContent =
    s.time < 5
      ? "파지 준비"
      : s.time < 14
        ? "몸통 유지 · 회전 패드와 엄지로 세움"
        : s.time < 16
          ? "몸통 파지 유지 · 헤드 척 닫힘"
          : s.time < 23
            ? "헤드 척으로 유지 · 집게 후퇴"
            : s.time < 61
              ? `지그 반력 지지 · 피치 ${spec.pitch * 1000}mm로 체결`
              : s.time < 63
                ? `최종 체결 · 예시 목표 ${spec.exampleTorque}Nm (측정 아님)`
                : "체결 완료 위치 · 헤드 해제";
  timeline.value = String(time);
  timeline.style.setProperty("--progress", `${(time / DURATION) * 100}%`);
  $("current-time").textContent = time.toFixed(1).padStart(4, "0");
  play.innerHTML = playing ? "Ⅱ <span>일시정지</span>" : "▶ <span>재생</span>";
  play.setAttribute("aria-label", playing ? "일시정지" : "재생");
  if (s.stage !== currentStage) {
    currentStage = s.stage;
    const phase = STAGES[s.stage];
    $("phase-title").textContent = phase.name;
    $("phase-description").textContent = phase.text;
    $("active-part").textContent = phase.part;
    $("step-count").textContent =
      `${String(s.stage + 1).padStart(2, "0")} / 11`;
    document
      .querySelectorAll<HTMLButtonElement>("[data-stage]")
      .forEach((b, i) => {
        b.classList.toggle("active", i === s.stage);
        b.classList.toggle("past", i < s.stage);
        if (i === s.stage) b.setAttribute("aria-current", "step");
        else b.removeAttribute("aria-current");
      });
  }
  $<HTMLButtonElement>("prev").disabled = !ready || s.stage === 0;
  $<HTMLButtonElement>("next").disabled =
    !ready || s.stage === STAGES.length - 1;
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
  stopAndSeek(STAGES[Math.max(0, currentStage - 1)].start),
);
$("next").addEventListener("click", () =>
  stopAndSeek(STAGES[Math.min(STAGES.length - 1, currentStage + 1)].start),
);
document
  .querySelectorAll<HTMLButtonElement>("[data-stage]")
  .forEach((b) =>
    b.addEventListener("click", () =>
      stopAndSeek(STAGES[Number(b.dataset.stage)].start),
    ),
  );
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
      "[data-stage], #reset, #prev, #next, [data-view], .camera-buttons button, .sidebar input, .sidebar select, #speed",
    )
    .forEach((b) => (b.disabled = true));
  updateUI();
}
$("viewport").addEventListener("viewer-error", (e) =>
  showError((e as CustomEvent<string>).detail),
);
async function start() {
  try {
    viewer = new Viewer($("viewport"), $("inset-label"));
    await viewer.load((n) => {
      const progress = document.getElementById("load-progress");
      if (progress)
        progress.textContent = `FR3 링크 ${n} / 8 · 자동 조절 헤드 척`;
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
