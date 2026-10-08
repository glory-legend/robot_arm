import * as T from "three";
import { RoundedBoxGeometry } from "three/addons/geometries/RoundedBoxGeometry.js";
import { ColladaLoader } from "three/addons/loaders/ColladaLoader.js";
import { toCreasedNormals } from "three/addons/utils/BufferGeometryUtils.js";
import { ROBOT_DATA, originMatrix } from "./kinematics";
import type { BoltSpec } from "./timeline";

/**
 * Photoreal dressing for the showcase only; the simulator model is untouched.
 * Treats the R11 kinematic model as a built part: real finishes, broken edges,
 * fasteners, a connector and harness, threaded bolts and the FR3 wrist it mounts on.
 * Added hardware is illustrative: the actuators and connector are not selected parts.
 * Units: millimetres inside a gripper root, metres elsewhere.
 */
const CREASE = (35 * Math.PI) / 180;
const phys = (
  color: string,
  metalness: number,
  roughness: number,
  extra: T.MeshPhysicalMaterialParameters = {},
) => new T.MeshPhysicalMaterial({ color, metalness, roughness, ...extra });

/** One set per gripper, so fading one model never fades the other. */
export function finishes() {
  return {
    anodized: phys("#c8cdd0", 0.9, 0.56), // bead-blasted clear anodise
    machined: phys("#d2d7da", 1, 0.27),
    blackAnodized: phys("#25292c", 0.7, 0.4),
    motor: phys("#1d2124", 0.3, 0.48),
    steel: phys("#c5cacd", 1, 0.18),
    toolSteel: phys("#a6acb0", 1, 0.3),
    hardened: phys("#899095", 1, 0.25),
    blackOxide: phys("#2a2e31", 0.8, 0.42),
    bluedSpring: phys("#39485a", 1, 0.3),
    bronze: phys("#a87e50", 1, 0.32),
    spring: phys("#cfd4d7", 1, 0.13),
    rubber: phys("#1a1c1e", 0, 0.82),
    // No clearcoat anywhere: the path tracer renders clearcoated materials black.
    teal: phys("#2b6a6f", 0.75, 0.3),
    label: phys("#d8dcdf", 0.2, 0.45),
    wire: [
      phys("#a3302b", 0, 0.45),
      phys("#202326", 0, 0.45),
      phys("#d9d9d4", 0, 0.45),
      phys("#2f5f9e", 0, 0.45),
    ],
    cable: phys("#17191b", 0, 0.62),
  };
}
export type Finishes = ReturnType<typeof finishes>;
type Single = Exclude<keyof Finishes, "wire">;
const FINISH: [RegExp, Single][] = [
  [/^structural-guide-housing|^cover-sleeve/, "anodized"],
  [/^slim-nose-tube|^front-plate|^feed-yoke|^rear-|^tie-rod/, "machined"],
  [
    /^robot-adapter|^grip-slide|^slide-to-drive|^thumb-column|^tweezer-spread-cam/,
    "blackAnodized",
  ],
  [
    /^spindle-motor|^feed-ring-motor|^grip-drive|^thumb-drive|^chuck-closure/,
    "motor",
  ],
  [/^chuck-spring-pack/, "bluedSpring"],
  [
    /^chuck-release|^output-shaft|^thumb-joint|^thumb-base|^roller-shaft|^feed-screw/,
    "steel",
  ],
  [/^spindle-gearhead|^chuck-back-disc|^chuck-web/, "toolSteel"],
  [/^head-jaw/, "hardened"],
  [/^radial-slider|^cover-screw/, "blackOxide"],
  [/^feed-ring-nut|^feed-nut|^guide-bushing/, "bronze"],
  [/^tweezer-blade/, "spring"],
  [/^passive-pad|^bolt-roller/, "rubber"],
  [/^thumb-proximal|^thumb-distal/, "teal"],
];

