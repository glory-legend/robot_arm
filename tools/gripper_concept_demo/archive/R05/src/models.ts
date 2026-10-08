import * as T from "three";
import { ColladaLoader } from "three/addons/loaders/ColladaLoader.js";
import { ROBOT_DATA, originMatrix } from "./kinematics";
import { PRESETS, type BoltSpec } from "./timeline";
export { makeGripper } from "./gripper";

const metal = (
  color: T.ColorRepresentation,
  roughness = 0.4,
  metalness = 0.45,
) => new T.MeshStandardMaterial({ color, roughness, metalness });
function mesh(
  g: T.BufferGeometry,
  m: T.Material,
  parent: T.Object3D,
  pos: number[] = [0, 0, 0],
) {
  const o = new T.Mesh(g, m);
  o.position.set(pos[0], pos[1], pos[2]);
  o.castShadow = true;
  o.receiveShadow = true;
  parent.add(o);
  return o;
}
function box(parent: T.Object3D, size: number[], pos: number[], m: T.Material) {
  return mesh(
    new T.BoxGeometry(...(size as [number, number, number])),
    m,
    parent,
    pos,
  );
}
function cylinder(
  parent: T.Object3D,
  r: number,
  len: number,
  pos: number[],
  m: T.Material,
  segments = 32,
) {
  const o = mesh(new T.CylinderGeometry(r, r, len, segments), m, parent, pos);
  o.rotation.x = Math.PI / 2;
  return o;
}
function ring(
  parent: T.Object3D,
  outer: number,
  inner: number,
  length: number,
  pos: number[],
  m: T.Material,
) {
  const shape = new T.Shape();
  shape.absarc(0, 0, outer, 0, Math.PI * 2, false);
  const hole = new T.Path();
  hole.absarc(0, 0, inner, 0, Math.PI * 2, true);
  shape.holes.push(hole);
  return mesh(
    new T.ExtrudeGeometry(shape, {
      depth: length,
      bevelEnabled: false,
      curveSegments: 32,
    }),
    m,
    parent,
    [pos[0], pos[1], pos[2] - length / 2],
  );
}
export function makeBolt(spec: BoltSpec, highlight = false) {
  const g = new T.Group();
  g.name = "bolt";
  const m = metal(highlight ? "#d6ad62" : "#8a969e", 0.32, 0.72);
  const head = cylinder(
    g,
    spec.headWidth / Math.sqrt(3),
    spec.headHeight,
    [0, 0, -spec.headHeight / 2],
    m,
    6,
  );
  // Hex flats face six radial jaws at 60 degree intervals.
  head.rotation.y = 0;
  cylinder(g, spec.diameter / 2, spec.length, [0, 0, spec.length / 2], m, 20);
  // A low-cost helical line conveys threads; this is not a manufacturing thread profile.
  const pts: T.Vector3[] = [];
  const turns = spec.length / spec.pitch;
  for (let i = 0; i <= Math.ceil(turns * 20); i++) {
    const f = i / Math.ceil(turns * 20),
      a = f * turns * Math.PI * 2;
    pts.push(
      new T.Vector3(
        Math.cos(a) * (spec.diameter / 2 + 0.00008),
        Math.sin(a) * (spec.diameter / 2 + 0.00008),
        f * spec.length,
      ),
    );
  }
  const line = new T.Line(
    new T.BufferGeometry().setFromPoints(pts),
    new T.LineBasicMaterial({ color: highlight ? "#856537" : "#56626c" }),
  );
  g.add(line);
  return g;
}
export async function loadRobot(onProgress: (n: number) => void) {
  const root = new T.Group();
  root.name = "FR3";
  let parent = root;
  const joints: T.Group[] = [];
  const slots: T.Group[] = [root];
  for (let i = 0; i < 7; i++) {
    const origin = new T.Group();
    origin.applyMatrix4(originMatrix(ROBOT_DATA[i]));
    parent.add(origin);
    const joint = new T.Group();
    origin.add(joint);
    joints.push(joint);
    slots.push(joint);
    parent = joint;
  }
  const flange = new T.Group();
  flange.applyMatrix4(originMatrix(ROBOT_DATA[7]));
  parent.add(flange);
  const loader = new ColladaLoader();
  let done = 0;
  await Promise.all(
    slots.map(async (slot, i) => {
      const asset = await loader.loadAsync(
        `${import.meta.env.BASE_URL}fr3/link${i}.dae`,
      );
      if (!asset) throw new Error(`FR3 link${i} could not be parsed`);
      // ColladaLoader rotates Z_UP into Y_UP. Our robot/world intentionally use Z_UP.
      asset.scene.rotation.set(0, 0, i === 7 ? Math.PI / 4 : 0);
      asset.scene.traverse((o) => {
        if (o instanceof T.Mesh) {
          o.castShadow = true;
          o.receiveShadow = true;
          const mats = Array.isArray(o.material) ? o.material : [o.material];
          for (const mat of mats) {
            if ("color" in mat) {
              const original = (mat as T.MeshPhongMaterial).color;
              const isDark = original.getHSL({ h: 0, s: 0, l: 0 }).l < 0.25;
              o.material = metal(isDark ? "#28313b" : "#e7eaec", 0.4, 0.22);
            }
          }
        }
      });
      slot.add(asset.scene);
      onProgress(++done);
    }),
  );
  return { root, joints, flange };
}
export function makeCell(spec: BoltSpec = PRESETS[1]) {
  const root = new T.Group();
  const steel = metal("#aebec7", 0.7, 0.2),
    edge = metal("#647a87", 0.55, 0.3),
    dark = metal("#364d58");
  const top = new T.Shape();
  top.moveTo(-0.375, -0.6);
  top.lineTo(0.975, -0.6);
  top.lineTo(0.975, 0.6);
  top.lineTo(-0.375, 0.6);
  top.closePath();
  const relief = new T.Path();
  relief.absarc(0.46, 0.23, 0.012, 0, Math.PI * 2, true);
  top.holes.push(relief);
  mesh(
    new T.ExtrudeGeometry(top, { depth: 0.055, bevelEnabled: false }),
    metal("#cbd5da", 0.88, 0.06),
    root,
    [0, 0, -0.0725],
  );
  box(root, [0.23, 0.23, 0.02], [0, 0, -0.006], dark);
  for (const x of [-0.085, 0.085])
    for (const y of [-0.085, 0.085])
      cylinder(root, 0.006, 0.005, [x, y, 0.006], edge, 8);
  const bin = new T.Group();
  bin.position.set(0.48, -0.22, 0);
  root.add(bin);
  box(bin, [0.3, 0.27, 0.014], [0, 0, 0.011], steel);
  for (const y of [-0.135, 0.135])
    box(bin, [0.31, 0.012, 0.068], [0, y, 0.047], edge);
  for (const x of [-0.155, 0.155])
    box(bin, [0.012, 0.27, 0.068], [x, 0, 0.047], edge);
  let seed = 17;
  const rand = () => {
    seed = (seed * 1664525 + 1013904223) >>> 0;
    return seed / 4294967296;
  };
  for (let i = 0; i < 58; i++) {
    const spec = PRESETS[i % 3];
    const bolt = makeBolt(spec);
    const x = (rand() - 0.5) * 0.24,
      y = (rand() - 0.5) * 0.21;
    // Keep a small access corridor around the featured bolt.
    if (Math.abs(x) < 0.045 && Math.abs(y) < 0.042) continue;
    const pileHeight = 0.019 * Math.exp(-(x * x + y * y) / 0.008);
    bolt.position.set(x, y, 0.027 + pileHeight + rand() * 0.014);
    bolt.rotation.set(
      Math.PI / 2 + (rand() - 0.5) * 0.5,
      rand() * 0.35,
      rand() * Math.PI * 2,
    );
    bin.add(bolt);
  }
  const plate = new T.Group();
  plate.position.set(0.46, 0.23, 0);
  root.add(plate);
  const plateShape = new T.Shape();
  plateShape.moveTo(-0.12, -0.1);
  plateShape.lineTo(0.12, -0.1);
  plateShape.lineTo(0.12, 0.1);
  plateShape.lineTo(-0.12, 0.1);
  plateShape.closePath();
  const hole = new T.Path();
  hole.absarc(0, 0, spec.diameter / 2 + 0.00015, 0, Math.PI * 2, true);
  plateShape.holes.push(hole);
  mesh(
    new T.ExtrudeGeometry(plateShape, { depth: 0.026, bevelEnabled: false }),
    steel,
    plate,
  );
  ring(plate, 0.01, spec.diameter / 2 + 0.00015, 0.004, [0, 0, 0.024], dark);
  for (const x of [-0.09, 0.09])
    for (const y of [-0.07, 0.07])
      cylinder(plate, 0.006, 0.004, [x, y, 0.028], edge, 6);
  // Paired stationary keyways take the stator torque while allowing axial feed.
  for (const x of [-0.042, 0.042]) {
    box(plate, [0.024, 0.036, 0.01], [x, 0, 0.031], dark);
    for (const y of [-0.01, 0.01])
      box(plate, [0.016, 0.008, 0.15], [x, y, 0.111], edge);
    box(plate, [0.004, 0.028, 0.15], [x + Math.sign(x) * 0.01, 0, 0.111], dark);
    for (const y of [-0.015, 0.015])
      cylinder(plate, 0.002, 0.003, [x, y, 0.038], dark, 6);
  }
  return root;
}
export function disposeObject(root: T.Object3D) {
  root.traverse((o) => {
    if (o instanceof T.Mesh || o instanceof T.Line) {
      o.geometry.dispose();
      for (const m of Array.isArray(o.material) ? o.material : [o.material])
        m.dispose();
    }
  });
}
