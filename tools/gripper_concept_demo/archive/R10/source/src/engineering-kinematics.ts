import { Matrix4, Vector3 } from "three";
import type { Variant } from "./variants";
import { ramp } from "./timeline";

// Assembly coordinates are millimetres. +Z points from the tool into the work.
// The head underside and fixed chuck mouth share z=0. These are layout values,
// not released manufacturing dimensions or validated component ratings.
export const DESIGN = {
  grasp: new Vector3(0, 0, 14),
  pivot: new Vector3(0, 100, -80),
  retract: new Vector3(0, 60, -35),
  fingerRoot: new Vector3(0, 100, -35),
  tipWidth: 3,
  tipDepth: 4,
  chuckOuter: 52,
  chuckInner: 48,
  openJaw: 24,
  shaftDiameter: 16,
} as const;
export function assemblyPose(value: number) {
  const t = Math.max(0, Math.min(100, Number.isFinite(value) ? value : 0));
  return {
    t,
    grip: ramp(t, 0, 8),
    align: ramp(t, 15, 40),
    clamp: ramp(t, 42, 50),
    release: ramp(t, 52, 57),
    retract: ramp(t, 59, 72),
    spin: ramp(t, 78, 100) * Math.PI * 6,
    chuckAxial: 0,
  };
}
export type AssemblyPose = ReturnType<typeof assemblyPose>;
export function swingTransform(s: AssemblyPose) {
  const p = DESIGN.pivot;
  return new Matrix4()
    .makeTranslation(p.x, p.y, p.z)
    .multiply(new Matrix4().makeRotationX((-Math.PI / 2) * (1 - s.align)))
    .multiply(new Matrix4().makeTranslation(-p.x, -p.y, -p.z));
}
export function gripTransform(variant: Variant, s: AssemblyPose) {
  const r = DESIGN.retract.clone().multiplyScalar(s.retract);
  const m = new Matrix4().makeTranslation(r.x, r.y, r.z);
  if (variant === "b") m.multiply(swingTransform(s));
  return m;
}
export function boltTransform(variant: Variant, s: AssemblyPose) {
  // Bolt remains in the fixed head chuck while the pickup cassette retracts.
  if (variant === "b")
    return swingTransform(s).multiply(new Matrix4().makeRotationZ(s.spin));
  return new Matrix4()
    .makeTranslation(0, 0, 14)
    .multiply(new Matrix4().makeRotationX((-Math.PI / 2) * (1 - s.align)))
    .multiply(new Matrix4().makeTranslation(0, 0, -14))
    .multiply(new Matrix4().makeRotationZ(s.spin));
}
export function jawHalfGap(s: AssemblyPose, diameterMm: number) {
  return diameterMm / 2 + DESIGN.tipWidth / 2 + 7 * (1 - s.grip + s.release);
}
