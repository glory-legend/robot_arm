import { Matrix4, Vector3 } from "three";
import { ramp, type BoltSpec } from "./timeline";

// Millimetres; head underside = z0; +Z points towards the bolt tip.
export function integratedPose(value: number) {
  const t = Math.max(0, Math.min(100, Number.isFinite(value) ? value : 0));
  const feed = ramp(t, 36, 52),
    stow = ramp(t, 83, 92);
  return {
    t,
    grip: ramp(t, 0, 8),
    align: ramp(t, 16, 34),
    feed,
    clamp: ramp(t, 54, 60),
    thumbPark: ramp(t, 62, 68),
    release: ramp(t, 69, 72),
    fold: ramp(t, 73, 81),
    stow,
    spin: ramp(t, 94, 100) * Math.PI * 6,
    carriageZ: 50 * (1 - feed) - 70 * stow,
    chuckAxial: 0,
  };
}
export type IntegratedPose = ReturnType<typeof integratedPose>;
export function boltMatrix(s: IntegratedPose) {
  return new Matrix4()
    .makeTranslation(0, 0, 14 + 50 * (1 - s.feed))
    .multiply(new Matrix4().makeRotationX((-Math.PI / 2) * (1 - s.align)))
    .multiply(new Matrix4().makeTranslation(0, 0, -14))
    .multiply(new Matrix4().makeRotationZ(s.spin));
}
export function fingerGap(s: IntegratedPose, spec: BoltSpec) {
  return spec.diameter * 500 + 1.5 + 6 * (1 - s.grip + s.release);
}
export function fingerMatrix(s: IntegratedPose, spec: BoltSpec, side: number) {
  return new Matrix4()
    .makeTranslation(side * (38 + fingerGap(s, spec)), 0, s.carriageZ)
    .multiply(new Matrix4().makeRotationY(((side * Math.PI) / 2) * s.fold));
}
export function thumbPoints(s: IntegratedPose, spec: BoltSpec) {
  const base = new Vector3(-16, 38, s.carriageZ + 3);
  const park = base.clone().add(new Vector3(0, 14, 6));
  const a = (-Math.PI / 2) * (1 - s.align),
    r = spec.diameter * 500 + 2;
  const contact = new Vector3(0, 0, spec.length * 1000 - 2).applyMatrix4(
    boltMatrix(s),
  );
  contact.add(new Vector3(0, Math.cos(a) * r, Math.sin(a) * r));
  contact.x = -16; // Offset link plane; a lateral roller shaft reaches the bolt at x0.
  const engaged = ramp(s.t, 8, 14) * (1 - s.thumbPark);
  const tip = park.clone().lerp(contact, engaged);
  const delta = tip.clone().sub(base),
    d = delta.length();
  if (d > 76 || d < 0.01)
    throw new Error("R08 thumb target outside its physical reach");
  const h = Math.sqrt(38 ** 2 - (d / 2) ** 2);
  // Select the elbow toward the rear pocket (+Y), not through the spindle.
  const perpendicular = new Vector3(0, delta.z, -delta.y).normalize();
  const elbow = base
    .clone()
    .addScaledVector(delta, 0.5)
    .addScaledVector(perpendicular, h);
  return [base, elbow, tip] as const;
}
