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
- If bolt/vision sensing is misbehaving and geometry constants (`bolt_scene.py`,
  `spawn_bolts.launch.py`) already check out, verify the `Sensors` system plugin is still
  present in this world file — its absence was a real, previously-hit root cause of the
  camera silently not publishing (see `PROGRESS.md`, 2026-07-23~24 vision pipeline entry).

<!-- MANUAL: Any manually added notes below this line are preserved on regeneration -->