/** Break every edge: 0.35 mm chamfers that keep the declared outline and length. */
function refine(g: T.BufferGeometry): T.BufferGeometry {
  if (g instanceof T.ExtrudeGeometry) {
    const { shapes, options } = g.parameters;
    const depth = options.depth ?? 1,
      b = Math.min(0.35, depth * 0.12);
    const out = new T.ExtrudeGeometry(shapes, {
      ...options,
      depth: depth - 2 * b,
      bevelEnabled: true,
      bevelThickness: b,
      bevelSize: b,
      bevelOffset: -b,
      bevelSegments: 2,
      curveSegments: Math.max(48, options.curveSegments ?? 12),
    });
    out.translate(0, 0, b);
    return toCreasedNormals(out, CREASE);
  }
  if (g instanceof T.BoxGeometry) {
    const { width, height, depth } = g.parameters;
    const r = Math.min(0.5, Math.min(width, height, depth) * 0.18);
    return new RoundedBoxGeometry(width, height, depth, 2, r);
  }
  if (g instanceof T.CylinderGeometry) {
    const { radiusTop: r, height: h, radialSegments } = g.parameters;
    return chamferedRod(r, h, Math.max(48, radialSegments));
  }
  return g;
}
function chamferedRod(r: number, h: number, segments = 48) {
  const c = Math.min(0.35, r * 0.2, h * 0.2);
  const pts = [
    [0, -h / 2],
    [r - c, -h / 2],
    [r, -h / 2 + c],
    [r, h / 2 - c],
    [r - c, h / 2],
    [0, h / 2],
  ].map(([x, y]) => new T.Vector2(x, y));
  return toCreasedNormals(new T.LatheGeometry(pts, segments), CREASE);
}

const mesh = (g: T.BufferGeometry, m: T.Material, name: string) => {
  const o = new T.Mesh(g, m);
  o.name = name;
  o.castShadow = o.receiveShadow = true;
  return o;
};
const Y = new T.Vector3(0, 1, 0);
/** Place a part built along +Y so that +Y points along `axis`, origin at `at`. */
function aim(o: T.Object3D, at: T.Vector3, axis: T.Vector3) {
  o.position.copy(at);
  o.quaternion.setFromUnitVectors(Y, axis.clone().normalize());
  return o;
}
function screw(f: Finishes, kind: "button" | "flat") {
  const g = new T.Group();
  const profile =
    kind === "button"
      ? [
          [0, 0],
          [2.2, 0],
          [2.2, 0.45],
          [2.05, 0.85],
          [1.7, 1.15],
          [1.05, 1.36],
          [0, 1.4],
        ]
      : [
          [0, -0.05],
          [2.35, -0.05],
          [2.35, 0.05],
          [0, 0.05],
        ];
  g.add(
    mesh(
      new T.LatheGeometry(
        profile.map(([x, y]) => new T.Vector2(x, y)),
        40,
      ),
      f.steel,
      `${kind}-screw`,
    ),
  );
  const socket = mesh(
    new T.CylinderGeometry(0.9, 0.9, 0.02, 6),
    f.blackOxide,
    "screw-socket",
  );
  socket.position.y = kind === "button" ? 1.405 : 0.06;
  g.add(socket);
  return g;
}

/** Laser-etched marking centred at `deg` on the tube: a colour map in the tube's own finish,
 * so raster and path tracer agree (no alpha). */
