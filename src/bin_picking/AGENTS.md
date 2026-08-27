<!-- Parent: ../AGENTS.md -->
<!-- Generated: 2026-08-04 | Updated: 2026-08-04 -->

# bin_picking (package)

## Purpose
The ROS2 `ament_python` package that is this project. FR3 + parallel gripper bin-picking
demo: a pick/place pipeline plans and executes grasps via MoveIt2 in Gazebo, receiving M8
bolt poses via `/next_bolt_pose` from an externally-developed desktop app (bolt recognition —
camera → point cloud → pose ranking — is owned entirely by that desktop app, not this repo),
and a WebSocket+JSON bridge exposes the robot to that desktop app. See root `README.md` for
the pipeline diagram and `docs/architecture.md` for why the code is split the way it is.

## Key Files
| File | Description |
|------|-------------|
| `package.xml` | ROS2 package manifest — declares `ament_python` build type and runtime deps (`rclpy`, MoveIt msgs, `franka_description`/`franka_fr3_moveit_config`/`franka_gazebo_bringup`, `ros_gz_sim`, etc.) |
| `setup.py` | Python package + console-script entry points: `integrated_pick_place`, `train_selector`, `desktop_bridge`. Also installs `models/`, `urdf/`, `worlds/`, `launch/*.launch.py` into `share/` |
| `setup.cfg` | ament_python install-scripts config |

## Subdirectories
| Directory | Purpose |
|-----------|---------|
| `bin_picking/` | ★ The Python package — all node logic, split by responsibility (see `bin_picking/AGENTS.md`) |
| `launch/` | ROS2 launch files that wire Gazebo + MoveIt + custom nodes together |
| `test/` | pytest unit tests (currently: `protocol.py` contract tests, ROS-free) |
| `tools/` | Standalone dev/verification scripts, not installed as ROS nodes (e.g. `mock_desktop_client.py`) |
| `models/` | Gazebo SDF models for the bolt bin and M8 bolt, spawned by `launch/spawn_bolts.launch.py` |
| `urdf/` | Thin xacro wrapper around `franka_description`'s FR3 URDF, adding Gazebo-specific overrides (gravity) |
| `worlds/` | Gazebo world SDF (`robot_view.sdf`) |
| `resource/` | Empty ament marker file (`resource/bin_picking`) required by `ament_python` — do not touch |

## For AI Agents

### Working In This Directory
- Console-script entry points in `setup.py` are the canonical list of runnable nodes/tools —
  if you add a new node, register it there or `ros2 run` won't find it.
- `data_tree()` in `setup.py` recursively installs `models/` into `share/` because
  `ament_python`'s `data_files` doesn't support directory recursion natively — if you add new
  model asset subdirectories, they're picked up automatically; no `setup.py` edit needed.
- Numeric layout constants (bin position, bolt rest height/orientation) are duplicated by
  necessity across `models/*/model.sdf`, `launch/spawn_bolts.launch.py`, and
  `bin_picking/bolt_scene.py`'s `BIN_*`/`BOLT_LAYOUT` — these three **must stay in sync**
  (Gazebo physics vs MoveIt planning-scene vs spawn script). Grep all three before changing
  bin/bolt geometry.

### Testing Requirements
- `python3 -m pytest test/` from this directory — only needs `pytest`, no ROS sourcing.
- Full-stack smoke test: `ros2 launch bin_picking desktop_integration_demo.launch.py`
  (Gazebo+MoveIt → spawn bolts → `desktop_bridge` → `integrated_pick_place`, in that order).

## Dependencies

### Internal
- `franka_description`, `franka_fr3_moveit_config`, `franka_gazebo_bringup` (`../`, vendored)

### External
- `rclpy`, MoveIt2 (`moveit_msgs`, `moveit_ros_move_group`), `ros_gz_sim`/`ros_gz_bridge`,
  `controller_manager`, `robot_state_publisher`, `rviz2`
- Python: `scikit-learn`, `numpy` (learned selector, `grasp_selector.py`), `aiohttp`
  (`desktop_bridge.py` — REST+WebSocket server, not in `package.xml`, installed via pip),
  `websockets` (`tools/mock_desktop_client.py`'s WS client only — not needed by the
  bridge itself since v3, also pip-only)

<!-- MANUAL: Any manually added notes below this line are preserved on regeneration -->
