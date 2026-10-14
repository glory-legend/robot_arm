// Geometry comparison only. Installation envelopes are excluded from the aluminium-equivalent
// estimate; this is neither a weighed assembly nor a strength/torque qualification.
import assert from "node:assert/strict";
import { mkdir, writeFile } from "node:fs/promises";
import { createServer } from "vite";
import { ShapeUtils } from "three";
const server = await createServer({
  server: { middlewareMode: true, ws: false },
  appType: "custom",
});
const output = "archive/R11";
try {
  const { makeCompactGripper } = await server.ssrLoadModule(
    "/src/compact-model.ts",
  );
  const { designOf } = await server.ssrLoadModule("/src/compact-kinematics.ts");
  // Closed triangulated solids: sum signed tetrahedron volumes about the local origin.
  const volume = (mesh) => {
    // R10's legacy yoke has an invalid cap near a slot corner. Compare the declared design
    // sections, not that broken cap. Dense curve sampling keeps circular area error <0.003%.
    if (mesh.geometry.type === "ExtrudeGeometry") {
      const { shapes, options } = mesh.geometry.parameters;
      return (
        Math.abs(ShapeUtils.area(shapes.getPoints(256))) * options.depth -
        shapes.holes.reduce(
          (v, h) =>
            v + Math.abs(ShapeUtils.area(h.getPoints(256))) * options.depth,
          0,
        )
      );
    }
    const p = mesh.geometry.attributes.position,
      ix = mesh.geometry.index;
    let sum = 0;
    for (let i = 0; i < (ix?.count ?? p.count); i += 3) {
      const [a, b, c] = [0, 1, 2].map((k) => (ix ? ix.getX(i + k) : i + k));
      sum +=
        p.getX(a) * (p.getY(b) * p.getZ(c) - p.getZ(b) * p.getY(c)) +
        p.getY(a) * (p.getZ(b) * p.getX(c) - p.getX(b) * p.getZ(c)) +
        p.getZ(a) * (p.getX(b) * p.getY(c) - p.getY(b) * p.getX(c));
    }
    return Math.abs(sum / 6);
  };
  const structure =
    /^(slim-nose-tube|front-plate-with-ports|rear-bulkhead|tie-rod|robot-adapter-ring|cover-sleeve|structural-guide-housing|feed-yoke)$/;
  const rows = ["c2", "r11"].map((id) => {
    const g = makeCompactGripper(undefined, id),
      d = designOf(id);
    const meshes = [],
      selected = [];
    g.root.traverse((o) => {
      if (!o.isMesh) return;
      meshes.push(o.name);
      if (structure.test(o.name))
        selected.push({ name: o.name, volume_mm3: volume(o) });
    });
    const material = selected.reduce((n, p) => n + p.volume_mm3, 0);
    return {
      id,
      body: d.body,
      nose_mm: d.nose,
      stow_mm: d.stow,
      envelope_mm3: ((Math.PI * d.body.width ** 2) / 4) * d.body.length,
      structural_material_mm3: material,
      aluminium_equivalent_g: material * 0.0027,
      mesh_count: meshes.length,
      structure_meshes: selected,
      all_mesh_names: meshes,
    };
  });
  const [before, after] = rows;
  assert(after.envelope_mm3 < before.envelope_mm3 * 0.92);
  assert(after.structural_material_mm3 < before.structural_material_mm3 * 0.85);
  assert(after.mesh_count < before.mesh_count);
  const result = {
    date: "2026-10-02",
    scope:
      "Declared section area x extrusion depth for extrusions (256 curve subdivisions); signed tetrahedra for closed primitives. R10 legacy yoke cap is invalid, so cap-volume is not used. Aluminium-equivalent estimate at 2.70 g/cm3 for named housing/frame/yoke solids only. Excludes other parts, motors, transmission, cables, fasteners. No measured mass or strength claim.",
    rows,
    reduction_percent: {
      envelope: 100 * (1 - after.envelope_mm3 / before.envelope_mm3),
      selected_material:
        100 *
        (1 - after.structural_material_mm3 / before.structural_material_mm3),
      mesh_count: 100 * (1 - after.mesh_count / before.mesh_count),
    },
  };
  await mkdir(output, { recursive: true });
  await writeFile(
    `${output}/geometry-comparison.json`,
    JSON.stringify(result, null, 2) + "\n",
  );
  await writeFile(
    `${output}/component-review.csv`,
    "design,mesh,volume_mm3\n" +
      rows
        .flatMap((r) =>
          r.structure_meshes.map(
            (p) => `${r.id},${p.name},${p.volume_mm3.toFixed(3)}`,
          ),
        )
        .join("\n") +
      "\n",
  );
  console.log(
    JSON.stringify(
      {
        rows: rows.map(({ structure_meshes, all_mesh_names, ...r }) => r),
        reduction_percent: result.reduction_percent,
      },
      null,
      2,
    ),
  );
} finally {
  await server.close();
}
