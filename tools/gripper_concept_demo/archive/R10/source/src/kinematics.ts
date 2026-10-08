import { Matrix4, Euler, Vector3 } from "three";
import data from "./robot-data.json";
import paths from "./motion-data.json";
import type { BoltSpec } from "./timeline";
import { boltLocalMatrix } from "./rod-kinematics";
import { sampleCycle } from "./timeline";
export const ROBOT_DATA = data;
export function originMatrix(j: (typeof data)[number]) {
  return new Matrix4()
    .makeRotationFromEuler(new Euler(j.roll, j.pitch, j.yaw, "ZYX"))
    .setPosition(j.x, j.y, j.z);
}
export function jointsAt(time: number, id: BoltSpec["id"]): number[] {
  const frames = paths[id];
  const idx = Math.min(frames.length - 2, Math.max(0, Math.floor(time * 10)));
  const a = frames[idx],
    b = frames[idx + 1];
  const f = Math.max(0, Math.min(1, (time - a[0]) / (b[0] - a[0])));
  return a.slice(1).map((v, i) => v + (b[i + 1] - v) * f);
}
export function flangeAt(time: number, id: BoltSpec["id"]) {
  return flangeAtPath(jointsAt(time, id));
}
export function flangeAtPath(q: number[]) {
  const m = new Matrix4();
  for (let i = 0; i < 7; i++)
    m.multiply(originMatrix(data[i])).multiply(
      new Matrix4().makeRotationZ(q[i]),
    );
  return m.multiply(originMatrix(data[7]));
}
export function boltWorldAt(time: number, spec: BoltSpec): Matrix4 {
  if (time < 5)
    return flangeAt(3, spec.id).multiply(boltLocalMatrix(sampleCycle(5, spec)));
  if (time >= 63)
    return flangeAt(63, spec.id).multiply(
      boltLocalMatrix(sampleCycle(63, spec)),
    );
  return flangeAt(time, spec.id).multiply(
    boltLocalMatrix(sampleCycle(time, spec)),
  );
}
export function flangePosition(time: number, id: BoltSpec["id"]) {
  return new Vector3().setFromMatrixPosition(flangeAt(time, id));
}
