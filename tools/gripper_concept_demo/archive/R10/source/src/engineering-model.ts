import * as T from "three";
import { makeBolt } from "./models";
import { PRESETS, sampleCycle, ramp, type BoltSpec } from "./timeline";
import { rodPose } from "./rod-kinematics";
import {
  DESIGN as D,
  assemblyPose,
  gripTransform,
  boltTransform,
  jawHalfGap,
} from "./engineering-kinematics";
import type { Variant } from "./variants";

export const ASSEMBLY_BOM = [
  [
    "01",
    "체결 스핀들",
    "1",
    "Ø57 × 322 설치 공간",
    "구매품 후보 · 토크 미선정",
  ],
  [
    "02",
    "내부 다조 척",
    "1",
    "외경104 / 개방 내측48",
    "자체 설계 공간 · 정격 미확정",
  ],
  [
    "03",
    "회전축 / 베어링",
    "1 / 2",
    "축Ø16 / 지지 간격24",
    "가선정 치수 · 끼워맞춤 미정",
  ],
  [
    "04",
    "6개 방사형 턱",
    "6",
    "개방 반경24 → 5~8.5",
    "강재 후보 · 접촉/잠금 설계 필요",
  ],
  [
    "05",
    "평행 파지 모듈",
    "1",
    "80 × 45 × 65 설치 공간",
    "긴 손가락 허용 모듈 선정 필요",
  ],
  [
    "06",
    "일자 테이퍼 손가락",
    "2",
    "뿌리12×10 / 끝3×4 / 길이113.1",
    "강재 후보 · 장착 나사/핀 표현",
  ],
  [
    "07",
    "직선 수납 캐리지",
    "1",
    "뒤60 / 위35 / 행정69.5",
    "레일2 / 블록2 / 나사1",
  ],
  [
    "08A",
    "2관절 보조 엄지",
    "A:1",
    "25+25 / 수동 회전 패드",
    "텐던·파지 안정성 추가 설계",
  ],
  [
    "08B",
    "1축 회전 크래들",
    "B:1",
    "90° / 양측 지지 / 브레이크",
    "감속기 설치 공간 · 규격 미선정",
  ],
  [
    "09",
    "척 폐쇄 액추에이터",
    "1",
    "축방향 인입 / 회전 추력 전달",
    "캠·씰·기계 잠금 미설계",
  ],
  [
    "10",
    "고정 반력 탭",
    "2",
    "회전축에서 반경65",
    "상대 지그 필수 · 허용 하중 미정",
  ],
] as const;
const material = (c: string, metalness = 0.65) =>
  new T.MeshStandardMaterial({ color: c, roughness: 0.42, metalness });
