<!-- Parent: ../AGENTS.md -->
<!-- Generated: 2026-08-04 | Updated: 2026-08-04 -->

# franka_fr3_moveit_config

## Purpose
**Vendored upstream package** (Franka Robotics GmbH, Apache-2.0) — MoveIt2 configuration
(kinematics, OMPL planner params, controllers, RViz config) for the FR3. Depends on
`franka_description`. Copied wholesale for workspace self-containment, not a submodule.

## For AI Agents

### Working In This Directory
- Treat as **read-only** unless a task explicitly requires tuning MoveIt planning behavior
  (e.g. OMPL planner timeout, controller mapping) — that's the one legitimate reason to edit
  files here, since `bin_picking` loads this config as-is (`launch/franka_gazebo_moveit.launch.py`).
- If motion planning fails or behaves unexpectedly and the bug isn't in `bin_picking`'s own
  code (`moveit_io.py`, `grasp_planning.py`), check here next — planner params, joint limits,
  or controller config mismatches live in this package.

<!-- MANUAL: Any manually added notes below this line are preserved on regeneration -->
