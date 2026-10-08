import * as T from "three";
import { makeBolt } from "./models";
import { PRESETS, type BoltSpec } from "./timeline";
import {
  integratedPose,
  boltMatrix,
  fingerMatrix,
  fingerGap,
  thumbPoints,
} from "./integrated-kinematics";

export const INTEGRATED_BOM = [
  ["01", "공통 프레임·분할 커버", "1", "152 × 144 × 250", "공간 검토값"],
  ["02", "동축 모터·감속부", "1", "Ø40 × 105 / Ø48 × 45", "정격·구매품 미선정"],
  [
    "03",
    "고정 위치 회전 척",
    "1",
    "외경56 / 6조",
    "잠금·회전 중 폐쇄력 상세 설계 필요",
  ],
  ["04", "U형 캐리지·가이드", "1", "총 행정120", "인입50 + 수납70"],
  ["05", "직선 테이퍼 손가락", "2", "뿌리10 × 8 / 끝3 × 4", "개폐 후 90° 접힘"],
  ["06", "2관절 보조 엄지", "1", "38 + 38", "캐리지 장착 / 후면 수납"],
  [
    "07",
    "구동부·센서 설치 공간",
    "1식",
    "7개 제어 기능",
    "모터 수·센서 규격 미정",
  ],
] as const;

