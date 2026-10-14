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
  fingerVector,
  fingerOffset,
  thumbOffset,
  RETRACT,
} from "./rod-kinematics";
import type { BoltSpec, CycleState } from "./timeline";
import { palette } from "./theme";
import type { Variant } from "./variants";
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
// Faceted straight blade: root 6×5 mm, cutting-style nose 1.6×2.4 mm.
function taperedFinger(side: number, variant: Variant) {
  const root = fingerVector(side, variant),
    vertices: number[] = [];
  const direction = root.clone().normalize();
  const across = new T.Vector3(1, 0, 0)
    .addScaledVector(direction, -direction.x)
    .normalize();
  const depth = new T.Vector3().crossVectors(direction, across).normalize();
  for (const [f, w, d] of [
    [1, 0.006, 0.005],
    [0.2, 0.0022, 0.003],
    [0, 0.0016, 0.0024],
  ]) {
    const c = root.clone().multiplyScalar(f);
    for (const [x, y] of [
      [-1, -1],
      [1, -1],
      [1, 1],
      [-1, 1],
    ])
      vertices.push(
        ...c
          .clone()
          .addScaledVector(across, (x * w) / 2)
          .addScaledVector(depth, (y * d) / 2)
          .toArray(),
      );
  }
  const indices = [0, 2, 1, 0, 3, 2, 8, 9, 10, 8, 10, 11];
  for (let layer = 0; layer < 2; layer++)
    for (let i = 0; i < 4; i++) {
      const a = layer * 4 + i,
        b = layer * 4 + ((i + 1) % 4);
      indices.push(a, b, b + 4, a, b + 4, a + 4);
    }
  const g = new T.BufferGeometry();
  g.setAttribute("position", new T.Float32BufferAttribute(vertices, 3));
  g.setIndex(indices);
  g.computeVertexNormals();
  return g;
}
export function makeGripper(variant: Variant = "a") {
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
  const shaft = cyl(root, 0.006, 0.054, [0, 0, 0.347], silver);
  shaft.name = "fixed-axial-output-shaft";
  for (const z of [0.323, 0.335]) ring(root, 0.011, 0.0063, 0.006, z, dark);
  // Fixed palm: open rear service window on A, continuous guard on B.
  const housing = new T.Group();
  housing.name = "stationary-palm";
  root.add(housing);
  cyl(housing, 0.035, 0.008, [0, 0, headZ - 0.031], dark);
  const shape = new T.Shape();
  const start = Math.PI * 0.75,
    end = Math.PI * 2.25;
  shape.absarc(0, 0, 0.0425, start, end, false);
  shape.lineTo(0.039 * Math.cos(end), 0.039 * Math.sin(end));
  shape.absarc(0, 0, 0.039, end, start, true);
  shape.closePath();
  part(
    housing,
    new T.ExtrudeGeometry(shape, {
      depth: variant === "a" ? 0.029 : 0.052,
      bevelEnabled: false,
      curveSegments: 48,
    }),
    cover(),
    [0, 0, variant === "a" ? headZ - 0.0295 : 0.3335],
  );
  // Rotor remains inside the fixed palm; no capture or fastening extension axis.
  const rotor = new T.Group();
  rotor.name = "internal-fastening-rotor";
  root.add(rotor);
  cyl(
    rotor,
    0.0345,
    variant === "a" ? 0.006 : 0.002,
    [0, 0, variant === "a" ? headZ - 0.024 : 0.3365],
    dark,
  );
  if (variant === "a") ring(rotor, 0.035, 0.028, 0.003, headZ - 0.018, blue);
  const scroll = new T.Group();
  rotor.add(scroll);
  ring(
    scroll,
    variant === "a" ? 0.031 : 0.025,
    0.008,
    0.003,
    variant === "a" ? headZ - 0.017 : 0.343,
    silver,
  );
  const spiral: T.Vector3[] = [];
  for (let i = 0; i <= 240; i++) {
    const a = (i / 240) * Math.PI * 6,
      r = 0.009 + (i / 240) * (variant === "a" ? 0.021 : 0.015);
    spiral.push(
      new T.Vector3(
        Math.cos(a) * r,
        Math.sin(a) * r,
        variant === "a" ? headZ - 0.0149 : 0.345,
      ),
    );
  }
  scroll.add(
    new T.Line(
      new T.BufferGeometry().setFromPoints(spiral),
      new T.LineBasicMaterial({ color: colors.orange }),
    ),
  );
  const heads: T.Group[] = [];
  for (let i = 0; i < (variant === "a" ? 6 : 2); i++) {
    const rail = new T.Group();
    rail.rotation.z = (i * Math.PI * 2) / (variant === "a" ? 6 : 2);
    rotor.add(rail);
    // Radial channels sit behind the swept head. Clamping faces alone enter its plane.
    box(
      rail,
      [0.026, 0.008, 0.003],
      [0.02, 0, variant === "a" ? headZ - 0.014 : headZ - 0.035],
      dark,
    );
    const jaw = new T.Group();
    jaw.name = "head-contact";
    rail.add(jaw);
    heads.push(jaw);
    box(
      jaw,
      [0.008, 0.0032, 0.002],
      [0.004, 0, variant === "a" ? headZ - 0.011 : headZ - 0.032],
      silver,
    );
    if (variant === "b")
      box(jaw, [0.0015, 0.006, 0.03], [0.00075, 0, headZ - 0.0176], silver);
    box(
      jaw,
      [
        variant === "a" ? 0.003 : 0.0015,
        variant === "a" ? 0.0032 : 0.006,
        variant === "a" ? 0.0084 : 0.0074,
      ],
      [
        variant === "a" ? 0.0015 : 0.00075,
        0,
        variant === "a" ? headZ - 0.0048 : headZ - 0.0043,
      ],
      copper,
    );
  }
  // A has a dedicated chuck actuator; B uses an indexed common cam for its two cassettes.
  box(housing, [0.018, 0.014, 0.022], [0, -0.04, headZ - 0.032], dark);
  for (const side of [-1, 1])
    box(
      root,
      [0.03, 0.01, 0.01],
      [side * 0.045, 0, GRASP_POINT.z - 0.09],
      blue,
    );
  const module = new T.Group();
  module.name =
    variant === "a" ? "sliding-shaft-module" : "integrated-two-jaw-cassettes";
  root.add(module);
  const aHardware = new T.Group();
  root.add(aHardware);
  if (variant === "a") {
    box(
      module,
      [0.044, 0.022, 0.069],
      [0, 0.052, GRASP_POINT.z - 0.0705],
      cover(),
    );
    box(module, [0.044, 0.024, 0.008], [0, 0.052, GRASP_POINT.z - 0.039], dark);
    // Twin open-bottom receiving channels show where the rigid fingers actually go.
    for (const side of [-1, 1]) {
      const a = new T.Vector3(side * 0.016, 0.052, GRASP_POINT.z - 0.02);
      const b = a.clone().add(RETRACT);
      for (const x of [-0.005, 0.005])
        beam(
          aHardware,
          a.clone().add(new T.Vector3(x, 0, 0)),
          b.clone().add(new T.Vector3(x, 0, 0)),
          0.002,
          blue,
        );
      beam(
        aHardware,
        new T.Vector3(side * 0.028, 0.065, 0.303),
        new T.Vector3(side * 0.028, 0.117, 0.283),
        0.003,
        silver,
      );
    }
    box(aHardware, [0.058, 0.07, 0.006], [0, 0.088, 0.299], cover());
  } else {
    // The same two rotating jaw carriers own both contact levels; no separate six-jaw chuck.
    for (const side of [-1, 1]) {
      beam(
        rotor,
        new T.Vector3(side * 0.029, side * 0.017, headZ - 0.03),
        new T.Vector3(side * 0.029, side * 0.017, headZ - 0.003),
        0.0028,
        blue,
      );
      box(
        rotor,
        [0.011, 0.01, 0.02],
        [side * 0.025, side * 0.016, headZ - 0.029],
        dark,
      );
    }
    ring(rotor, 0.033, 0.029, 0.002, 0.335, copper);
  }
  // A moves its pickup module; B only stores the short shaft blades inside the cassette.
  const mains: {
    side: number;
    finger: T.Group;
    pad: T.Group;
    carrier: T.Group;
  }[] = [];
  for (const side of [-1, 1]) {
    const finger = new T.Group();
    finger.name = "sharp-shaft-blade";
    root.add(finger);
    part(finger, taperedFinger(side, variant), silver);
    const pad = new T.Group();
    finger.add(pad);
    const axle = cyl(pad, 0.0015, 0.0016, [0, 0, 0], blue, 20);
    axle.rotation.set(0, 0, Math.PI / 2);
    box(pad, [0.0005, 0.0024, 0.0024], [-side * 0.00055, 0, 0], rubber);
    const carrier = new T.Group();
    root.add(carrier);
    if (variant === "a") {
      box(carrier, [0.006, 0.012, 0.015], [0, 0, -0.0075], dark);
      box(carrier, [0.009, 0.016, 0.003], [0, 0, -0.0165], blue);
    }
    mains.push({ side, finger, pad, carrier });
  }
  const accessory = new T.Group();
  root.add(accessory);
  // Thumb motors stay proximal; fingers remain small and free of motor envelopes.
  for (const side of [-1, 1])
    box(
      accessory,
      [0.02, 0.026, 0.034],
      [side * 0.012, 0.066, GRASP_POINT.z - 0.075],
      dark,
    );
  const thumb = new T.Group();
  thumb.position.copy(THUMB_BASE);
  accessory.add(thumb);
  function knuckle(parent: T.Group, r: number) {
    const p = cyl(parent, r, 0.007, [0, 0, 0], dark, 24);
    p.rotation.set(0, 0, Math.PI / 2);
    const cap = cyl(parent, r * 0.6, 0.0075, [0, 0, 0], silver, 20);
    cap.rotation.set(0, 0, Math.PI / 2);
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
  const support = [
    new T.Vector3(0, 0.07, 0.344),
    new T.Vector3(0, 0.064, 0.375),
    new T.Vector3(0, 0.04, 0.387),
    THUMB_BASE,
  ];
  for (let i = 0; i < support.length - 1; i++)
    beam(accessory, support[i], support[i + 1], 0.0028, silver);
  for (const x of [-0.003, 0.003])
    beam(
      accessory,
      new T.Vector3(x, 0.074, 0.343),
      new T.Vector3(x, 0.043, 0.387),
      0.0007,
      rubber,
    );
  const labelAnchors = [
    {
      name:
        variant === "a" ? "A · 날렵한 수납 팁" : "B · 통합 카세트의 몸통 팁",
      position: new T.Vector3(),
      color: colors.blue,
    },
    { name: "보조 엄지 · 50mm", position: new T.Vector3(), color: "#397f8b" },
    {
      name:
        variant === "a" ? "본체 내부 · 6조 회전 척" : "같은 2조 · 헤드 접촉면",
      position: new T.Vector3(),
      color: colors.orange,
    },
  ];
  async function load() {}
  function update(
    s: CycleState,
    spec: BoltSpec,
    transparent: boolean,
    exploded: boolean,
  ) {
    for (const m of translucent) {
      if (m.transparent !== transparent) m.needsUpdate = true;
      m.transparent = transparent;
      m.opacity = transparent ? 0.13 : 1;
      m.depthWrite = !transparent;
    }
    module.position.copy(
      variant === "a"
        ? fingerOffset(variant).multiplyScalar(s.clear)
        : new T.Vector3(),
    );
    accessory.position.copy(thumbOffset(variant)).multiplyScalar(s.clear);
    if (exploded) {
      module.position.y += 0.045;
      accessory.position.y += 0.06;
      housing.position.z = -0.05;
    } else housing.position.z = 0;
    for (const f of mains) {
      const p = mainFingerPose(f.side, s, spec, variant);
      f.finger.position.copy(p.contact);
      f.carrier.position.copy(p.root);
      f.finger.rotation.z = variant === "b" ? s.spindle : 0;
      if (exploded) f.finger.position.x += f.side * 0.045;
      f.pad.rotation.x = (-Math.PI / 2) * (1 - s.align);
    }
    const p = rodPose(s, spec, variant);
    proximal.rotation.x = p.angles[0];
    distal.rotation.x = p.angles[1];
    rotor.rotation.z = s.spindle + HEAD_CLOCKING;
    shaft.rotation.y = s.spindle;
    scroll.rotation.z = s.chuckClosed * Math.PI * 1.5;
    for (const jaw of heads)
      jaw.position.x =
        HEAD_OPEN_RADIUS +
        (spec.headWidth / 2 - HEAD_OPEN_RADIUS) * s.chuckClosed;
    labelAnchors[0].position.copy(mainFingerPose(-1, s, spec, variant).contact);
    labelAnchors[1].position.copy(p.elbow);
    labelAnchors[2].position.set(0, 0, headZ);
  }
  return { root, load, update, labelAnchors };
}
