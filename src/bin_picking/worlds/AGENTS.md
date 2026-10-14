<!-- Parent: ../AGENTS.md -->
<!-- Generated: 2026-08-04 | Updated: 2026-08-04 -->

# worlds

## Purpose
Gazebo world definition for the simulation.

## Key Files
| File | Description |
|------|-------------|
| `robot_view.sdf` | The Gazebo world loaded by `franka_gazebo_moveit.launch.py` — ground plane, lighting, and physics settings the robot/bin/bolts are spawned into |

## For AI Agents

### Working In This Directory
- No robot-side camera/vision sensing lives in this repo — bolt pose estimation is owned by
  the desktop app, which delivers poses to the robot via `/next_bolt_pose`
  (`EXT_POSE_TOPIC`, see `sensing.py`). This world file only needs ground plane, lighting,
  and physics for the robot/bin/bolts.

<!-- MANUAL: Any manually added notes below this line are preserved on regeneration -->