function marking(R: number, deg: number, z: number) {
  const c = document.createElement("canvas");
  c.width = 1024;
  c.height = 384;
  const x = c.getContext("2d")!;
  x.fillStyle = "#c8cdd0";
  x.fillRect(0, 0, c.width, c.height);
  x.fillStyle = "#3b4246";
  x.font = "600 210px 'R11 Figures', 'Arial Narrow', sans-serif";
  x.fillText("R11", 24, 214);
  x.font = "500 58px 'R11 Figures', 'Arial Narrow', sans-serif";
  x.fillText("BOLT PICK + FASTEN", 28, 298);
  x.fillText("PROTO-01  2026.10", 28, 362);
  x.fillRect(450, 40, 4, 180);
  for (let i = 0; i <= 10; i++)
    x.fillRect(480 + i * 50, 200, 3, i % 5 ? 20 : 40);
  const etch = new T.CanvasTexture(c);
  etch.anisotropy = 8;
  etch.colorSpace = T.SRGBColorSpace;
  const arc = 30 / R, // 30 mm of circumference
    height = 11.25;
  const patch = mesh(
    new T.CylinderGeometry(R + 0.02, R + 0.02, height, 48, 1, true, 0, arc),
    new T.MeshPhysicalMaterial({
      map: etch,
      metalness: 0.9,
      roughness: 0.56,
      polygonOffset: true,
      polygonOffsetFactor: -2,
    }),
    "laser-marking",
  );
  patch.castShadow = false;
  // -90 deg about X: the cylinder axis becomes the tool axis with the text top towards the flange;
  // the patch then spans angles 90 deg - arc .. 90 deg, so turn it to centre on `deg`.
  patch.rotation.x = -Math.PI / 2;
  const turn = new T.Group();
  turn.rotation.z = ((deg - 90) * Math.PI) / 180 + arc / 2;
  turn.position.z = z;
  turn.add(patch);
  return turn;
}

/**
 * Dress a makeCompactGripper() root in place. With `hardware`, also add fasteners, an
 * M8 right-angle connector with its harness, internal motor leads, a motor label band
 * and the laser marking (R11 geometry). Returns the external cable so the caller can
 * hide it when the tool is shown detached from the robot.
 */
export function realize(
  root: T.Object3D,
  f: Finishes,
  body?: { width: number; length: number; nose: number },
) {
  root.traverse((o) => {
    if (!(o instanceof T.Mesh)) return;
    const g = refine(o.geometry);
    if (g !== o.geometry) {
      o.geometry.dispose();
      o.geometry = g;
    }
    const hit = FINISH.find(([re]) => re.test(o.name));
    if (hit) o.material = f[hit[1]];
  });
  if (!body) return null;
  const frame = root.getObjectByName("frame")!;
  const R = body.width / 2,
    L = body.length,
    F = -body.nose;
  const radial = (deg: number, r: number, z: number) => {
    const a = (deg * Math.PI) / 180;
    return new T.Vector3(r * Math.cos(a), r * Math.sin(a), z);
  };
  const out = (deg: number) => radial(deg, 1, 0);
  // Six button-head screws into the adapter spigot, three flat heads into the guide ribs.
  for (let k = 0; k < 6; k++)
    frame.add(
      aim(screw(f, "button"), radial(k * 60, R - 0.1, -L + 9), out(k * 60)),
    );
  for (const deg of [60, 240, 300])
    frame.add(
      aim(screw(f, "flat"), radial(deg, 26, F), new T.Vector3(0, 0, 1)),
    );
  // Motor label band, visible through the x-ray housing.
  const band = mesh(chamferedRod(12.12, 9, 64), f.label, "motor-label-band");
  band.rotation.x = Math.PI / 2;
  band.position.z = -62;
  frame.add(band, marking(R, 45, -46));

  // M8 4-pin right-angle connector at 150 deg, beside the feed ring motor where the tube is
  // clear between r 22 and the wall; the cable leaves towards the robot.
  const C = 150,
    zc = -L + 10;
  const conn = new T.Group();
  conn.name = "m8-connector";
  aim(conn, radial(C, R, zc), out(C)); // a turn about the tool axis: local z stays tool z
  const part = (
    g: T.BufferGeometry,
    m: T.Material,
    y: number,
    name: string,
  ) => {
    const o = mesh(g, m, name);
    o.position.y = y;
    conn.add(o);
    return o;
  };
  part(chamferedRod(5.1, 1.6, 6), f.steel, 0.8, "connector-flange-nut");
  part(chamferedRod(4, 3, 40), f.steel, 3, "connector-receptacle");
  part(chamferedRod(4.9, 7, 56), f.toolSteel, 7.6, "connector-coupling-nut");
  for (let i = 0; i < 5; i++)
    part(
      chamferedRod(5.0, 0.35, 56),
      f.steel,
      4.8 + i * 1.3,
      "connector-knurl",
    );
  part(
    new RoundedBoxGeometry(9, 8, 9, 3, 2.2),
    f.motor,
    14.5,
    "connector-right-angle",
  ).position.z = -2.5;
  frame.add(conn);
  conn.updateMatrix();
  const exit = new T.Vector3(0, 14.5, -7).applyMatrix4(conn.matrix);
  const relief = mesh(
    new T.LatheGeometry(
      [
        [0, 0],
        [3.6, 0],
        [3.3, 3],
        [2.7, 9],
        [0, 9],
      ].map(([x, y]) => new T.Vector2(x, y)),
      32,
    ),
    f.rubber,
    "cable-strain-relief",
  );
  frame.add(aim(relief, exit, new T.Vector3(0, 0, -1)));
  // The harness runs up the tube, past the adapter and on along the arm.
  const along = (r: number, z: number) => radial(C, r, z);
  const path = new T.CatmullRomCurve3([
    exit.clone().add(new T.Vector3(0, 0, -8)),
    along(R + 15, zc - 18),
    along(R + 17, -L - 20),
    along(R + 26, -L - 70),
    along(R + 44, -L - 150),
    along(R + 60, -L - 260),
  ]);
  const cable = mesh(
    new T.TubeGeometry(path, 160, 2.3, 16),
    f.cable,
    "harness-cable",
  );
  for (const u of [0.3, 0.52]) {
    const tie = mesh(
      new T.TorusGeometry(2.9, 0.55, 8, 24),
      f.motor,
      "cable-tie",
    );
    tie.position.copy(path.getPointAt(u));
    tie.quaternion.setFromUnitVectors(
      new T.Vector3(0, 0, 1),
      path.getTangentAt(u),
    );
    cable.add(tie);
  }
  frame.add(cable);
  // Feed ring motor leads to the receptacle, inside the tube (seen in the x-ray views).
  const inside = radial(C, R - 3, zc);
  f.wire.slice(0, 3).forEach((m, i) => {
    const o = new T.Vector3(0, 0, (i - 1) * 1.1);
    const curve = new T.CatmullRomCurve3([
      radial(C - 28, 22.3, zc).add(o),
      radial(C - 12, 24.5, zc).add(o),
      inside.clone().add(o),
    ]);
    frame.add(mesh(new T.TubeGeometry(curve, 32, 0.4, 8), m, "motor-lead"));
  });
  return cable;
}

