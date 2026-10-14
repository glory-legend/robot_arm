<!-- Parent: ../AGENTS.md -->
<!-- Generated: 2026-08-04 | Updated: 2026-08-04 -->

# urdf

## Purpose
Thin xacro wrapper around the vendored FR3 robot description.

## Key Files
| File | Description |
|------|-------------|
| `fr3_gazebo.urdf.xacro` | Wraps `franka_description`'s unmodified URDF, adding Gazebo-only overrides: gravity settings |

## For AI Agents

### Working In This Directory
- Keep this a thin wrapper — the actual robot geometry/kinematics comes from
  `franka_description` (vendored, upstream). Additions here should be Gazebo-simulation-only
  concerns (gravity, plugin config), not robot model changes.
- No robot-side camera/vision sensor lives here — bolt pose estimation is the desktop app's
  responsibility; the robot receives bolt poses via `/next_bolt_pose` (`EXT_POSE_TOPIC`,
  see `bin_picking/sensing.py`).

<!-- MANUAL: Any manually added notes below this line are preserved on regeneration -->