export function makeEngineeringAssembly(
  variant: Variant,
  spec: BoltSpec = PRESETS[1],
) {
  const root = new T.Group();
  root.name = `R07-${variant.toUpperCase()}-ASSEMBLY-REVIEW-NOT-RELEASED`;
  const steel = material("#a6b8c2"),
    dark = material("#243942"),
    teal = material("#246f7c"),
    gold = material("#ba843c"),
    black = material("#202b31", 0.2),
    cast = material("#657982");
  const covers: T.MeshStandardMaterial[] = [];
  const housingMat = () => {
    const m = material("#d6dedd", 0.35);
    covers.push(m);
    return m;
  };
  const meshes: T.Mesh[] = [];
  function mesh(
    p: T.Object3D,
    g: T.BufferGeometry,
    m: T.Material,
    name: string,
    pos = [0, 0, 0],
  ) {
    const o = new T.Mesh(g, m);
    o.name = name;
    o.position.fromArray(pos);
    o.castShadow = o.receiveShadow = true;
    p.add(o);
    meshes.push(o);
    return o;
  }
  function box(
    p: T.Object3D,
    s: number[],
    pos: number[],
    m: T.Material,
    name: string,
  ) {
    return mesh(p, new T.BoxGeometry(s[0], s[1], s[2]), m, name, pos);
  }
  function cyl(
    p: T.Object3D,
    r: number,
    l: number,
    pos: number[],
    m: T.Material,
    name: string,
    axis = "z",
  ) {
    const o = mesh(p, new T.CylinderGeometry(r, r, l, 40), m, name, pos);
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
    name: string,
  ) {
    const s = new T.Shape();
    s.absarc(0, 0, ro, 0, 2 * Math.PI, false);
    const h = new T.Path();
    h.absarc(0, 0, ri, 0, 2 * Math.PI, true);
    s.holes.push(h);
    return mesh(
      p,
      new T.ExtrudeGeometry(s, {
        depth: l,
        bevelEnabled: false,
        curveSegments: 48,
      }),
      m,
      name,
      [0, 0, z - l / 2],
    );
  }
  function beam(
    p: T.Object3D,
    a: T.Vector3,
    b: T.Vector3,
    r: number,
    m: T.Material,
    name: string,
  ) {
    const o = mesh(
      p,
      new T.CylinderGeometry(r, r, a.distanceTo(b), 20),
      m,
      name,
    );
    o.position.copy(a).add(b).multiplyScalar(0.5);
    o.quaternion.setFromUnitVectors(
      new T.Vector3(0, 1, 0),
      b.clone().sub(a).normalize(),
    );
    return o;
  }
  function line(
    p: T.Object3D,
    points: T.Vector3[],
    color: string,
    name: string,
  ) {
    const o = new T.Line(
      new T.BufferGeometry().setFromPoints(points),
      new T.LineBasicMaterial({ color }),
    );
    o.name = name;
    p.add(o);
    return o;
  }
  function plate(
    p: T.Object3D,
    w: number,
    h: number,
    th: number,
    z: number,
    holes: { x: number; y: number; r: number }[],
    name: string,
    m = steel,
  ) {
    const s = new T.Shape();
    s.moveTo(-w / 2, -h / 2);
    s.lineTo(w / 2, -h / 2);
    s.lineTo(w / 2, h / 2);
    s.lineTo(-w / 2, h / 2);
    s.closePath();
    for (const { x, y, r } of holes) {
      const path = new T.Path();
      path.absarc(x, y, r, 0, Math.PI * 2, true);
      s.holes.push(path);
    }
    return mesh(
      p,
      new T.ExtrudeGeometry(s, {
        depth: th,
        bevelEnabled: false,
        curveSegments: 24,
      }),
      m,
      name,
      [0, 0, z - th / 2],
    );
  }
  function fastener(p: T.Object3D, x: number, y: number, z: number, r = 2.5) {
    // visible cap + shank, no pretend helical manufacturing thread
    cyl(p, r * 0.6, 8, [x, y, z + 3], dark, "fastener-shank");
    const cap = ring(p, r, r * 0.45, 3, z, dark, "socket-cap");
    cap.position.x = x;
    cap.position.y = y;
  }
  const fixed = new T.Group();
  fixed.name = "FIXED-HOUSING-AND-REACTION-PATH";
  root.add(fixed);
  ring(fixed, 34, 14, 12, -418, dark, "robot-adapter-bore");
  for (let i = 0; i < 6; i++) {
    const a = (i * Math.PI) / 3;
    fastener(fixed, 26 * Math.cos(a), 26 * Math.sin(a), -424, 3);
  }
  cyl(
    fixed,
    28.5,
    322,
    [0, 0, -251],
    housingMat(),
    "01-SPINDLE-INSTALLATION-ENVELOPE",
  );
  for (const z of [-400, -220, -105])
    ring(fixed, 30, 28.6, 8, z, teal, "spindle-clamp-band");
  box(fixed, [18, 14, 30], [0, -34, -385], black, "power-and-signal-connector");
  const driveShaft = cyl(
    root,
    8,
    60,
    [0, 0, -70],
    steel,
    "03-ROTATING-SHAFT-16mm",
  );
  for (const z of [-76, -52]) {
    ring(fixed, 17, 8.2, 10, z, dark, "03-BEARING-INSTALLATION-ENVELOPE");
    ring(fixed, 23, 17.2, 12, z, steel, "bearing-seat");
  }
  ring(fixed, 52, 23, 8, -43, cast, "chuck-rear-mounting-ring");
  // Rear service opening is real removed volume, not an opaque plate hiding a collision.
  const shell = new T.Shape();
  shell.absarc(0, 0, 52, Math.PI, 2 * Math.PI, false);
  shell.lineTo(48, 0);
  shell.absarc(0, 0, 48, 2 * Math.PI, Math.PI, true);
  shell.closePath();
  mesh(
    fixed,
    new T.ExtrudeGeometry(shell, {
      depth: 40,
      bevelEnabled: false,
      curveSegments: 48,
    }),
    housingMat(),
    "02-FRONT-HALF-GUARD-REAR-OPEN",
    [0, 0, -40.5],
  );
  const rotor = new T.Group();
  rotor.name = "ROTATING-CHUCK-NO-AXIAL-EXTENSION";
  root.add(rotor);
  ring(rotor, 44, 8, 6, -30, dark, "rotor-back-flange");
  cyl(rotor, 12, 12, [0, 0, -39], steel, "shaft-keyed-hub");
  const jaws: T.Group[] = [];
  for (let i = 0; i < 6; i++) {
    const rail = new T.Group();
    rail.rotation.z = (i * Math.PI) / 3;
    rotor.add(rail);
    // Raised flanks with an actual open channel; the slider is not inside a solid rail.
    for (const y of [-6, 6])
      box(rail, [28, 3, 7], [28.5, y, -20], steel, "04-radial-guide-flank");
    box(rail, [30, 15, 3], [28.5, 0, -25], cast, "04-radial-guide-base");
    const jaw = new T.Group();
    jaw.name = `04-JAW-${i + 1}`;
    rail.add(jaw);
    jaws.push(jaw);
    const profile = new T.Shape();
    profile.moveTo(0, -1.9);
    profile.lineTo(6, -4);
    profile.lineTo(16, -4);
    profile.lineTo(16, 4);
    profile.lineTo(6, 4);
    profile.lineTo(0, 1.9);
    profile.closePath();
    mesh(
      jaw,
      new T.ExtrudeGeometry(profile, { depth: 10, bevelEnabled: false }),
      steel,
      "jaw-load-body",
      [0, 0, -17],
    );
    box(jaw, [6, 3.8, 6.2], [3, 0, -4], gold, "hardened-hex-contact-insert");
    box(jaw, [12, 8, 6], [10, 0, -20], dark, "captured-master-slider");
    fastener(jaw, 10, 0, -17.5, 2.4);
  }
  // Real architecture boundary: actuator/thrust-transfer envelopes, not fictitious finished cam teeth.
  const clampRing = new T.Group();
  clampRing.name = "09-DRAW-SLEEVE-ARCHITECTURE-ENVELOPE";
  root.add(clampRing);
  ring(clampRing, 27, 23.5, 20, -76, gold, "draw-sleeve");
  ring(clampRing, 31, 27.2, 8, -82, steel, "clamp-thrust-bearing-envelope");
  ring(
    fixed,
    36,
    31.5,
    38,
    -80,
    housingMat(),
    "09-STATIONARY-CLAMP-ACTUATOR-ENVELOPE",
  );
  // Fixed reaction tabs attach to a split collar; they require a matching external fixture.
  ring(fixed, 34, 28.6, 16, -145, cast, "reaction-collar");
  for (const side of [-1, 1])
    box(fixed, [39, 14, 14], [side * 49, 0, -145], teal, "10-REACTION-TAB");
  // Split mounting bridge with the spindle bore and four real mounting holes.
  for (const side of [-1, 1]) {
    box(fixed, [50, 26, 10], [side * 54, 0, -126], steel, "slide-mounting-ear");
    fastener(fixed, side * 66, -7, -132, 3);
    fastener(fixed, side * 66, 7, -132, 3);
  }
  ring(fixed, 35, 28.6, 14, -126, steel, "slide-support-collar");
  const axis = D.retract.clone().normalize();
  const start = new T.Vector3(0, 35, -110);
  const carriageOrigin = start.clone().addScaledVector(axis, 35);
  const carriage = new T.Group();
  carriage.name = "07-SLIDE-CARRIAGE-69.5mm";
  root.add(carriage);
  for (const side of [-1, 1]) {
    const a = start.clone();
    a.x = side * 65;
    const b = a.clone().addScaledVector(axis, 140);
    beam(
      fixed,
      new T.Vector3(side * 65, 0, -126),
      a,
      5,
      cast,
      "fixed-rail-standoff",
    );
    beam(fixed, a, b, 5, steel, "07-10mm-guide-shaft");
    const c = carriageOrigin.clone();
    c.x = side * 65;
    const block = ring(
      carriage,
      9,
      5.05,
      32,
      0,
      dark,
      "07-linear-bushing-carriage",
    );
    block.position.copy(c);
    block.quaternion.setFromUnitVectors(new T.Vector3(0, 0, 1), axis);
    beam(
      carriage,
      c,
      new T.Vector3(side * 50, 100, -80),
      5,
      steel,
      "pickup-cradle-support",
    );
  }
  box(
    carriage,
    [138, 14, 12],
    carriageOrigin.toArray(),
    teal,
    "moving-crossmember",
  );
  const screwStart = start.clone();
  screwStart.x = -83;
  beam(
    fixed,
    screwStart,
    screwStart.clone().addScaledVector(axis, 140),
    3,
    dark,
    "07-lead-screw-envelope",
  );
  const nut = cyl(
    carriage,
    6,
    16,
    carriageOrigin.clone().setX(-83).toArray(),
    gold,
    "07-lead-nut",
    "y",
  );
  nut.quaternion.setFromUnitVectors(new T.Vector3(0, 1, 0), axis);
  beam(
    carriage,
    carriageOrigin.clone().setX(-83),
    carriageOrigin.clone().setX(-65),
    4,
    steel,
    "lead-nut-mount",
  );
  const motorCentre = screwStart.clone().addScaledVector(axis, -24);
  const slideMotor = cyl(
    fixed,
    12,
    38,
    motorCentre.toArray(),
    black,
    "07-slide-motor-envelope",
    "y",
  );
  slideMotor.quaternion.setFromUnitVectors(new T.Vector3(0, 1, 0), axis);
  beam(
    fixed,
    new T.Vector3(-65, 0, -126),
    screwStart,
    5,
    steel,
    "slide-motor-bracket",
  );
  for (const f of [0, 1])
    box(
      fixed,
      [9, 9, 10],
      start
        .clone()
        .setX(72)
        .addScaledVector(axis, 35 + f * D.retract.length())
        .toArray(),
      black,
      "slide-end-sensor-envelope",
    );
  const pickup = new T.Group();
  pickup.name = "05-PARALLEL-PICKUP-CASSETTE";
  root.add(pickup);
  const pc = D.pivot;
  box(
    pickup,
    [80, 45, 65],
    pc.toArray(),
    housingMat(),
    "05-GRIPPER-INSTALLATION-ENVELOPE-NOT-SELECTED",
  );
  // Linear master jaw rails and fastening faces. Clamp motor is an envelope inside the module.
  for (const y of [92, 108])
    box(pickup, [76, 4, 5], [0, y, -45], steel, "05-master-jaw-guide");
  const fingers: { group: T.Group; pad: T.Group; side: number }[] = [];
  function blade(side: number) {
    const root = D.fingerRoot
        .clone()
        .sub(D.grasp)
        .setX(side * 20),
      dir = root.clone().normalize();
    const across = new T.Vector3(1, 0, 0)
      .addScaledVector(dir, -dir.x)
      .normalize();
    const depth = new T.Vector3().crossVectors(dir, across).normalize();
    const vertices: number[] = [];
    for (const [f, w, d] of [
      [1, 12, 10],
      [0.12, 5, 6],
      [0, 3, 4],
    ])
      for (const [x, y] of [
        [-1, -1],
        [1, -1],
        [1, 1],
        [-1, 1],
      ])
        vertices.push(
          ...root
            .clone()
            .multiplyScalar(f)
            .addScaledVector(across, (x * w) / 2)
            .addScaledVector(depth, (y * d) / 2)
            .toArray(),
        );
    const idx = [0, 2, 1, 0, 3, 2, 8, 9, 10, 8, 10, 11];
    for (let l = 0; l < 2; l++)
      for (let i = 0; i < 4; i++) {
        const a = l * 4 + i,
          b = l * 4 + ((i + 1) % 4);
        idx.push(a, b, b + 4, a, b + 4, a + 4);
      }
    const g = new T.BufferGeometry();
    g.setAttribute("position", new T.Float32BufferAttribute(vertices, 3));
    g.setIndex(idx);
    g.computeVertexNormals();
    const f = new T.Group();
    pickup.add(f);
    mesh(f, g, steel, `06-SHARP-TAPERED-FINGER-${side}`, [0, 0, 14]);
    const pad = new T.Group();
    pad.position.z = 14;
    f.add(pad);
    if (variant === "a")
      cyl(pad, 2, 3, [0, 0, 0], teal, "passive-pad-pin", "x");
    box(
      pad,
      [0.6, 3, 3],
      [-side * 1.2, 0, 0],
      black,
      variant === "a" ? "passive-pivot-contact" : "fixed-grip-contact",
    );
    const shoe = plate(
      f,
      14,
      24,
      5,
      -37,
      [
        { x: 0, y: 7, r: 1.7 },
        { x: 0, y: -7, r: 1.7 },
        { x: 4, y: 0, r: 1 },
      ],
      "06-finger-mount-drilled-shoe",
    );
    shoe.position.y = 100;
    shoe.position.x = side * 20;
    // Fasteners straddle the taper root; its load goes through the shoulder and dowel.
    for (const y of [93, 107]) fastener(f, side * 20, y, -40, 2.5);
    box(f, [12, 19, 7], [side * 20, 100, -43], dark, "05-master-jaw-block");
    fingers.push({ group: f, pad, side });
  }
  blade(-1);
  blade(1);
  const pivotHardware = new T.Group();
  pivotHardware.name =
    variant === "b"
      ? "08B-SUPPORTED-ROTARY-CRADLE"
      : "08A-RIGID-CASSETTE-MOUNT";
  carriage.add(pivotHardware);
  for (const side of [-1, 1]) {
    if (variant === "b") {
      const bearing = ring(
        pivotHardware,
        11,
        5.15,
        10,
        0,
        dark,
        "08B-bearing-housing",
      );
      bearing.position.set(side * 50, 100, -80);
      bearing.rotation.y = Math.PI / 2;
      cyl(pickup, 5, 20, [side * 45, 100, -80], steel, "08B-stub-shaft", "x");
    } else
      box(
        pivotHardware,
        [10, 18, 25],
        [side * 45, 100, -80],
        dark,
        "08A-fixed-mounting-cheek",
      );
  }
  if (variant === "b") {
    cyl(
      pivotHardware,
      22,
      34,
      [76, 100, -80],
      black,
      "08B-geared-rotary-actuator-envelope",
      "x",
    );
    cyl(pivotHardware, 23, 10, [98, 100, -80], gold, "08B-brake-envelope", "x");
    for (const a of [-Math.PI / 2, 0])
      box(
        pivotHardware,
        [8, 10, 8],
        [-48, 100 + 19 * Math.sin(a), -80 + 19 * Math.cos(a)],
        teal,
        "08B-hard-stop",
      );
    box(pivotHardware, [7, 9, 12], [48, 100, -106], black, "08B-index-sensor");
  }
  const thumb = new T.Group();
  thumb.name = "08A-AUXILIARY-THUMB";
  carriage.add(thumb);
  thumb.visible = variant === "a";
  const thumbParts: T.Object3D[] = [];
  const tBase = cyl(thumb, 3.5, 8, [0, 33, 4], dark, "thumb-root-pivot", "x");
  thumbParts.push(tBase);
  const tElbow = cyl(thumb, 3, 8, [0, 0, 0], dark, "thumb-elbow-pivot", "x");
  const tEnd = mesh(
    thumb,
    new T.SphereGeometry(3, 24, 16),
    black,
    "thumb-contact-roller",
  );
  const link1 = beam(
    thumb,
    new T.Vector3(),
    new T.Vector3(0, 25, 0),
    2,
    teal,
    "thumb-link-25mm",
  );
  const link2 = beam(
    thumb,
    new T.Vector3(),
    new T.Vector3(0, 25, 0),
    1.5,
    steel,
    "thumb-link-25mm",
  );
  for (const x of [-12, 12])
    box(thumb, [20, 30, 35], [x, 145, -75], black, "08A-tendon-drive-envelope");
  beam(
    thumb,
    new T.Vector3(0, 135, -65),
    new T.Vector3(0, 62, -10),
    4,
    steel,
    "thumb-motor-bracket",
  );
  beam(
    thumb,
    new T.Vector3(0, 62, -10),
    new T.Vector3(0, 33, 4),
    3,
    steel,
    "thumb-bearing-bracket",
  );
  for (const x of [-3, 3])
    line(
      thumb,
      [
        new T.Vector3(x, 145, -65),
        new T.Vector3(x, 62, -10),
        new T.Vector3(x, 33, 4),
      ],
      "#566970",
      "tendon-routing-envelope",
    );
  const bolt = makeBolt(spec);
  bolt.scale.setScalar(1000);
  bolt.name = "WORKPIECE-HEX-BOLT";
  root.add(bolt);
  const bounds = new T.Group();
  bounds.name = "B-SWING-ENVELOPE";
  root.add(bounds);
  const arc: T.Vector3[] = [];
  for (let i = 0; i <= 90; i++) {
    const p = D.grasp
      .clone()
      .sub(D.pivot)
      .applyAxisAngle(new T.Vector3(1, 0, 0), ((-Math.PI / 2) * i) / 90)
      .add(D.pivot);
    arc.push(p);
  }
  line(bounds, arc, "#d57f4d", "supported-pick-point-sweep");
  bounds.visible = variant === "b";
  const labels = [
    { name: "01 · 체결 스핀들 설치 공간", point: new T.Vector3(0, -30, -220) },
    { name: "02 · 고정 높이의 내부 척", point: new T.Vector3(-40, -15, -15) },
    {
      name:
        variant === "a"
          ? "08A · 별도 2관절 엄지"
          : "08B · 지지 베어링 + 1축 회전",
      point:
        variant === "a" ? new T.Vector3(0, 33, 4) : new T.Vector3(98, 100, -80),
    },
    {
      name: "07 · 가이드·나사·수납 캐리지",
      point: new T.Vector3(-83, 75, -133),
    },
    { name: "06 · 일자 테이퍼 손가락", point: new T.Vector3(0, 65, -18) },
  ];
  function update(t: number, cutaway = false, explode = false) {
    const s = assemblyPose(t);
    for (const m of covers) {
      m.transparent = cutaway;
      m.opacity = cutaway ? 0.16 : 1;
      m.depthWrite = !cutaway;
    }
    pickup.matrixAutoUpdate = false;
    pickup.matrix.copy(gripTransform(variant, s));
    carriage.position.copy(D.retract).multiplyScalar(s.retract);
    if (explode) {
      pickup.matrix.premultiply(new T.Matrix4().makeTranslation(0, 100, 0));
      carriage.position.y += 100;
      rotor.position.z = 45;
    } else rotor.position.z = 0;
    for (const f of fingers) {
      f.group.position.x = f.side * jawHalfGap(s, spec.diameter * 1000);
      f.pad.rotation.x = variant === "a" ? (-Math.PI / 2) * (1 - s.align) : 0;
    }
    rotor.rotation.z = s.spin;
    driveShaft.rotation.y = s.spin;
    for (const j of jaws)
      j.position.x = D.openJaw + (spec.headWidth * 500 - D.openJaw) * s.clamp;
    clampRing.position.z = 19 * s.clamp;
    bolt.matrixAutoUpdate = false;
    bolt.matrix
      .copy(boltTransform(variant, s))
      .scale(new T.Vector3(1000, 1000, 1000));
    const rs = sampleCycle(10 + 4 * s.align, spec);
    rs.clear = 0;
    rs.align = s.align;
    rs.rodEngaged = ramp(t, 8, 15) * (1 - ramp(t, 72, 77));
    const tp = rodPose(rs, spec);
    const cv = (v: T.Vector3) =>
      v
        .clone()
        .sub(new T.Vector3(0, 0, 0.386))
        .multiplyScalar(1000);
    const a = cv(tp.base),
      b = cv(tp.elbow),
      c = cv(tp.tip);
    tElbow.position.copy(b);
    tEnd.position.copy(c);
    for (const [link, p, q] of [
      [link1, a, b],
      [link2, b, c],
    ] as const) {
      link.position.copy(p).add(q).multiplyScalar(0.5);
      link.quaternion.setFromUnitVectors(
        new T.Vector3(0, 1, 0),
        q.clone().sub(p).normalize(),
      );
    }
    bounds.visible = variant === "b" && !explode;
    root.updateMatrixWorld(true);
  }
  update(0);
  return { root, update, labels, meshes };
}