/** Hex bolt with a modelled 60-degree thread, in the same metre frame as makeBolt(). */
export function makeRealBolt(
  spec: BoltSpec,
  m: T.Material,
  detail: 0 | 1 | 2 = 2,
) {
  const outer = new T.Group(),
    g = new T.Group();
  outer.name = "bolt";
  g.scale.setScalar(0.001);
  outer.add(g);
  const H = spec.headHeight * 1000,
    Lb = spec.length * 1000,
    P = spec.pitch * 1000,
    rMaj = spec.diameter * 500;
  const hex = new T.Shape(),
    rh = (spec.headWidth * 1000) / Math.sqrt(3);
  for (let k = 0; k < 6; k++) {
    const a = ((30 + 60 * k) * Math.PI) / 180;
    if (k) hex.lineTo(rh * Math.cos(a), rh * Math.sin(a));
    else hex.moveTo(rh * Math.cos(a), rh * Math.sin(a));
  }
  const b = 0.25;
  const head = new T.ExtrudeGeometry(hex, {
    depth: H - 2 * b,
    bevelEnabled: true,
    bevelThickness: b,
    bevelSize: 0.45,
    bevelOffset: -0.45,
    bevelSegments: 1,
  });
  head.translate(0, 0, -H + b);
  g.add(mesh(toCreasedNormals(head, CREASE), m, "bolt-head"));
  const washer = mesh(
    chamferedRod(spec.headWidth * 470, 0.35, 48),
    m,
    "bolt-washer-face",
  );
  washer.rotation.x = Math.PI / 2;
  washer.position.z = 0.17;
  g.add(washer);
  if (detail === 0) {
    const shank = mesh(chamferedRod(rMaj * 0.97, Lb, 32), m, "bolt-shank");
    shank.rotation.x = Math.PI / 2;
    shank.position.z = Lb / 2;
    g.add(shank);
    return outer;
  }
  g.add(
    mesh(
      thread(rMaj, P, Lb, detail === 2 ? 16 : 9, detail === 2 ? 48 : 28),
      m,
      "bolt-thread",
    ),
  );
  return outer;
}
function thread(
  rMaj: number,
  pitch: number,
  length: number,
  perTurn: number,
  around: number,
) {
  const depth = 0.6134 * pitch * 0.85,
    rMin = rMaj - depth;
  const rows = Math.ceil((length / pitch) * perTurn);
  const pos: number[] = [],
    idx: number[] = [];
  for (let i = 0; i <= rows; i++) {
    const z = (i / rows) * length;
    const point = Math.min(1, (length - z) / (pitch * 0.9));
    for (let j = 0; j <= around; j++) {
      const th = (j / around) * Math.PI * 2;
      const u = (((z / pitch - j / around) % 1) + 1) % 1;
      const crest = Math.min(1, (1 - Math.abs(2 * u - 1)) * 1.35);
      const r = Math.min(
        rMin + depth * crest,
        rMin - 0.3 + (depth + 0.3) * point,
      );
      pos.push(r * Math.cos(th), r * Math.sin(th), z);
    }
  }
  for (let i = 0; i < rows; i++)
    for (let j = 0; j < around; j++) {
      const a = i * (around + 1) + j,
        c = a + around + 1;
      idx.push(a, a + 1, c + 1, a, c + 1, c);
    }
  const tip = pos.length / 3;
  pos.push(0, 0, length);
  const last = rows * (around + 1);
  for (let j = 0; j < around; j++) idx.push(tip, last + j, last + j + 1);
  const g = new T.BufferGeometry();
  g.setAttribute("position", new T.Float32BufferAttribute(pos, 3));
  g.setIndex(idx);
  g.computeVertexNormals();
  return g;
}

