import * as T from "three";
import { OrbitControls } from "three/addons/controls/OrbitControls.js";
import {
  loadRobot,
  makeGripper,
  makeCell,
  makeBolt,
  disposeObject,
} from "./models";
import {
  sampleCycle,
  PRESETS,
  type BoltSpec,
  type CycleState,
} from "./timeline";
import { jointsAt, boltWorldAt } from "./kinematics";
import { palette } from "./theme";
export type ViewName = "whole" | "detail" | "front" | "side";
export class Viewer {
  readonly scene = new T.Scene();
  readonly camera = new T.PerspectiveCamera(38, 1, 0.002, 20);
  readonly detailCamera = new T.PerspectiveCamera(34, 1, 0.002, 20);
  readonly renderer: T.WebGLRenderer;
  readonly controls: OrbitControls;
  private robot!: Awaited<ReturnType<typeof loadRobot>>;
  private gripper = makeGripper();
  private bolt = makeBolt(PRESETS[1], true);
  private spec: BoltSpec = PRESETS[1];
  private state = sampleCycle(0);
  private view: ViewName = "whole";
  private transparent = false;
  private exploded = false;
  private labels = true;
  private inset = true;
  private labelNodes: HTMLSpanElement[] = [];
  private resizeObserver: ResizeObserver;
  private width = 1;
  private height = 1;
  private focused = new T.Vector3();
  private lastFocus = new T.Vector3();
  private initialized = false;
  constructor(
    private host: HTMLElement,
    private insetLabel: HTMLElement,
  ) {
    const colors = palette();
    this.scene.background = new T.Color(colors.surface);
    this.renderer = new T.WebGLRenderer({ antialias: true, alpha: false });
    this.renderer.setPixelRatio(Math.min(devicePixelRatio, 1.75));
    this.renderer.shadowMap.enabled = true;
    this.renderer.shadowMap.type = T.PCFShadowMap;
    this.renderer.setClearColor(colors.surface);
    this.renderer.outputColorSpace = T.SRGBColorSpace;
    this.renderer.toneMapping = T.ACESFilmicToneMapping;
    this.renderer.toneMappingExposure = 1.2;
    this.renderer.domElement.setAttribute(
      "aria-label",
      "FR3 로봇팔과 볼트 그리퍼 3D 장면",
    );
    this.renderer.domElement.setAttribute("role", "img");
    host.prepend(this.renderer.domElement);
    this.camera.up.set(0, 0, 1);
    this.detailCamera.up.set(0, 0, 1);
    this.controls = new OrbitControls(this.camera, this.renderer.domElement);
    this.controls.enableDamping = true;
    this.controls.dampingFactor = 0.09;
    this.controls.minDistance = 0.1;
    this.controls.maxDistance = 3.7;
    this.controls.maxPolarAngle = Math.PI * 0.92;
    this.scene.add(new T.HemisphereLight("#ffffff", "#859cab", 2.7));
    const key = new T.DirectionalLight("#fff5e2", 3.4);
    key.position.set(-0.6, -1, 2);
    key.castShadow = true;
    key.shadow.mapSize.set(2048, 2048);
    key.shadow.camera.left = -1;
    key.shadow.camera.right = 1.4;
    key.shadow.camera.top = 1.2;
    key.shadow.camera.bottom = -1.2;
    key.shadow.bias = -0.0003;
    key.shadow.normalBias = 0.002;
    this.scene.add(key);
    const fill = new T.DirectionalLight("#e4f1ff", 1.3);
    fill.position.set(1.4, 1.2, 1.4);
    this.scene.add(fill);
    this.scene.add(makeCell());
    this.scene.add(this.bolt);
    const grid = new T.GridHelper(3, 60, "#b8c8d0", "#d4dee3");
    grid.rotation.x = Math.PI / 2;
    grid.position.z = -0.075;
    this.scene.add(grid);
    for (const anchor of this.gripper.labelAnchors) {
      const el = document.createElement("span");
      el.className = "part-label";
      el.textContent = anchor.name;
      el.style.setProperty("--part-color", anchor.color);
      host.append(el);
      this.labelNodes.push(el);
    }
    this.resizeObserver = new ResizeObserver(() => this.resize());
    this.resizeObserver.observe(host);
    this.resize();
    this.setView("whole");
    this.renderer.domElement.addEventListener("webglcontextlost", (event) => {
      event.preventDefault();
      host.dispatchEvent(
        new CustomEvent("viewer-error", {
          detail: "3D 화면 연결이 중단되었습니다. 페이지를 다시 불러오세요.",
        }),
      );
    });
  }
  async load(onProgress: (n: number) => void) {
    const [robot] = await Promise.all([
      loadRobot(onProgress),
      this.gripper.load(),
    ]);
    this.robot = robot;
    this.scene.add(this.robot.root);
    this.robot.flange.add(this.gripper.root);
    this.initialized = true;
    this.update(0);
  }
  private resize() {
    this.width = Math.max(1, this.host.clientWidth);
    this.height = Math.max(1, this.host.clientHeight);
    this.renderer.setSize(this.width, this.height);
    this.camera.aspect = this.width / this.height;
    this.camera.updateProjectionMatrix();
  }
  setSpec(spec: BoltSpec) {
    this.spec = spec;
    this.scene.remove(this.bolt);
    disposeObject(this.bolt);
    this.bolt = makeBolt(spec, true);
    this.scene.add(this.bolt);
    this.update(0);
  }
  setOptions(o: {
    transparent?: boolean;
    exploded?: boolean;
    labels?: boolean;
    inset?: boolean;
  }) {
    if (o.transparent !== undefined) this.transparent = o.transparent;
    if (o.exploded !== undefined) this.exploded = o.exploded;
    if (o.labels !== undefined) this.labels = o.labels;
    if (o.inset !== undefined) this.inset = o.inset;
    this.update(this.state.time);
  }
  setView(name: ViewName) {
    this.view = name;
    if (this.initialized) {
      this.robot.flange.updateWorldMatrix(true, false);
      this.focused.set(0, 0, 0.115).applyMatrix4(this.robot.flange.matrixWorld);
    } else this.focused.set(0.45, -0.2, 0.32);
    if (name === "detail") {
      this.camera.position
        .copy(this.focused)
        .add(new T.Vector3(-0.28, 0.37, 0.015));
      this.controls.target.copy(this.focused);
    } else {
      const target = new T.Vector3(0.3, 0, 0.28);
      const offset =
        name === "front"
          ? new T.Vector3(0, -1.95, 0.1)
          : name === "side"
            ? new T.Vector3(1.95, 0, 0.1)
            : new T.Vector3(1.25, -1.55, 1.05);
      this.camera.position.copy(target).add(offset);
      this.controls.target.copy(target);
    }
    this.lastFocus.copy(this.focused);
    this.controls.update();
  }
  nudgeCamera(direction: number) {
    const offset = this.camera.position.clone().sub(this.controls.target);
    offset.applyAxisAngle(new T.Vector3(0, 0, 1), direction * 0.18);
    this.camera.position.copy(this.controls.target).add(offset);
    this.controls.update();
  }
  zoom(factor: number) {
    const offset = this.camera.position
      .clone()
      .sub(this.controls.target)
      .multiplyScalar(factor);
    offset.clampLength(0.1, 3.7);
    this.camera.position.copy(this.controls.target).add(offset);
    this.controls.update();
  }
  update(time: number) {
    this.state = sampleCycle(time);
    if (!this.initialized) return;
    jointsAt(time, this.spec.id).forEach(
      (q, i) => (this.robot.joints[i].rotation.z = q),
    );
    this.robot.root.updateMatrixWorld(true);
    this.gripper.update(this.state, this.spec, this.transparent, this.exploded);
    this.bolt.matrixAutoUpdate = false;
    this.bolt.matrix.copy(boltWorldAt(time, this.spec));
    this.bolt.matrixWorldNeedsUpdate = true;
    this.focused.set(0, 0, 0.115).applyMatrix4(this.robot.flange.matrixWorld);
    if (this.view === "detail") {
      const delta = this.focused.clone().sub(this.lastFocus);
      this.camera.position.add(delta);
      this.controls.target.add(delta);
    }
    this.lastFocus.copy(this.focused);
  }
  render() {
    this.controls.update();
    this.renderer.setScissorTest(false);
    this.renderer.setViewport(0, 0, this.width, this.height);
    this.renderer.render(this.scene, this.camera);
    const showInset =
      this.initialized &&
      this.inset &&
      this.view !== "detail" &&
      this.width > 670;
    this.insetLabel.hidden = !showInset;
    if (showInset) {
      const w = Math.min(340, this.width * 0.32),
        h = w * 0.82,
        x = this.width - w - 18,
        y = this.height - h - 66;
      this.detailCamera.position
        .copy(this.focused)
        .add(new T.Vector3(-0.23, 0.29, 0.015));
      this.detailCamera.lookAt(this.focused);
      this.detailCamera.aspect = w / h;
      this.detailCamera.updateProjectionMatrix();
      this.renderer.setScissorTest(true);
      this.renderer.setScissor(x, y, w, h);
      this.renderer.setViewport(x, y, w, h);
      this.renderer.clearDepth();
      this.renderer.render(this.scene, this.detailCamera);
      this.renderer.setScissorTest(false);
      this.insetLabel.style.width = `${w}px`;
      this.insetLabel.style.height = `${h}px`;
    }
    this.gripper.labelAnchors.forEach((a, i) => {
      const el = this.labelNodes[i];
      el.hidden = !(this.initialized && this.labels && this.view === "detail");
      if (el.hidden) return;
      const v = this.gripper.root
        .localToWorld(a.position.clone())
        .project(this.camera);
      const x = (v.x * 0.5 + 0.5) * this.width + (i === 2 ? 70 : -175);
      const y = (-v.y * 0.5 + 0.5) * this.height + [-50, -25, 40][i];
      el.style.left = `${Math.max(8, Math.min(this.width - el.offsetWidth - 8, x))}px`;
      el.style.top = `${Math.max(80, Math.min(this.height - 65, y))}px`;
      el.style.opacity = v.z < 1 ? "1" : "0";
    });
  }
  dispose() {
    this.resizeObserver.disconnect();
    this.controls.dispose();
    disposeObject(this.scene);
    this.renderer.dispose();
  }
}
