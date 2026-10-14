import * as T from "three";
import { RoundedBoxGeometry } from "three/addons/geometries/RoundedBoxGeometry.js";
import {
  rodPose,
  mainFingerPose,
  HEAD_OPEN_RADIUS,
  HEAD_CLOCKING,
  THUMB_LENGTHS,
  THUMB_BASE,
  ROLLER_RADIUS,
  GRASP_POINT,
  GRASP_DISTANCE,
  HEAD_STROKE,
  RETRACT,
} from "./rod-kinematics";
import type { BoltSpec, CycleState } from "./timeline";
import { palette } from "./theme";
const mat = (color: string, metalness = 0.55) =>
  new T.MeshStandardMaterial({ color, roughness: 0.36, metalness });
function part(
  parent: T.Object3D,
  geometry: T.BufferGeometry,
  material: T.Material,
  xyz = [0, 0, 0],
) {
  const m = new T.Mesh(geometry, material);
  m.position.set(...(xyz as [number, number, number]));
  m.castShadow = m.receiveShadow = true;
  parent.add(m);
  return m;
}
function box(p: T.Object3D, s: number[], xyz: number[], m: T.Material) {
  return part(
    p,
    new RoundedBoxGeometry(s[0], s[1], s[2], 2, Math.min(...s, 0.006) * 0.2),
    m,
    xyz,
  );
}
function cyl(
  p: T.Object3D,
  r: number,
  l: number,
  xyz: number[],
  m: T.Material,
  n = 40,
) {
  const o = part(p, new T.CylinderGeometry(r, r, l, n), m, xyz);
  o.rotation.x = Math.PI / 2;
  return o;
}
function ring(
  p: T.Object3D,
  outer: number,
  inner: number,
  l: number,
  z: number,
  m: T.Material,
) {
  const s = new T.Shape();
  s.absarc(0, 0, outer, 0, Math.PI * 2, false);
  const h = new T.Path();
  h.absarc(0, 0, inner, 0, Math.PI * 2, true);
  s.holes.push(h);
  return part(
    p,
    new T.ExtrudeGeometry(s, {
      depth: l,
      bevelEnabled: false,
      curveSegments: 40,
    }),
    m,
    [0, 0, z - l / 2],
  );
}
function beam(
  p: T.Object3D,
  a: T.Vector3,
  b: T.Vector3,
  r: number,
  m: T.Material,
) {
  const o = part(p, new T.CylinderGeometry(r, r, a.distanceTo(b), 16), m);
  o.position.copy(a).add(b).multiplyScalar(0.5);
  o.quaternion.setFromUnitVectors(
    new T.Vector3(0, 1, 0),
    b.clone().sub(a).normalize(),
  );
  return o;
}
// Straight, rigid taper: 8 × 8 mm root, 3 × 4 mm tip. No size-specific mesh.
function taperedFinger() {
  const vertices: number[] = [];
  const root = new T.Vector3(0, 0.042, -0.04),
    tip = new T.Vector3();
  const v = new T.Vector3(0, 0.04, 0.042).normalize();
  for (const [center, w, d] of [
    [root, 0.008, 0.008],
    [tip, 0.003, 0.004],
  ] as const)
    for (const [x, y] of [
      [-1, -1],
      [1, -1],
      [1, 1],
      [-1, 1],
    ])
      vertices.push(
        ...center
          .clone()
          .add(new T.Vector3((x * w) / 2, 0, 0))
          .addScaledVector(v, (y * d) / 2)
          .toArray(),
      );
  const g = new T.BufferGeometry();
  g.setAttribute("position", new T.Float32BufferAttribute(vertices, 3));
  g.setIndex([
    0, 2, 1, 0, 3, 2, 4, 5, 6, 4, 6, 7, 0, 1, 5, 0, 5, 4, 1, 2, 6, 1, 6, 5, 2,
    3, 7, 2, 7, 6, 3, 0, 4, 3, 4, 7,
  ]);
  g.computeVertexNormals();
  return g;
}
export function makeGripper() {
  const root = new T.Group();
  root.name = "tapered-parallel-gripper-with-adaptive-six-jaw-head";
  const colors = palette(),
    dark = mat("#293b43"),
    silver = mat("#b5c3cb", 0.8),
    blue = mat("#3c8192"),
    rubber = mat("#263e44", 0.05),
    copper = mat(colors.orange, 0.75),
    ivory = mat("#d9e1e2", 0.25);
  const translucent: T.MeshStandardMaterial[] = [];
  const cover = () => {
    const m = ivory.clone();
    translucent.push(m);
    return m;
  };
  const headZ = GRASP_POINT.z - GRASP_DISTANCE;
  // Full 322 × Ø57 mm installation envelope of the selected 1.8 kg spindle.
  cyl(root, 0.032, 0.012, [0, 0, 0.006], dark);
  cyl(root, 0.0285, 0.322, [0, 0, 0.173], cover());
  for (const z of [0.03, 0.205, 0.309])
    ring(root, 0.0295, 0.028, 0.01, z, dark);
  for (let i = 0; i < 6; i++) {
    const a = (i * Math.PI) / 3;
    cyl(
      root,
      0.002,
      0.004,
      [0.023 * Math.cos(a), 0.023 * Math.sin(a), 0.014],
      silver,
      6,
    );
  }
  // Longitudinal cooling grooves and cable connector; fixed housing never rotates.
  for (const a of [0, Math.PI / 2, Math.PI, Math.PI * 1.5]) {
    const rib = box(
      root,
      [0.003, 0.004, 0.16],
      [0.028 * Math.cos(a), 0.028 * Math.sin(a), 0.14],
      dark,
    );
    rib.rotation.z = a - Math.PI / 2;
  }
  box(root, [0.019, 0.014, 0.025], [0, -0.033, 0.037], dark);
  beam(
    root,
    new T.Vector3(0, -0.034, 0.03),
    new T.Vector3(0, -0.034, 0.005),
    0.002,
    rubber,
  );
  // A rigid splined quill, supported by bearings, permits the short capture stroke.
  const shaft = cyl(root, 0.006, 0.054, [0, 0, 0.347], silver);
  shaft.name = "rigid-output-spline";
  for (const z of [0.323, 0.335]) ring(root, 0.011, 0.0063, 0.006, z, dark);
  const carriage = new T.Group();
  root.add(carriage);
  for (const x of [-0.026, 0.026]) {
    cyl(root, 0.0025, 0.045, [x, 0, 0.343], silver);
    box(carriage, [0.012, 0.016, 0.012], [x, 0, headZ - 0.038], dark);
  }
  const rotor = new T.Group();
  carriage.add(rotor);
  cyl(rotor, 0.0232, 0.008, [0, 0, headZ - 0.027], dark);
  ring(rotor, 0.0232, 0.0208, 0.011, headZ - 0.018, cover());
  ring(rotor, 0.0235, 0.0208, 0.003, headZ - 0.014, blue);
  const cam = new T.Group();
  rotor.add(cam);
  const camProfile = [
    [0.0205, -0.025],
    [0.0205, -0.0175],
    [0.01, -0.0175],
    [0.018, -0.025],
    [0.0205, -0.025],
  ].map(([r, z]) => new T.Vector2(r, z));
  const wedge = part(cam, new T.LatheGeometry(camProfile, 48), silver, [
    0,
    0,
    headZ,
  ]);
  wedge.rotation.x = Math.PI / 2;
  // Retaining pawl/ratchet is a layout placeholder, not a rated safety lock.
  box(cam, [0.003, 0.005, 0.007], [0.02, 0, headZ - 0.021], blue);
  const jaws: T.Group[] = [];
  for (let i = 0; i < 6; i++) {
    const rail = new T.Group();
    rail.rotation.z = (i * Math.PI) / 3;
    rotor.add(rail);
    box(rail, [0.01, 0.006, 0.003], [0.014, 0, headZ - 0.0145], dark);
    for (const side of [-1, 1])
      box(
        rail,
        [0.01, 0.001, 0.007],
        [0.014, side * 0.0024, headZ - 0.0115],
        dark,
      );
    const jaw = new T.Group();
    rail.add(jaw);
    jaws.push(jaw);
    // Radial steel slides are rigid. Narrow flats engage all six hex faces.
    box(jaw, [0.008, 0.0032, 0.003], [0.004, 0, headZ - 0.009], silver);
    box(jaw, [0.003, 0.0032, 0.0084], [0.0015, 0, headZ - 0.0048], copper);
    // Cam follower and self-lock latch schematic, carried with the rotor.
    cyl(jaw, 0.0012, 0.004, [0.006, 0, headZ - 0.012], silver, 16);
  }
  ring(carriage, 0.026, 0.0235, 0.006, headZ - 0.025, dark); // thrust bearing outer race
  const closer = box(
    carriage,
    [0.014, 0.014, 0.03],
    [0, -0.033, headZ - 0.036],
    dark,
  );
  beam(
    carriage,
    new T.Vector3(0, -0.029, headZ - 0.031),
    new T.Vector3(0, -0.023, headZ - 0.025),
    0.002,
    silver,
  );
  closer.name = "head-cam-actuator-envelope";
  // Torque reaction tabs remain on the stator and slide through a fixture keyway.
  for (const side of [-1, 1])
    box(
      root,
      [0.023, 0.01, 0.01],
      [side * 0.034, 0, GRASP_POINT.z - 0.09],
      blue,
    );
  // Entire shaft-gripping module withdraws diagonally after the chuck is locked.
  const module = new T.Group();
  root.add(module);
  box(
    module,
    [0.044, 0.022, 0.069],
    [0, 0.042, GRASP_POINT.z - 0.0905],
    cover(),
  );
  box(module, [0.044, 0.024, 0.009], [0, 0.042, GRASP_POINT.z - 0.059], dark);
  box(module, [0.026, 0.001, 0.023], [0, 0.0535, GRASP_POINT.z - 0.086], blue);
  for (const x of [-0.016, 0.016])
    for (const z of [GRASP_POINT.z - 0.113, GRASP_POINT.z - 0.066])
      cyl(module, 0.0017, 0.002, [x, 0.054, z], silver, 6).rotation.x = 0;
  // Two proximal tendon motor envelopes, intentionally visible rather than hidden in fingers.
  for (const side of [-1, 1]) {
    box(
      module,
      [0.02, 0.026, 0.034],
      [side * 0.012, 0.067, GRASP_POINT.z - 0.098],
      dark,
    );
    cyl(
      module,
      0.005,
      0.004,
      [side * 0.012, 0.067, GRASP_POINT.z - 0.079],
      blue,
    );
    const railStart = new T.Vector3(side * 0.028, 0.05, GRASP_POINT.z - 0.132);
    beam(
      root,
      railStart,
      railStart
        .clone()
        .add(RETRACT)
        .add(new T.Vector3(0, 0.006, -0.006)),
      0.003,
      silver,
    );
    box(
      module,
      [0.012, 0.014, 0.015],
      [side * 0.028, 0.05, GRASP_POINT.z - 0.132],
      dark,
    );
  }
  beam(
    root,
    new T.Vector3(0, 0.029, GRASP_POINT.z - 0.14),
    new T.Vector3(0, 0.058, GRASP_POINT.z - 0.14),
    0.005,
    dark,
  );
  beam(
    root,
    new T.Vector3(0, 0.072, GRASP_POINT.z - 0.17),
    new T.Vector3(0, 0.035, GRASP_POINT.z - 0.133),
    0.006,
    dark,
  );
  const mains: { side: number; finger: T.Group; pad: T.Group; jaw: T.Group }[] =
    [];
  for (const side of [-1, 1]) {
    const finger = new T.Group();
    root.add(finger);
    part(finger, taperedFinger(), silver);
    const pad = new T.Group();
    finger.add(pad);
    // Passive X-axis pad bearing lets the bolt pivot without opening the main jaws.
    const axle = cyl(pad, 0.002, 0.003, [0, 0, 0], blue, 20);
    axle.rotation.set(0, 0, Math.PI / 2);
    box(pad, [0.001, 0.004, 0.004], [-side * 0.001, 0, 0], rubber);
    const jaw = new T.Group();
    module.add(jaw);
    box(
      jaw,
      [0.007, 0.013, 0.0165],
      [0, 0.042, GRASP_POINT.z - 0.04825],
      silver,
    );
    mains.push({ side, finger, pad, jaw });
  }
  const thumb = new T.Group();
  thumb.position.copy(THUMB_BASE);
  module.add(thumb);
  function knuckle(parent: T.Group, r: number) {
    const p = cyl(parent, r, 0.007, [0, 0, 0], dark, 24);
    p.rotation.set(0, 0, Math.PI / 2);
    const c = cyl(parent, r * 0.6, 0.0075, [0, 0, 0], silver, 20);
    c.rotation.set(0, 0, Math.PI / 2);
  }
  const proximal = new T.Group();
  thumb.add(proximal);
  knuckle(proximal, 0.0035);
  beam(
    proximal,
    new T.Vector3(),
    new T.Vector3(0, THUMB_LENGTHS[0], 0),
    0.002,
    blue,
  );
  const distal = new T.Group();
  distal.position.y = THUMB_LENGTHS[0];
  proximal.add(distal);
  knuckle(distal, 0.003);
  beam(
    distal,
    new T.Vector3(),
    new T.Vector3(0, THUMB_LENGTHS[1], 0),
    0.0015,
    silver,
  );
  part(distal, new T.SphereGeometry(ROLLER_RADIUS, 20, 12), rubber, [
    0,
    THUMB_LENGTHS[1],
    0,
  ]);
  // Rear support goes around the narrow closed-jaw gap, never through it.
  const supportPath = [
    new T.Vector3(0, 0.054, GRASP_POINT.z - 0.064),
    new T.Vector3(0, 0.058, GRASP_POINT.z - 0.025),
    new T.Vector3(0, 0.04, GRASP_POINT.z - 0.013),
    THUMB_BASE,
  ];
  for (let i = 0; i < supportPath.length - 1; i++)
    beam(module, supportPath[i], supportPath[i + 1], 0.0028, silver);
  for (const x of [-0.003, 0.003]) {
    const route = [
      new T.Vector3(x, 0.06, GRASP_POINT.z - 0.081),
      new T.Vector3(x, 0.064, GRASP_POINT.z - 0.025),
      new T.Vector3(x, 0.04, GRASP_POINT.z - 0.013),
    ];
    for (let i = 0; i < route.length - 1; i++)
      beam(module, route[i], route[i + 1], 0.0007, rubber);
  }
  const labelAnchors = [
    {
      name: "일자형 집게 · 테이퍼 팁",
      position: new T.Vector3(),
      color: colors.blue,
    },
    { name: "보조 엄지 · 50mm", position: new T.Vector3(), color: "#397f8b" },
    {
      name: "자동 조절 · 6조 척",
      position: new T.Vector3(),
      color: colors.orange,
    },
  ];
  async function load() {} // Geometry is local; only FR3 requires asset loading.
  function update(
    s: CycleState,
    spec: BoltSpec,
    transparent: boolean,
    exploded: boolean,
  ) {
    for (const m of translucent) {
      m.transparent = transparent;
      m.opacity = transparent ? 0.16 : 1;
      m.depthWrite = !transparent;
    }
    module.position.copy(RETRACT).multiplyScalar(s.clear);
    if (exploded) module.position.y += 0.035;
    for (const f of mains) {
      const p = mainFingerPose(f.side, s, spec);
      f.finger.position.copy(p.contact);
      if (exploded) {
        f.finger.position.x += f.side * 0.025;
        f.finger.position.y += 0.035;
      }
      f.pad.rotation.x = (-Math.PI / 2) * (1 - s.align);
      f.jaw.position.x = p.root.x;
    }
    const p = rodPose(s, spec);
    proximal.rotation.x = p.angles[0];
    distal.rotation.x = p.angles[1];
    carriage.position.z =
      -HEAD_STROKE * (1 - s.headAdvance) + (exploded ? 0.025 : 0);
    rotor.rotation.z = s.spindle + HEAD_CLOCKING;
    shaft.rotation.y = s.spindle;
    cam.position.z = 0.0048 * s.chuckClosed;
    for (const jaw of jaws)
      jaw.position.x =
        HEAD_OPEN_RADIUS +
        (spec.headWidth / 2 - HEAD_OPEN_RADIUS) * s.chuckClosed;
    labelAnchors[0].position.copy(mainFingerPose(-1, s, spec).contact);
    labelAnchors[1].position.copy(p.elbow);
    labelAnchors[2].position.set(0, 0, headZ + carriage.position.z);
  }
  return { root, load, update, labelAnchors };
}
