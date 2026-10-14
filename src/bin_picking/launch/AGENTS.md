<!-- Parent: ../AGENTS.md -->
<!-- Generated: 2026-08-04 | Updated: 2026-08-04 -->

# launch

## Purpose
ROS2 launch files that assemble Gazebo, MoveIt2, and the custom `bin_picking` nodes into
runnable stacks. Installed to `share/bin_picking/launch` via `setup.py`.

## Key Files
| File | Description |
|------|-------------|
| `franka_gazebo_moveit.launch.py` | Base stack: FR3 in Gazebo Sim + MoveIt + RViz. Loads the URDF from `../urdf/fr3_gazebo.urdf.xacro` (thin wrapper over vendored `franka_description`), MoveIt config as-is from `franka_fr3_moveit_config`, controller YAML from `franka_gazebo_bringup` |
| `spawn_bolts.launch.py` | Spawns the bolt bin + 7 M8 bolts into an already-running Gazebo sim at a fixed pose. **Layout constants (`BIN_XYZ`/`BOLT_REST_Z`) must match `bin_picking/bolt_scene.py` exactly** — mismatch desyncs Gazebo physics from the MoveIt planning-scene |
| `desktop_integration_demo.launch.py` | **One-command demo.** Sequences (with startup delays): Gazebo+MoveIt → spawn bolts → `desktop_bridge` → `integrated_pick_place`. Bolt vision/recognition is owned entirely by the desktop app; this robot-side stack only receives resulting poses via `/next_bolt_pose`. Args: `rviz`, `auto`, `bolts_delay`, `apps_delay` |

## For AI Agents

### Working In This Directory
- Launch order matters and is delay-based, not readiness-based (e.g. `bolts_delay`/`apps_delay`
  in `desktop_integration_demo.launch.py`) — if a slower machine causes a race, increase the
  delay args rather than assuming the pipeline logic is broken.
- `spawn_bolts.launch.py`'s bin/bolt position constants have exactly one other place they must
  match: `bin_picking/bolt_scene.py`'s `BIN_*`/`BOLT_LAYOUT`. Grep both before changing geometry.
- This repo has no robot-side camera/vision launch step. Bolt recognition (camera → point
  cloud → pose ranking) is the desktop app's pipeline; the robot only consumes the resulting
  poses via `/next_bolt_pose` (see `docs/desktop_protocol.md` §2C). Don't add vision nodes
  here to "complete" the stack.

### Testing Requirements
- Launch files can't be unit tested; verify by actually running them
  (`ros2 launch bin_picking <file>`) against a sourced ROS2 Jazzy + Gazebo Harmonic environment.

<!-- MANUAL: Any manually added notes below this line are preserved on regeneration -->
