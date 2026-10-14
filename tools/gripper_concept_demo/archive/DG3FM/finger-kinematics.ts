import { Matrix4, Vector3, Quaternion } from "three";
import type { BoltSpec, CycleState } from "./timeline";
import data from "./dg3fm-data.json";
import motion from "./finger-motion.json";
export const HAND_DATA = data;
export const TIP_LENGTH = 0.018;
export const PAD_RADIUS = 0.003;
export function palmDrawMatrix(curl: number, spin = 0) {
  return new Matrix4()
    .makeTranslation(0.003 * Math.sin(Math.PI * curl), 0, 0.2 - 0.03 * curl)
    .multiply(new Matrix4().makeRotationY(0.48 * (1 - curl)))
    .multiply(new Matrix4().makeRotationZ(spin));
}
export function fingerAngles(index: number, spec: BoltSpec, time: number) {
  const frames = motion[spec.id],
    v = Math.max(0, Math.min(36, time)) * 10;
  const a = Math.floor(v),
    b = Math.min(360, a + 1),
    f = v - a;
  return frames[a]
    .slice(index * 4, index * 4 + 4)
    .map((q, j) => q + (frames[b][index * 4 + j] - q) * f);
}
/** Exact upstream joint frames; only the replaceable contact tip is customized. */
export function fingerPose(index: number, spec: BoltSpec, state: CycleState) {
  const angles = fingerAngles(index, spec, state.time),
    m = new Matrix4().makeTranslation(0, 0, 0.004),
    points: Vector3[] = [];
  const joints = data.joints.filter((j) =>
    j.name.startsWith(`j_dg_${index + 1}_`),
  );
  for (const j of joints) {
    m.multiply(
      new Matrix4().makeTranslation(...(j.xyz as [number, number, number])),
    );
    if (j.axis) {
      const q = angles[Number(j.name.at(-1)) - 1];
      m.multiply(
        new Matrix4().makeRotationFromQuaternion(
          new Quaternion().setFromAxisAngle(
            new Vector3(...(j.axis as [number, number, number])),
            q,
          ),
        ),
      );
    }
    points.push(new Vector3().setFromMatrixPosition(m));
  }
  const tip = new Vector3(
    (index === 0 ? 1 : -1) * TIP_LENGTH,
    0,
    0,
  ).applyMatrix4(m);
  return { root: points[0], points, tip, angles };
}