export function makeIntegratedAssembly(spec: BoltSpec = PRESETS[1]) {
  const root = new T.Group();
  root.name = "R08-INTEGRATED-ASSEMBLY-REVIEW";
  const mat = (c: string, metalness = 0.65) =>
    new T.MeshStandardMaterial({ color: c, metalness, roughness: 0.35 });
  const steel = mat("#b4c5ca"),
    dark = mat("#263d44"),
    teal = mat("#28747a"),
    gold = mat("#c28d49"),
    black = mat("#182a31", 0.2);
  const shellMaterial = mat("#ced8d7", 0.4);
  const shell = new T.Group();
  shell.name = "removable-covers";
  root.add(shell);
  const frame = new T.Group();
  frame.name = "common-load-frame";
  root.add(frame);
  const carrier = new T.Group();
  carrier.name = "common-U-carriage";
  root.add(carrier);
  const rotor = new T.Group();
  rotor.name = "fixed-axial-internal-rotor";
  root.add(rotor);
  function mesh(
    p: T.Object3D,
    g: T.BufferGeometry,
    m: T.Material,
    n: string,
    pos = [0, 0, 0],
  ) {
    const o = new T.Mesh(g, m);
    o.name = n;
    o.position.fromArray(pos);
    o.castShadow = o.receiveShadow = true;
    p.add(o);
    return o;
  }
  function box(
    p: T.Object3D,
    s: number[],
    pos: number[],
    m: T.Material,
    n: string,
  ) {
    return mesh(p, new T.BoxGeometry(s[0], s[1], s[2]), m, n, pos);
  }
  function cyl(
    p: T.Object3D,
    r: number,
    l: number,
    pos: number[],
    m: T.Material,
    n: string,
    axis = "z",
  ) {
    const o = mesh(p, new T.CylinderGeometry(r, r, l, 40), m, n, pos);
    if (axis === "z") o.rotation.x = Math.PI / 2;
    if (axis === "x") o.rotation.z = Math.PI / 2;
    return o;
  }
  function ring(
    p: T.Object3D,
    ro: number,
    ri: number,
    l: number,
    z: number,
    m: T.Material,
    n: string,
  ) {
    const shape = new T.Shape();
    shape.absarc(0, 0, ro, 0, Math.PI * 2, false);
    const hole = new T.Path();
    hole.absarc(0, 0, ri, 0, Math.PI * 2, true);
    shape.holes.push(hole);
    return mesh(
      p,
      new T.ExtrudeGeometry(shape, {
        depth: l,
        bevelEnabled: false,
        curveSegments: 40,
      }),
      m,
      n,
      [0, 0, z - l / 2],
    );
  }
  function beam(
    p: T.Object3D,
    a: T.Vector3,
    b: T.Vector3,
    r: number,
    m: T.Material,
    n: string,
  ) {
    const o = cyl(p, r, a.distanceTo(b), [0, 0, 0], m, n, "y");
    o.position.copy(a).add(b).multiplyScalar(0.5);
    o.quaternion.setFromUnitVectors(
      new T.Vector3(0, 1, 0),
      b.clone().sub(a).normalize(),
    );
    return o;
  }
  function roundedOutline(w: number, h: number, r: number) {
    const s = new T.Shape();
    s.moveTo(-w / 2 + r, -h / 2);
    s.lineTo(w / 2 - r, -h / 2);
    s.quadraticCurveTo(w / 2, -h / 2, w / 2, -h / 2 + r);
    s.lineTo(w / 2, h / 2 - r);
    s.quadraticCurveTo(w / 2, h / 2, w / 2 - r, h / 2);
    s.lineTo(-w / 2 + r, h / 2);
    s.quadraticCurveTo(-w / 2, h / 2, -w / 2, h / 2 - r);
    s.lineTo(-w / 2, -h / 2 + r);
    s.quadraticCurveTo(-w / 2, -h / 2, -w / 2 + r, -h / 2);
    return s;
  }
  // Hollow continuous perimeter: the visual envelope is not a solid block.
  const outline = roundedOutline(152, 144, 22);
  const inner = roundedOutline(146, 138, 19);
  outline.holes.push(new T.Path(inner.getPoints(40).reverse()));
  mesh(
    shell,
    new T.ExtrudeGeometry(outline, {
      depth: 240,
      bevelEnabled: false,
      curveSegments: 20,
    }),
    shellMaterial,
    "hollow-perimeter-cover",
    [0, 0, -247],
  );
  // Front face has physical access ports for the two fingers, thumb and chuck.
  const nose = roundedOutline(152, 144, 22);
  for (const [x, y, w, h] of [
    [-51, 0, 40, 28],
    [51, 0, 40, 28],
    [-10, 50, 44, 40],
  ]) {
    const hole = new T.Path();
    hole.moveTo(x - w / 2, y - h / 2);
    hole.lineTo(x - w / 2, y + h / 2);
    hole.lineTo(x + w / 2, y + h / 2);
    hole.lineTo(x + w / 2, y - h / 2);
    hole.closePath();
    nose.holes.push(hole);
  }
  const centerHole = new T.Path();
  centerHole.absarc(0, 0, 29, 0, Math.PI * 2, true);
  nose.holes.push(centerHole);
  mesh(
    shell,
    new T.ExtrudeGeometry(nose, { depth: 3, bevelEnabled: false }),
    dark,
    "front-plate-with-working-ports",
    [0, 0, -3],
  );
  const cap = roundedOutline(152, 144, 22);
  mesh(
    shell,
    new T.ExtrudeGeometry(cap, { depth: 3, bevelEnabled: false }),
    shellMaterial,
    "rear-service-cap",
    [0, 0, -250],
  );
  // Structural end plates remain with the chassis when service covers are off.
  mesh(
    frame,
    new T.ExtrudeGeometry(nose, { depth: 3, bevelEnabled: false }),
    steel,
    "common-front-structural-plate",
    [0, 0, -6],
  );
  const backPlate = roundedOutline(142, 134, 17);
  const cableBore = new T.Path();
  cableBore.absarc(0, 0, 13, 0, Math.PI * 2, true);
  backPlate.holes.push(cableBore);
  mesh(
    frame,
    new T.ExtrudeGeometry(backPlate, { depth: 6, bevelEnabled: false }),
    steel,
    "common-rear-structural-plate",
    [0, 0, -245],
  );
  // Narrow service seams distinguish bolted covers from a monolithic solid.
  for (const y of [-72, 72]) {
    box(shell, [99, 0.4, 1], [0, y, -62], dark, "service-cover-seam");
    box(shell, [32, 0.4, 5], [0, y, -212], teal, "cover-identification-insert");
    for (const x of [-46, 46])
      for (const z of [-70, -229])
        cyl(shell, 2, 1, [x, y, z], dark, "service-cover-fastener", "y");
  }
  ring(frame, 38, 16, 9, -254, dark, "robot-mount-flange");
  for (let i = 0; i < 6; i++) {
    const a = (i * Math.PI) / 3;
    cyl(
      frame,
      2.6,
      4,
      [30 * Math.cos(a), 30 * Math.sin(a), -260],
      steel,
      `mount-fastener-${i}`,
    );
  }
  for (const x of [-65, 65])
    for (const y of [-52, 52]) {
      box(frame, [8, 8, 242], [x, y, -124], steel, "frame-longitudinal-rib");
      for (const z of [-5, -244])
        cyl(shell, 2.5, 2, [x, y, z], black, "cover-screw");
    }
  for (const z of [-220, -38]) {
    ring(frame, 34, 26, 6, z, steel, "spindle-support-bridge");
    for (const x of [-50, 50])
      box(frame, [38, 7, 6], [x, -25, z], steel, "frame-cross-member");
    for (const sx of [-1, 1])
      for (const sy of [-1, 1])
        beam(
          frame,
          new T.Vector3(sx * 20, sy * 20, z),
          new T.Vector3(sx * 65, sy * 52, z),
          3,
          steel,
          "spindle-to-common-frame-strut",
        );
  }
  // All drive dimensions are reserved envelopes, not selected vendor products.
  cyl(frame, 20, 105, [0, 0, -147.5], teal, "motor-envelope-unselected");
  cyl(frame, 24, 4, [0, 0, -202], steel, "motor-mount-plate");
  for (const x of [-14, 14])
    cyl(frame, 3, 35, [x, 0, -221.5], steel, "motor-mount-standoff");
  cyl(frame, 24, 45, [0, 0, -72.5], dark, "gearhead-envelope-unselected");
  cyl(rotor, 8, 24, [0, 0, -38], steel, "output-shaft");
  ring(frame, 15, 8.2, 9, -39, steel, "output-bearing-envelope");
  ring(frame, 30, 28.5, 27, -16.5, dark, "stationary-chuck-bearing-seat");
  for (let i = 0; i < 6; i++) {
    const a = (i * Math.PI) / 3 + 0.16,
      b = ((i + 1) * Math.PI) / 3 - 0.16;
    const sector = new T.Shape();
    sector.absarc(0, 0, 28, a, b, false);
    sector.lineTo(19.5 * Math.cos(b), 19.5 * Math.sin(b));
    sector.absarc(0, 0, 19.5, b, a, true);
    sector.closePath();
    mesh(
      rotor,
      new T.ExtrudeGeometry(sector, { depth: 25, bevelEnabled: false }),
      gold,
      `chuck-web-between-slots-${i}`,
      [0, 0, -28],
    );
  }
  ring(rotor, 28, 20.5, 2, -2, gold, "chuck-front-rim");
  ring(rotor, 28, 19.5, 2, -29, gold, "chuck-rear-rim");
  ring(rotor, 19.5, 11, 5, -27, steel, "radial-jaw-support");
  cyl(rotor, 16, 4, [0, 0, -29], steel, "shaft-to-chuck-flange");
  // The closure ring is an installation envelope; no fictitious lock is implied.
  ring(frame, 24, 16, 12, -38, teal, "chuck-closure-actuator-envelope");
  const jaws: T.Group[] = [];
  for (let i = 0; i < 6; i++) {
    const g = new T.Group();
    g.rotation.z = (i * Math.PI) / 3;
    rotor.add(g);
    jaws.push(g);
    box(g, [7, 5, 7], [0, 0, -3.5], steel, `head-jaw-${i + 1}`);
    box(g, [12, 4, 17], [3, 0, -15], dark, `radial-slider-${i + 1}`);
  }
  for (const x of [-58, 58]) {
    cyl(frame, 4, 175, [x, -16, -115], steel, "fixed-carriage-guide");
    for (const z of [-202, -28])
      box(frame, [12, 14, 8], [x, -16, z], dark, "guide-seat");
    const b = ring(carrier, 7, 4.1, 23, -100, gold, "sliding-guide-bushing");
    b.position.x = x;
    b.position.y = -16;
    box(carrier, [10, 36, 8], [x, -32, -100], steel, "guide-to-carriage-arm");
  }
  cyl(frame, 3, 172, [0, -48, -117], steel, "axial-feed-screw");
  cyl(frame, 11, 28, [0, -48, -218], teal, "feed-motor-envelope");
  box(carrier, [110, 12, 10], [0, -48, -100], steel, "rear-U-crossbar");
  box(carrier, [13, 14, 15], [0, -48, -100], gold, "feed-nut");
  cyl(carrier, 2.5, 108, [0, -48, -90], steel, "opposed-jaw-leadscrew", "x");
  box(
    carrier,
    [22, 20, 20],
    [0, -49, -75],
    teal,
    "parallel-grip-drive-envelope",
  );
  const fingers: T.Group[] = [],
    columns: T.Group[] = [],
    pads: T.Mesh[] = [];
  for (const side of [-1, 1]) {
    const column = new T.Group();
    carrier.add(column);
    columns.push(column);
    box(column, [10, 10, 98], [0, 0, -50], dark, "finger-side-column");
    box(column, [12, 49, 8], [0, -24, -100], steel, "U-arm");
    box(column, [13, 18, 22], [0, 0, -67], teal, "finger-fold-drive-envelope");
    cyl(column, 2, 50, [0, 0, -31], steel, "fold-transmission-shaft");
    cyl(column, 6, 12, [0, 0, 0], steel, "supported-fold-hinge", "y");
    const finger = new T.Group();
    root.add(finger);
    fingers.push(finger);
    const a = new T.Vector3(),
      b = new T.Vector3(-side * 38, 0, 14);
    const n = new T.Vector3(b.z, 0, -b.x).normalize(),
      vertices: number[] = [];
    for (const [p, w, d] of [
      [a, 5, 4],
      [b, 1.5, 2],
    ] as const)
      for (const [u, v] of [
        [-1, -1],
        [1, -1],
        [1, 1],
        [-1, 1],
      ]) {
        const q = p
          .clone()
          .add(new T.Vector3(0, u * w, 0))
          .addScaledVector(n, v * d);
        vertices.push(...q.toArray());
      }
    const geometry = new T.BufferGeometry();
    geometry.setAttribute(
      "position",
      new T.Float32BufferAttribute(vertices, 3),
    );
    geometry.setIndex([
      0, 2, 1, 0, 3, 2, 4, 5, 6, 4, 6, 7, 0, 1, 5, 0, 5, 4, 1, 2, 6, 1, 6, 5, 2,
      3, 7, 2, 7, 6, 3, 0, 4, 3, 4, 7,
    ]);
    geometry.computeVertexNormals();
    mesh(finger, geometry, steel, "straight-tapered-finger");
    const pad = cyl(
      finger,
      2.2,
      3,
      b.toArray(),
      black,
      "passive-grasp-pad",
      "x",
    );
    pads.push(pad);
    for (const u of [0.14, 0.27])
      cyl(
        finger,
        1.7,
        5,
        b.clone().multiplyScalar(u).toArray(),
        dark,
        "finger-fastener",
        "y",
      );
  }
  const thumb = new T.Group();
  thumb.name = "integrated-two-joint-thumb";
  root.add(thumb);
  const thumbLinks = [
    beam(
      thumb,
      new T.Vector3(),
      new T.Vector3(0, 0, 38),
      3,
      teal,
      "thumb-proximal",
    ),
    beam(
      thumb,
      new T.Vector3(),
      new T.Vector3(0, 0, 38),
      2.5,
      teal,
      "thumb-distal",
    ),
  ];
  const thumbJoints = [0, 1, 2].map((i) =>
    cyl(
      thumb,
      i === 2 ? 2 : 5,
      i === 2 ? 4 : 12,
      [0, 0, 0],
      steel,
      `thumb-joint-${i}`,
      "x",
    ),
  );
  const rollerShaft = cyl(
    thumb,
    1.5,
    16,
    [0, 0, 0],
    steel,
    "offset-roller-shaft",
    "x",
  );
  const roller = cyl(
    thumb,
    2,
    10,
    [0, 0, 0],
    black,
    "bolt-contact-roller",
    "x",
  );
  box(carrier, [20, 13, 52], [-16, 40, -45], dark, "thumb-drive-housing");
  for (const x of [-5, 5])
    cyl(carrier, 4, 32, [x - 16, 39, -40], teal, "thumb-tendon-motor-envelope");
  box(carrier, [17, 15, 12], [-16, 38, 0], dark, "thumb-base-mount");
  const bolt = makeBolt(spec, true);
  bolt.scale.setScalar(1000);
  bolt.name = "held-bolt";
  root.add(bolt);
  const labels = [
    { name: "공통 몸체 · 152 × 144", point: new T.Vector3(-75, -36, -150) },
    { name: "중앙 동축 구동부", point: new T.Vector3(0, 0, -135) },
    { name: "위치가 고정된 회전 척", point: new T.Vector3(0, 0, -9) },
    { name: "양옆 집게 수납 공간", point: new T.Vector3(61, 0, -45) },
  ];
  function update(t: number, transparent: boolean, explode: boolean) {
    const s = integratedPose(t);
    carrier.position.z = s.carriageZ;
    shellMaterial.transparent = transparent;
    shellMaterial.opacity = transparent ? 0.12 : 1;
    shellMaterial.depthWrite = !transparent;
    shell.visible = !explode;
    rotor.rotation.z = s.spin;
    jaws.forEach((g, i) => {
      const angle = (i * Math.PI) / 3;
      const r = 16 * (1 - s.clamp) + (spec.headWidth * 500 + 3.5) * s.clamp;
      g.position.set(r * Math.cos(angle), r * Math.sin(angle), 0);
    });
    fingers.forEach((f, i) => {
      const side = i === 0 ? -1 : 1;
      f.matrixAutoUpdate = false;
      f.matrix.copy(fingerMatrix(s, spec, side));
      columns[i].position.x = side * (38 + fingerGap(s, spec));
      pads[i].rotation.x = (-Math.PI / 2) * (1 - s.align);
    });
    const pts = thumbPoints(s, spec);
    thumbLinks.forEach((o, i) => {
      o.position
        .copy(pts[i])
        .add(pts[i + 1])
        .multiplyScalar(0.5);
      o.quaternion.setFromUnitVectors(
        new T.Vector3(0, 1, 0),
        pts[i + 1].clone().sub(pts[i]).normalize(),
      );
    });
    thumbJoints.forEach((o, i) => o.position.copy(pts[i]));
    rollerShaft.position.copy(pts[2]);
    rollerShaft.position.x = -8;
    roller.position.copy(pts[2]);
    roller.position.x = 0;
    bolt.matrixAutoUpdate = false;
    bolt.matrix.copy(boltMatrix(s)).scale(new T.Vector3(1000, 1000, 1000));
    root.updateMatrixWorld(true);
  }
  update(0, false, false);
  return { root, labels, update };
}
