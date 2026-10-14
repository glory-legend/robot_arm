import * as T from "three";
import type { BoltSpec } from "./timeline";
import {
  CHUCK,
  NOSE,
  THUMB,
  TWEEZER,
  compactPose,
  designOf,
  thumbPose,
  tweezerPoints,
  type DesignId,
} from "./compact-kinematics";

/**
 * R09 compact assembly. Every moving part hangs off the part that carries it:
 * frame -> spindle -> rotor -> jaws, frame -> guides -> yoke -> slide -> tweezer blade -> pad,
 * yoke -> thumb column -> link1 -> link2 -> roller. Model units are mm; `root` converts to metres.
 */
export function makeCompactGripper(
  initial?: BoltSpec,
  design: DesignId = "r09",
) {
  const D = designOf(design),
    BODY = D.body,
    YOKE_Z = D.yokeZ;
  const root = new T.Group();
  root.name = `${design.toUpperCase()}-COMPACT-GRIPPER`;
  root.position.z = BODY.length / 1000;
  root.scale.setScalar(0.001);
  const colors = { blue: "#286ca8", orange: "#bb591f" };
  const mat = (c: string, metalness = 0.55) =>
    new T.MeshStandardMaterial({ color: c, metalness, roughness: 0.36 });
  const alu = mat("#b9c6cc"),
    dark = mat("#2b3b44", 0.3),
    drive = mat("#28747a", 0.35),
    gold = mat(colors.orange, 0.5),
    springSteel = mat("#56656e", 0.8),
    rubber = mat("#182a31", 0.1),
    thumbMat = mat("#397f8b", 0.35),
    coverMat = mat("#d3dcdb", 0.25);
  const translucent = [coverMat];

  function add(
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
  const box = (
    p: T.Object3D,
    s: number[],
    pos: number[],
    m: T.Material,
    n: string,
  ) => add(p, new T.BoxGeometry(s[0], s[1], s[2]), m, n, pos);
  function cyl(
    p: T.Object3D,
    r: number,
    l: number,
    pos: number[],
    m: T.Material,
    n: string,
    axis = "z",
    seg = 32,
  ) {
    const o = add(p, new T.CylinderGeometry(r, r, l, seg), m, n, pos);
    if (axis === "z") o.rotation.x = Math.PI / 2;
    if (axis === "x") o.rotation.z = Math.PI / 2;
    return o;
  }
  /**
   * Flat strip swept through points in the x-z plane: half width w along y, half thickness t
   * across the path. Used for the tweezer blades.
   */
  function strip(pts: T.Vector3[], w: number[], t: number[]) {
    const v: number[] = [],
      idx: number[] = [];
    pts.forEach((p, i) => {
      const a = pts[Math.max(0, i - 1)],
        b = pts[Math.min(pts.length - 1, i + 1)];
      const d = b.clone().sub(a).normalize();
      const n = new T.Vector3(d.z, 0, -d.x);
      for (const [u, k] of [
        [-1, -1],
        [1, -1],
        [1, 1],
        [-1, 1],
      ])
        v.push(
          ...p
            .clone()
            .add(new T.Vector3(0, u * w[i], 0))
            .addScaledVector(n, k * t[i])
            .toArray(),
        );
    });
    for (let i = 0; i < pts.length - 1; i++)
      for (let k = 0; k < 4; k++) {
        const a = i * 4 + k,
          b = i * 4 + ((k + 1) % 4),
          c = a + 4,
          d = b + 4;
        idx.push(a, b, d, a, d, c);
      }
    const last = (pts.length - 1) * 4;
    idx.push(
      0,
      2,
      1,
      0,
      3,
      2,
      last,
      last + 1,
      last + 2,
      last,
      last + 2,
      last + 3,
    );
    const g = new T.BufferGeometry();
    g.setAttribute("position", new T.Float32BufferAttribute(v, 3));
    g.setIndex(idx);
    g.computeVertexNormals();
    return g;
  }
  function rounded(w: number, h: number, r: number) {
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
  const circle = (x: number, y: number, r: number) => {
    const h = new T.Path();
    h.absarc(x, y, r, 0, Math.PI * 2, true);
    return h;
  };
  const rect = (x0: number, x1: number, y0: number, y1: number) => {
    const h = new T.Path();
    h.moveTo(x0, y0);
    h.lineTo(x0, y1);
    h.lineTo(x1, y1);
    h.lineTo(x1, y0);
    h.closePath();
    return h;
  };
  const plate = (
    p: T.Object3D,
    s: T.Shape,
    z0: number,
    depth: number,
    m: T.Material,
    n: string,
  ) =>
    add(
      p,
      new T.ExtrudeGeometry(s, {
        depth,
        bevelEnabled: false,
        curveSegments: 24,
      }),
      m,
      n,
      [0, 0, z0],
    );
  const ring = (
    p: T.Object3D,
    ro: number,
    ri: number,
    z0: number,
    depth: number,
    m: T.Material,
    n: string,
  ) => {
    const s = new T.Shape();
    s.absarc(0, 0, ro, 0, Math.PI * 2, false);
    s.holes.push(circle(0, 0, ri));
    return plate(p, s, z0, depth, m, n);
  };

  const W = BODY.width,
    H = BODY.height,
    L = BODY.length,
    F = -D.nose, // body front face
    back = YOKE_Z[0] - D.stow, // stowed yoke rear face = motor plate front
    round = D.shape === "cyl",
    R = W / 2;
  // Cross-section outline, optionally inset (cover wall, internal plates).
  const outline = (inset = 0) => {
    if (round) {
      const c = new T.Shape();
      c.absarc(0, 0, R - inset, 0, Math.PI * 2, false);
      return c;
    }
    if (D.shape === "oct") {
      const w = W / 2 - inset,
        h = H / 2 - inset,
        c = 10 - inset * 0.41;
      const o = new T.Shape();
      o.moveTo(-w + c, -h);
      for (const [x, y] of [
        [w - c, -h],
        [w, -h + c],
        [w, h - c],
        [w - c, h],
        [-w + c, h],
        [-w, h - c],
        [-w, -h + c],
      ])
        o.lineTo(x, y);
      o.closePath();
      return o;
    }
    return rounded(W - 2 * inset, H - 2 * inset, 9 - inset);
  };
  const rods: number[][] = round
    ? [60, 240, 300].map((a) => [
        25 * Math.cos((a * Math.PI) / 180),
        25 * Math.sin((a * Math.PI) / 180),
      ])
    : D.shape === "oct"
      ? [
          [-24, -20.5],
          [-24, 20.5],
          [24, -20.5],
          [24, 20.5],
        ]
      : [
          [-25.5, -22],
          [-25.5, 22],
          [25.5, -22],
          [25.5, 22],
        ];
  const thumbCol = round ? [-14.5, 20.5, 6] : [-18, THUMB.base.y, 8]; // x, y, drive size // body front face
  const frame = new T.Group(),
    shell = new T.Group(),
    rotor = new T.Group(),
    carriage = new T.Group();
  frame.name = "frame";
  shell.name = "removable-cover";
  rotor.name = "fixed-axial-chuck-rotor";
  carriage.name = "feed-carriage";
  root.add(frame, shell, rotor, carriage);

  // ---- Frame: nose tube, front plate with working ports, rear plates, tie rods.
  ring(
    frame,
    NOSE.radius,
    CHUCK.radius + 0.2,
    F,
    D.nose - 0.5,
    alu,
    "slim-nose-tube",
  );
  const front = outline();
  front.holes.push(circle(0, 0, CHUCK.radius + 0.2));
  for (const s of [-1, 1])
    front.holes.push(
      rect(s < 0 ? -28.6 : 14.9, s < 0 ? -14.9 : 28.6, -2.4, 2.4),
    );
  if (round) {
    // Stepped thumb port that stays inside the round face.
    const port = new T.Path();
    port.moveTo(-17.5, 16.5);
    for (const [x, y] of [
      [-17.5, 24.6],
      [-11.5, 24.6],
      [-11.5, 26.4],
      [4, 26.4],
      [4, 16.5],
    ])
      port.lineTo(x, y);
    port.closePath();
    front.holes.push(port);
  } else front.holes.push(rect(-22.5, 4, 16.5, 27));
  plate(frame, front, F - 3, 3, alu, "front-plate-with-ports");
  if (!round) plate(frame, outline(1.2), back - 4, 4, alu, "rear-motor-plate");
  plate(frame, outline(), back - 19, 3, alu, "rear-bulkhead");
  const rodLen = F - 3 - (back - 16);
  for (const [x, y] of rods)
    cyl(frame, 2.5, rodLen, [x, y, back - 16 + rodLen / 2], alu, "tie-rod");
  // FR3 adapter (ISO 50 bolt circle); motor drivers sit in the robot cabinet, not in the tool.
  ring(frame, 28, 10, -L, 6, dark, "robot-adapter-ring");
  // Fastening axis: motor + gearhead, then the chuck-closing element around the gearhead.
  const motorRear = round ? back - 16 : back;
  cyl(
    frame,
    12,
    -36 - motorRear,
    [0, 0, (motorRear - 36) / 2],
    drive,
    "spindle-motor-envelope",
  );
  cyl(frame, 12, 16, [0, 0, -28], dark, "spindle-gearhead-envelope");
  if (D.cam) {
    // Spring-closed chuck: belleville pack + three release rods pushed by the yoke over-travel.
    ring(frame, CHUCK.radius, 12, -23, 6, gold, "chuck-spring-pack");
    for (const a of [90, 210, 330]) {
      const r = (a * Math.PI) / 180;
      cyl(
        frame,
        0.8,
        43,
        [13.1 * Math.cos(r), 13.1 * Math.sin(r), -38.5],
        alu,
        "chuck-release-rod",
      );
    }
    // Fixed cam rails spread the tweezer slides in the first 0.6 mm of the stow stroke.
    for (const s of [-1, 1])
      box(
        frame,
        [0.8, 4, 15],
        [s * 29, 0, F - 10.5],
        dark,
        "tweezer-spread-cam",
      );
  } else ring(frame, CHUCK.radius, 12, -23, 6, drive, "chuck-closure-actuator");
  if (round) {
    // Coaxial feed: a ring motor turns a threaded sleeve around the spindle; the yoke carries the nut.
    ring(
      frame,
      15.5,
      14,
      back - 16,
      F - 3 - 1 - (back - 16),
      alu,
      "feed-screw-sleeve",
    );
    ring(frame, 22, 15.7, back - 16, 10, drive, "feed-ring-motor");
  } else {
    for (const x of [-16, 16])
      cyl(
        frame,
        3,
        F - 3 - back,
        [x, -21, (F - 3 + back) / 2],
        alu,
        "carriage-guide-rod",
      );
    cyl(
      frame,
      2.5,
      F - 3 - back,
      [0, -21, (F - 3 + back) / 2],
      alu,
      "feed-screw",
    );
    cyl(frame, 5, 12, [0, -21, back - 10], drive, "feed-motor-envelope");
  }

  // ---- Cover sleeve (service/transparency only, not structural).
  const sleeve = outline();
  sleeve.holes.push(new T.Path(outline(1.2).getPoints(24).reverse()));
  plate(
    shell,
    sleeve,
    back - 16,
    F - 3 - (back - 16),
    coverMat,
    "cover-sleeve",
  );
  for (const x of [-22, 22])
    for (const z of [F - 10, back - 10])
      cyl(
        shell,
        1.4,
        1,
        [x, (round ? Math.sqrt(R * R - x * x) : H / 2) + 0.5, z],
        rubber,
        "cover-screw",
        "y",
      );

  // ---- Rotor: output shaft, back disc, six webs between radial slots, six jaws on sliders.
  cyl(rotor, 4, 5, [0, 0, -17.5], alu, "output-shaft");
  ring(rotor, CHUCK.radius, 0.01, -CHUCK.depth, 3, gold, "chuck-back-disc");
  for (let i = 0; i < 6; i++) {
    const a = (i * Math.PI) / 3 + Math.PI / 6 - 0.34,
      b = (i * Math.PI) / 3 + Math.PI / 6 + 0.34;
    const s = new T.Shape();
    s.absarc(0, 0, CHUCK.radius, a, b, false);
    s.lineTo(10.3 * Math.cos(b), 10.3 * Math.sin(b));
    s.absarc(0, 0, 10.3, b, a, true);
    s.closePath();
    plate(rotor, s, -12, 11, gold, `chuck-web-${i}`);
  }
  const jaws: T.Group[] = [];
  for (let i = 0; i < 6; i++) {
    const g = new T.Group();
    g.rotation.z = (i * Math.PI) / 3;
    const slider = new T.Group();
    g.add(slider);
    box(slider, [3.6, 3.2, 5], [0, 0, -4], alu, `head-jaw-${i + 1}`);
    box(slider, [4, 2.6, 5.5], [0.3, 0, -9.25], dark, `radial-slider-${i + 1}`);
    rotor.add(g);
    jaws.push(slider);
  }

  // ---- Carriage: yoke, feed nut, two tweezer slides, thumb column.
  const yoke = round
    ? outline(1.4)
    : D.shape === "oct"
      ? outline(1.5)
      : rounded(58, 54, 8);
  yoke.holes.push(circle(0, 0, round ? 18.5 : CHUCK.radius + 1.5));
  if (!round) {
    for (const x of [-16, 16]) yoke.holes.push(circle(x, -21, 3.2));
    yoke.holes.push(circle(0, -21, 2.8));
  }
  for (const [x, y] of rods) yoke.holes.push(circle(x, y, 3));
  const slotEnd = D.cam ? 29.4 : 28.8,
    slotStart = round ? 18.6 : 15.6;
  for (const s of [-1, 1])
    yoke.holes.push(
      rect(
        s < 0 ? -slotEnd : slotStart,
        s < 0 ? -slotStart : slotEnd,
        -3.2,
        3.2,
      ),
    );
  plate(carriage, yoke, YOKE_Z[0], YOKE_Z[1] - YOKE_Z[0], alu, "feed-yoke");
  if (round)
    ring(
      carriage,
      18.5,
      15.6,
      YOKE_Z[0],
      YOKE_Z[1] - YOKE_Z[0],
      gold,
      "feed-ring-nut",
    );
  else {
    for (const x of [-16, 16])
      ring(
        carriage,
        5.5,
        3.05,
        YOKE_Z[0],
        7,
        gold,
        "guide-bushing",
      ).position.set(x, -21, YOKE_Z[0]);
    box(carriage, [12, 9, 7], [0, -21, YOKE_Z[0] + 3.5], gold, "feed-nut");
  }

  const yokeMid = (YOKE_Z[0] + YOKE_Z[1]) / 2;
  const blades = [-1, 1].map((side) => {
    box(
      carriage,
      [10, 6, 6],
      [side * 21, -8, yokeMid],
      drive,
      "grip-drive-envelope",
    );
    const slide = new T.Group();
    slide.name = `tweezer-slide-${side}`;
    carriage.add(slide);
    box(slide, [3, 6, 6], [0, 0, yokeMid], dark, "grip-slide-block");
    box(slide, [3, 3, 4], [0, -4.5, yokeMid], dark, "slide-to-drive-link");
    // Flat spring blade: shank -> knee -> converging taper -> flat parallel jaw.
    const pts = [
      new T.Vector3(0, 0, YOKE_Z[1]),
      new T.Vector3(0, 0, TWEEZER.knee),
      new T.Vector3(-side * TWEEZER.lx, 0, 14 - TWEEZER.flat),
      new T.Vector3(-side * TWEEZER.lx, 0, 14 + TWEEZER.overrun),
    ];
    const tw = TWEEZER;
    add(
      slide,
      strip(
        pts,
        [tw.width, tw.width, (tw.width + tw.tipWidth) / 2, tw.tipWidth],
        [tw.thick, tw.thick, (tw.thick + tw.tipThick) / 2, tw.tipThick],
      ),
      springSteel,
      "tweezer-blade",
    );
    const pad = new T.Group();
    pad.position.set(-side * (TWEEZER.lx + TWEEZER.tipThick + 0.25), 0, 14);
    slide.add(pad);
    cyl(pad, 1, 0.5, [0, 0, 0], rubber, "passive-pad", "x", 16);
    return { side, slide, pad };
  });

  const thumbColumn = THUMB.base.z - 3 - YOKE_Z[1];
  const [tx, ty, td] = thumbCol;
  box(
    carriage,
    [td, td, 14],
    [tx, ty, YOKE_Z[1] + 7],
    drive,
    "thumb-drive-envelope",
  );
  box(
    carriage,
    [6, 6, thumbColumn],
    [tx, ty, YOKE_Z[1] + thumbColumn / 2],
    dark,
    "thumb-column",
  );
  const axleLen = THUMB.base.x + 3 - (tx - 3);
  cyl(
    carriage,
    3,
    axleLen,
    [(tx - 3 + THUMB.base.x + 3) / 2, THUMB.base.y, THUMB.base.z],
    alu,
    "thumb-base-axle",
    "x",
  );
  const link1 = new T.Group(),
    link2 = new T.Group();
  link1.position.copy(THUMB.base);
  carriage.add(link1);
  link2.position.z = THUMB.links[0];
  link1.add(link2);
  cyl(link1, 3.5, 6, [0, 0, 0], alu, "thumb-joint-1", "x");
  cyl(
    link1,
    2.2,
    THUMB.links[0],
    [0, 0, THUMB.links[0] / 2],
    thumbMat,
    "thumb-proximal",
  );
  cyl(link2, 3, 6, [0, 0, 0], alu, "thumb-joint-2", "x");
  cyl(
    link2,
    1.8,
    THUMB.links[1],
    [0, 0, THUMB.links[1] / 2],
    thumbMat,
    "thumb-distal",
  );
  cyl(
    link2,
    1.2,
    -THUMB.base.x,
    [-THUMB.base.x / 2, 0, THUMB.links[1]],
    alu,
    "roller-shaft",
    "x",
  );
  cyl(
    link2,
    2,
    6,
    [-THUMB.base.x, 0, THUMB.links[1]],
    rubber,
    "bolt-roller",
    "x",
    20,
  );

  const labelAnchors = [
    {
      name: "핀셋 날 · 평평한 끝",
      position: new T.Vector3(),
      color: colors.blue,
    },
    {
      name: `보조 엄지 · ${THUMB.links.join("+")}mm`,
      position: new T.Vector3(),
      color: "#397f8b",
    },
    {
      name: `가는 노즈 · Ø${NOSE.radius * 2}`,
      position: new T.Vector3(),
      color: colors.orange,
    },
  ];
  // Points along the link direction: rotation.x = atan2(-dy, dz) maps local +Z onto (dy, dz).
  const aim = (from: T.Vector3, to: T.Vector3) =>
    Math.atan2(-(to.y - from.y), to.z - from.z);

  function update(
    s: { time: number },
    spec: BoltSpec,
    transparent = false,
    exploded = false,
  ) {
    const p = compactPose(s.time, spec, design);
    for (const m of translucent) {
      // Toggling `transparent` changes the shader (OPAQUE define), so it must recompile.
      if (m.transparent !== transparent) m.needsUpdate = true;
      m.transparent = transparent;
      m.opacity = transparent ? 0.14 : 1;
      m.depthWrite = !transparent;
    }
    shell.visible = !exploded;
    carriage.position.z = p.carriageZ;
    rotor.rotation.z = p.spin;
    const closed = spec.headWidth * 500 + 1.8;
    for (const j of jaws)
      j.position.x = CHUCK.jawOpen + (closed - CHUCK.jawOpen) * p.clamp;
    for (const f of blades) {
      f.slide.position.x = f.side * (p.gap + TWEEZER.lx);
      f.pad.rotation.x = (-Math.PI / 2) * (1 - p.align);
    }
    const th = thumbPose(p, spec);
    const rel = new T.Vector3(0, 0, -p.carriageZ);
    const base = th.base.clone().add(rel),
      elbow = th.elbow.clone().add(rel),
      tip = th.tip.clone().add(rel);
    link1.rotation.x = aim(base, elbow);
    link2.rotation.x = aim(elbow, tip) - link1.rotation.x;
    labelAnchors[0].position.copy(tweezerPoints(p, -1, design).tip);
    labelAnchors[1].position.copy(th.elbow);
    labelAnchors[2].position.set(0, -NOSE.radius, -6);
    root.updateMatrixWorld(true);
  }
  async function load() {}
  if (initial) update({ time: 0 }, initial);
  return {
    root,
    load,
    update,
    labelAnchors,
    parts: { frame, rotor, carriage, shell },
  };
}
