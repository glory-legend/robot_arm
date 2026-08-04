<!-- Parent: ../AGENTS.md -->
<!-- Generated: 2026-08-04 | Updated: 2026-08-04 -->

# src

## Purpose
colcon workspace source root. One custom ROS2 package (`bin_picking`) plus three vendored
Franka Robotics packages that `bin_picking` depends on for the robot model, MoveIt config,
and Gazebo controller config. Vendoring them here makes the whole repo buildable without
fetching external ROS repos ("self-contained workspace" per `README.md`).

## Subdirectories
| Directory | Purpose |
|-----------|---------|
| `bin_picking/` | ★ The actual project — vision, grasp planning, MoveIt orchestration, desktop bridge (see `bin_picking/AGENTS.md`) |
| `franka_description/` | Vendored upstream: FR3 URDF/xacro + meshes (Franka Robotics GmbH, Apache-2.0). Read-only in practice |
| `franka_fr3_moveit_config/` | Vendored upstream: MoveIt2 config (kinematics, OMPL, controllers, RViz) for FR3. Read-only in practice |
| `franka_gazebo_bringup/` | Vendored upstream: Gazebo controller YAML referenced by `franka_description`'s URDF when `gazebo:=true`. Read-only in practice |

## For AI Agents

### Working In This Directory
- Only `bin_picking/` is project-owned code. The three `franka_*` directories are vendored
  third-party packages (no `.git` of their own — plain copies), not forks under active
  development here; treat changes to them as exceptional and call it out explicitly if you
  make one (e.g. patching a controller YAML to fix a local integration bug).
- `bin_picking/launch/*.py` is what wires the vendored packages together with the custom
  code (spawns Gazebo with `franka_description`'s URDF, loads `franka_fr3_moveit_config`,
  applies `franka_gazebo_bringup`'s controller YAML). If a launch fails, check whether it's
  a `bin_picking` bug or a version mismatch against the vendored assets first.

### Testing Requirements
- Build the whole workspace with `colcon build --symlink-install` from the repo root after
  sourcing ROS2 Jazzy. `--symlink-install` matters: it lets edits to `bin_picking`'s Python
  files take effect without rebuilding.

<!-- MANUAL: Any manually added notes below this line are preserved on regeneration -->
