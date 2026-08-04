<!-- Parent: ../AGENTS.md -->
<!-- Generated: 2026-08-04 | Updated: 2026-08-04 -->

# franka_gazebo_bringup

## Purpose
**Vendored upstream package** (Franka Robotics GmbH, Apache-2.0) — hosts the controllers YAML
referenced by `franka_description`'s URDF when `gazebo:=true`. Copied wholesale for workspace
self-containment, not a submodule. Smallest of the three vendored packages: just
`config/franka_gazebo_controllers.yaml` plus package/build boilerplate.

## For AI Agents

### Working In This Directory
- Treat as **read-only** unless a task explicitly requires changing gz_ros2_control controller
  definitions (joint controller types, PID gains, update rate) used by the Gazebo simulation.
- Referenced by `launch/franka_gazebo_moveit.launch.py` — if you rename or move
  `config/franka_gazebo_controllers.yaml`, update that launch file's path.

<!-- MANUAL: Any manually added notes below this line are preserved on regeneration -->
