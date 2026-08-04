<!-- Parent: ../AGENTS.md -->
<!-- Generated: 2026-08-04 | Updated: 2026-08-04 -->

# models

## Purpose
Gazebo SDF models for the bin-picking scene: the bin and the M8 bolt, spawned by
`launch/spawn_bolts.launch.py`.

## Subdirectories
| Directory | Purpose |
|-----------|---------|
| `bolt_bin/` | `model.sdf` + `model.config` — open box (floor + 4 walls, hollow so the gripper can enter) |
| `m8_bolt/` | `model.sdf` + `model.config` — bolt approximated as a lying cylinder |

## For AI Agents

### Working In This Directory
- **Dimensions here have two other places they must match**: `launch/spawn_bolts.launch.py`
  (spawn pose constants) and `bin_picking/bin_picking/bolt_scene.py` (`BIN_*`/`BOLT_LAYOUT`,
  which registers the matching MoveIt planning-scene collision objects). Changing a model's
  size/shape without updating both means Gazebo physics and MoveIt's collision checking
  disagree — grasps will plan against geometry that isn't actually there.
- `setup.py`'s `data_tree()` installs this directory recursively into `share/` automatically;
  no `setup.py` change needed when adding files here, only when adding a new top-level model dir.

<!-- MANUAL: Any manually added notes below this line are preserved on regeneration -->
