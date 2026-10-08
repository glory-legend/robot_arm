import * as T from "three";
import { ColladaLoader } from "three/addons/loaders/ColladaLoader.js";
import {
  rodPose,
  mainFingerPose,
  TIP_INSET,
  HEAD_OPEN_RADIUS,
  HEAD_CLOCKING,
  THUMB_LENGTHS,
  THUMB_BASE,
  ROLLER_RADIUS,
  GRASP_POINT,
  GRASP_DISTANCE,
  HEAD_EXTENSION,
} from "./rod-kinematics";
import type { BoltSpec, CycleState } from "./timeline";
import { palette } from "./theme";
const material = (
  color: T.ColorRepresentation,
  roughness = 0.4,
  metalness = 0.45,
) => new T.MeshStandardMaterial({ color, roughness, metalness });
function part(
  parent: T.Object3D,
  geo: T.BufferGeometry,
  mat: T.Material,
  pos: number[] = [0, 0, 0],
) {
  const o = new T.Mesh(geo, mat);
  o.position.set(...(pos as [number, number, number]));
  o.castShadow = true;
  o.receiveShadow = true;
  parent.add(o);
  return o;
}
function ellipsoid(
  parent: T.Object3D,
  size: number[],
  pos: number[],
  mat: T.Material,
) {
  const o = part(parent, new T.SphereGeometry(1, 32, 20), mat, pos);
  o.scale.set(...(size as [number, number, number]));
  return o;
}
function shell(length: number, r: number) {
  const profile = [
    [0, length * 0.03],
    [r * 0.55, length * 0.06],
    [r * 0.85, length * 0.14],
    [r, length * 0.25],
    [r * 0.92, length * 0.52],
    [r * 0.7, length * 0.8],
    [r * 0.45, length * 0.94],
    [0, length * 0.98],
  ].map(([x, y]) => new T.Vector2(x, y));
  const g = new T.LatheGeometry(profile, 32);
  g.rotateX(Math.PI / 2);
  return g;
}
export function makeGripper() {
  const colors = palette(),
    root = new T.Group();
  root.name = "robotiq-2f85-with-custom-bolt-tips-and-thumb";
  const ivory = material("#d5dcd9", 0.36, 0.25),
    dark = material("#27383e", 0.52, 0.28),
    silver = material("#a8b9bf", 0.29, 0.7),
    blue = material("#397f8b", 0.48, 0.3),
    rubber = material("#2b5360", 0.85, 0.02),
    copper = material(colors.orange, 0.3, 0.65);
  const translucent: T.MeshStandardMaterial[] = [];
  const stock = new T.Group();
  root.add(stock);
  const assets: { parent: T.Object3D; file: string }[] = [
    { parent: stock, file: "robotiq_base" },
  ];
  // An external bracket supports the custom thumb; the commercial body stays intact.
  part(root, new T.BoxGeometry(0.018, 0.006, 0.055), silver, [0, 0.032, 0.072]);
  function joint(parent: T.Group, r: number, axis: "x" | "y") {
    const axle = part(parent, new T.CylinderGeometry(r, r, r * 1.45, 32), dark);
    if (axis === "x") axle.rotation.z = Math.PI / 2;
    for (const side of [-1, 1]) {
      const pos =
        axis === "x" ? [side * r * 0.78, 0, 0] : [0, side * r * 0.78, 0];
      const cap = part(
        parent,
        new T.CylinderGeometry(r * 0.68, r * 0.68, 0.0015, 32),
        silver,
        pos,
      );
      if (axis === "x") cap.rotation.z = Math.PI / 2;
      const bolt = part(
        parent,
        new T.CylinderGeometry(r * 0.22, r * 0.22, 0.0018, 6),
        dark,
        pos.map((v) => v * 1.13),
      );
      if (axis === "x") bolt.rotation.z = Math.PI / 2;
    }
  }
  function phalanx(
    parent: T.Group,
    len: number,
    width: number,
    axis: "z" | "y",
    accent = false,
  ) {
    const bone = new T.Group();
    if (axis === "y") bone.rotation.x = -Math.PI / 2;
    parent.add(bone);
    const cover = ivory.clone();
    translucent.push(cover);
    const body = part(bone, shell(len, width / 2), accent ? blue : cover);
    body.scale.y = 0.72;
    // A soft ventral pad and a slim exposed tendon make each segment read as a finger.
    ellipsoid(
      bone,
      [width * 0.28, width * 0.17, Math.max(0.004, len * 0.3)],
      [0, width * 0.33, len * 0.52],
      rubber,
    );
    const tendon = part(
      bone,
      new T.CylinderGeometry(0.0012, 0.0012, len * 0.52, 12),
      silver,
      [0, -width * 0.34, len * 0.52],
    );
    tendon.rotation.x = Math.PI / 2;
  }
  const mains: {
    side: number;
    base: T.Group;
    inner: T.Group;
    tip: T.Group;
    stem: T.Mesh;
    toe: T.Group;
  }[] = [];
  for (const side of [-1, 1]) {
    const name = side > 0 ? "left" : "right";
    const base = new T.Group();
    base.name = `2f85-${name}-knuckle`;
    stock.add(base);
    assets.push({ parent: base, file: `${name}_knuckle` });
    const finger = new T.Group();
    finger.position.set(side * 0.03152616, 0, -0.00376347);
    base.add(finger);
    assets.push({ parent: finger, file: `${name}_finger` });
    const inner = new T.Group();
    inner.position.set(side * 0.0127, 0, 0.06142);
    stock.add(inner);
    assets.push({ parent: inner, file: `${name}_inner_knuckle` });
    const tip = new T.Group();
    tip.position.set(side * 0.00563134, 0, 0.04718515);
    finger.add(tip);
    // Thin, rigid fingers keep the bulky linkages above the pile.
    joint(tip, 0.006, "y");
    const stem = part(tip, new T.BoxGeometry(0.005, 0.006, 1), silver);
    const toe = new T.Group();
    tip.add(toe);
    part(toe, new T.BoxGeometry(TIP_INSET, 0.006, 0.005), blue, [
      (-side * TIP_INSET) / 2,
      0,
      -0.002,
    ]);
    ellipsoid(toe, [0.003, 0.004, 0.004], [-side * TIP_INSET, 0, 0], rubber);
    mains.push({ side, base, inner, tip, stem, toe });
  }
  // A slim, two-knuckle auxiliary thumb. It nudges the bolt end, not the main jaws.
  const thumb = new T.Group();
  thumb.name = "two-joint-auxiliary-thumb";
  thumb.position.copy(THUMB_BASE);
  root.add(thumb);
  const proximal = new T.Group();
  thumb.add(proximal);
  joint(proximal, 0.008, "x");
  phalanx(proximal, THUMB_LENGTHS[0], 0.012, "y");
  const distal = new T.Group();
  distal.position.y = THUMB_LENGTHS[0];
  proximal.add(distal);
  joint(distal, 0.006, "x");
  phalanx(distal, THUMB_LENGTHS[1], 0.009, "y", true);
  part(distal, new T.SphereGeometry(ROLLER_RADIUS, 20, 14), rubber, [
    0,
    THUMB_LENGTHS[1],
    0,
  ]);
  // Existing fastening concept remains a compact palm-mounted head holder; no funnel.
  const carriage = new T.Group();
  root.add(carriage);
  const rotor = new T.Group();
  carriage.add(rotor);
  const headZ = GRASP_POINT.z - GRASP_DISTANCE;
  const hub = part(
    rotor,
    new T.CylinderGeometry(0.011, 0.011, 0.014, 40),
    dark,
    [0, 0, headZ - 0.018],
  );
  hub.rotation.x = Math.PI / 2;
  part(rotor, new T.TorusGeometry(0.0105, 0.001, 8, 40), silver, [
    0,
    0,
    headZ - 0.011,
  ]);
  const jaws: { jaw: T.Group; bridge: T.Mesh }[] = [];
  for (let i = 0; i < 3; i++) {
    const rail = new T.Group();
    rail.rotation.z = (i * Math.PI * 2) / 3;
    rotor.add(rail);
    const jaw = new T.Group();
    rail.add(jaw);
    const bridge = part(rail, new T.BoxGeometry(1, 0.004, 0.002), silver, [
      0,
      0,
      headZ - 0.013,
    ]);
    jaws.push({ jaw, bridge });
    part(jaw, new T.BoxGeometry(0.003, 0.004, 0.014), copper, [
      0.0015,
      0,
      headZ - 0.007,
    ]);
  }
  const driver = part(
    root,
    new T.CylinderGeometry(0.004, 0.004, 0.084, 32),
    silver,
    [0, 0, 0.088],
  );
  driver.rotation.x = Math.PI / 2;
  const labelAnchors = [
    {
      name: "2F-85 · 슬림 손끝",
      position: new T.Vector3(-0.04, 0, 0.1),
      color: colors.blue,
    },
    {
      name: "보조 엄지 · 2관절",
      position: new T.Vector3(0, 0.06, 0.1),
      color: "#397f8b",
    },
    {
      name: "추가 헤드 척",
      position: new T.Vector3(0, 0, 0.116),
      color: colors.orange,
    },
  ];
  async function load() {
    const loader = new ColladaLoader();
    await Promise.all(
      assets.map(async ({ parent, file }) => {
        const data = await loader.loadAsync(
          `./robotiq-2f85/meshes/${file}.dae`,
        );
        if (!data) throw new Error(`2F-85 모델을 읽지 못했습니다: ${file}`);
        const scene = data.scene;
        // URDF mesh coordinates already use Z-up. Cancel ColladaLoader's scene conversion.
        scene.rotation.set(0, 0, 0);
        scene.traverse((o) => {
          if (!(o instanceof T.Mesh)) return;
          const mat = file === "robotiq_base" ? dark.clone() : silver.clone();
          o.material = mat;
          o.castShadow = o.receiveShadow = true;
          if (file === "robotiq_base") translucent.push(mat);
        });
        parent.add(scene);
      }),
    );
  }
  function update(
    s: CycleState,
    spec: BoltSpec,
    transparent: boolean,
    exploded: boolean,
  ) {
    for (const m of translucent) {
      m.transparent = transparent;
      m.opacity = transparent ? 0.2 : 1;
      m.depthWrite = !transparent;
    }
    for (const f of mains) {
      const p = mainFingerPose(f.side, s, spec);
      f.base.position.copy(p.root);
      if (exploded) f.base.position.x += f.side * 0.035;
      f.base.rotation.y = -f.side * p.angles[0];
      f.inner.rotation.y = -f.side * p.angles[0];
      f.inner.position.x = f.side * (0.0127 + (exploded ? 0.035 : 0));
      f.tip.rotation.y = f.side * p.angles[0];
      f.stem.scale.z = p.tipLength - 0.002;
      f.stem.position.z = (p.tipLength - 0.002) / 2;
      f.toe.position.z = p.tipLength;
    }
    const p = rodPose(s, spec);
    proximal.rotation.x = p.angles[0];
    distal.rotation.x = p.angles[1];
    thumb.position.y = THUMB_BASE.y + (exploded ? 0.035 : 0);
    carriage.position.z = HEAD_EXTENSION * s.clear + (exploded ? 0.035 : 0);
    // Clock the three chuck jaws between the two narrow finger stems.
    rotor.rotation.z = s.spindle + HEAD_CLOCKING;
    driver.scale.y = (0.084 + HEAD_EXTENSION * s.clear) / 0.084;
    driver.position.z = 0.088 + (HEAD_EXTENSION * s.clear) / 2;
    for (const { jaw, bridge } of jaws) {
      jaw.position.x =
        spec.headWidth / 2 +
        (HEAD_OPEN_RADIUS - spec.headWidth / 2) * (1 - s.chuckClosed);
      bridge.scale.x = jaw.position.x + 0.003 - 0.005;
      bridge.position.x = 0.005 + bridge.scale.x / 2;
    }
    labelAnchors[0].position.copy(mainFingerPose(-1, s, spec).points[2]);
    labelAnchors[1].position
      .copy(p.elbow)
      .add(new T.Vector3(0, exploded ? 0.035 : 0, 0));
    labelAnchors[2].position.set(0, 0, headZ + carriage.position.z);
  }
  return { root, load, update, labelAnchors };
}
