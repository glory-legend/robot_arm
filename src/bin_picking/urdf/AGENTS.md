<!-- Parent: ../AGENTS.md -->
<!-- Generated: 2026-08-04 | Updated: 2026-08-04 -->

# urdf

## Purpose
Thin xacro wrapper around the vendored FR3 robot description.

## Key Files
| File | Description |
|------|-------------|
| `fr3_gazebo.urdf.xacro` | Wraps `franka_description`'s unmodified URDF, adding Gazebo-only overrides: gravity settings and the `rgbd_camera` sensor (topic `bin_camera`) that feeds `bolt_vision.py` / `vision_pipeline.launch.py` |

## For AI Agents

### Working In This Directory
- Keep this a thin wrapper — the actual robot geometry/kinematics comes from
  `franka_description` (vendored, upstream). Additions here should be Gazebo-simulation-only
  concerns (sensors, gravity, plugin config), not robot model changes.
- If you change the camera topic name or sensor config, `vision_pipeline.launch.py` and
  `bolt_vision.py`'s subscribed topic must be updated together.

<!-- MANUAL: Any manually added notes below this line are preserved on regeneration -->