/** FR3 links 6 and 7, placed in the flange frame (metres) so the tool hangs from the real wrist. */
export async function loadWrist(q6: number) {
  T.Cache.enabled = true; // the cell viewer later reuses the same files
  const loader = new ColladaLoader();
  const base = import.meta.env.BASE_URL;
  const [l6, l7] = await Promise.all(
    [6, 7].map((i) => loader.loadAsync(`${base}fr3/link${i}.dae`)),
  );
  const paint = phys("#eceef0", 0, 0.24);
  const black = phys("#1b1e21", 0, 0.42);
  const j6 = originMatrix(ROBOT_DATA[7]).invert();
  const j5 = j6
    .clone()
    .multiply(new T.Matrix4().makeRotationZ(-q6))
    .multiply(originMatrix(ROBOT_DATA[6]).invert());
  const wrist = new T.Group();
  wrist.name = "fr3-wrist";
  for (const [asset, frame, spin] of [
    [l6, j5, 0],
    [l7, j6, Math.PI / 4],
  ] as const) {
    if (!asset) throw new Error("FR3 wrist link could not be parsed");
    // ColladaLoader turns Z_UP files to Y_UP; this scene stays Z_UP like the cell viewer.
    asset.scene.rotation.set(0, 0, spin);
    const holder = new T.Group();
    holder.matrixAutoUpdate = false;
    holder.matrix.copy(frame);
    holder.add(asset.scene);
    asset.scene.traverse((o) => {
      if (!(o instanceof T.Mesh)) return;
      const mats = Array.isArray(o.material) ? o.material : [o.material];
      const dark = mats.some(
        (m) =>
          "color" in m &&
          (m as T.MeshPhongMaterial).color.getHSL({ h: 0, s: 0, l: 0 }).l <
            0.25,
      );
      o.material = dark ? black : paint;
      o.castShadow = o.receiveShadow = true;
    });
    wrist.add(holder);
  }
  return wrist;
}
