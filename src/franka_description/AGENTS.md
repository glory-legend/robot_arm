<!-- Parent: ../AGENTS.md -->
<!-- Generated: 2026-08-04 | Updated: 2026-08-04 -->

# franka_description

## Purpose
**Vendored upstream package** (Franka Robotics GmbH, Apache-2.0, v2.7.0) — URDF/xacro and
meshes for Franka robots, including the FR3 used by this project. Copied wholesale into this
repo so the workspace is self-contained (no external ROS repo fetch needed to build). Not a
git submodule — plain files, no upstream tracking.

Subdirectories (`end_effectors/`, `meshes/`, `robots/`, `launch/`, `rviz/`, `scripts/`, `.ci/`,
`.docker/`, `.github/`) are upstream package internals and are not individually documented
here — they're not actively developed as part of this project.

## For AI Agents

### Working In This Directory
- Treat as **read-only** unless a task explicitly requires patching upstream Franka assets
  (e.g. a local bug workaround). This project's own robot-model customization happens instead
  in `src/bin_picking/urdf/fr3_gazebo.urdf.xacro`, a thin wrapper that includes this package's
  URDF unmodified and adds Gazebo-only overrides — prefer extending that wrapper over editing
  files here.
- `src/bin_picking/package.xml` and `launch/franka_gazebo_moveit.launch.py` depend on this
  package's URDF/xacro paths; if you must rename or move files here, update both.

<!-- MANUAL: Any manually added notes below this line are preserved on regeneration -->
