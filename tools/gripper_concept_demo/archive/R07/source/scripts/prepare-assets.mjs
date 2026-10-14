import { mkdir, copyFile, writeFile, readFile, cp } from "node:fs/promises";
import { fileURLToPath } from "node:url";
import path from "node:path";
const root = path.resolve(
  path.dirname(fileURLToPath(import.meta.url)),
  "../../..",
);
const source = path.join(root, "src/franka_description");
const dest = new URL("../public/fr3/", import.meta.url);
await mkdir(dest, { recursive: true });
for (let i = 0; i < 8; i++)
  await copyFile(
    path.join(source, `meshes/robots/fr3/visual/link${i}.dae`),
    new URL(`link${i}.dae`, dest),
  );
for (const file of ["LICENSE", "NOTICE"])
  await copyFile(path.join(source, file), new URL(file, dest));
// Keep browser FK data derived from the vendored YAML; no ROS runtime needed.
const parse = (text) =>
  [...text.matchAll(/joint(\d+):\s*\n([\s\S]*?)(?=\njoint\d+:|$)/g)].map(
    ([, id, body]) => ({
      id: Number(id),
      values: Object.fromEntries(
        [
          ...body.matchAll(
            /^\s+(x|y|z|roll|pitch|yaw|lower|upper):\s+([-\d.]+)/gm,
          ),
        ].map(([, k, v]) => [k, Number(v)]),
      ),
    }),
  );
const kin = parse(
  await readFile(path.join(source, "robots/fr3/kinematics.yaml"), "utf8"),
);
const limits = parse(
  await readFile(path.join(source, "robots/fr3/joint_limits.yaml"), "utf8"),
);
await writeFile(
  new URL("../src/robot-data.json", import.meta.url),
  JSON.stringify(
    kin.map(({ id, values }) => ({
      ...values,
      ...(limits.find((j) => j.id === id)?.values ?? {}),
    })),
    null,
    2,
  ) + "\n",
);
console.log("Prepared 8 FR3 meshes, kinematics and license notices.");

await cp(
  new URL("../assets/robotiq-2f85/", import.meta.url),
  new URL("../public/robotiq-2f85/", import.meta.url),
  { recursive: true },
);
console.log("Prepared vendored Robotiq 2F-85 meshes and attribution.");

await cp(
  new URL("../R06.md", import.meta.url),
  new URL("../public/design-notes.md", import.meta.url),
);

await cp(
  new URL("../MECHANICAL_REVIEW.md", import.meta.url),
  new URL("../public/mechanical-review.md", import.meta.url),
);
