<!-- Parent: ../AGENTS.md -->
<!-- Generated: 2026-08-04 | Updated: 2026-08-04 -->

# bin_picking (Python module)

## Purpose
Core implementation. Originally a single 3350-line god-class; refactored into responsibility-
scoped **Mixin** modules that `IntegratedPickPlace` (in `pick_place_node.py`) all inherits
from — behavior is unchanged (107 methods / 82 constants verified identical pre/post-split),
but each file now shows only the code for its one responsibility. An independent ROS2 node
also lives here (`desktop_bridge.py`) plus ROS-free pure-Python helpers.
Full rationale: `docs/architecture.md`. Full desktop wire contract: `docs/desktop_protocol.md`.

## Key Files
| File | Description |
|------|-------------|
| `pick_place_node.py` | **Start here.** Thin orchestrator (`run`/`_pick`/`_drop`) + `main()`; assembles all the Mixins below into `IntegratedPickPlace(Node, ...)` |
| `config.py` | **Task** constants (grasp depth/aperture, learning knobs) with "why this value" comments, plus `apply_profile()` which injects the active robot model's **machine** constants into `PickPlaceConfig` at import time |
| `robot_profiles/` | Robot model registration/validation/switching. `schema.py` (what a registrant must fill in), `registry.py` (what counts as registered + active-model selection), `validator.py` (does the hand-entered value match the real robot), `data/*.yaml` (built-in profiles). ROS-free — see `docs/robot_profiles.md` |
| `model_cli.py` | `binpick_model` console script — `list`/`show`/`new`/`validate`/`verify`/`use` |
| `gripper_adapters.py` | Gripper action-interface adapters (`FollowJointTrajectory` / `GripperCommand`); owns goal construction and result interpretation so `gripper.py` stays vendor-neutral |
| `geometry.py` | Pure math: bolt axis/rotation, grasp coordinate frames, segment distance. ROS-free, unit-testable |
| `grasp_planning.py` | Gripper aperture, approach tilt, bin-wall/reachability judgment |
| `sensing.py` | Subscribes to bolt 6D poses via `/next_bolt_pose` (`EXT_POSE_TOPIC`, the desktop app's pose input) plus the Gazebo ground-truth fallback. **Owns the single entry point `_all_bolt_poses()`** |
| `robot_state.py` | `/joint_states` subscription, arm + finger joint state queries |
| `moveit_io.py` | MoveIt plan/execute/Cartesian/IK/FK service & action wrappers |
| `gripper.py` | Gripper control (delegates goal/result handling to `gripper_adapters.py`) + grasp-success judgment |
| `scene.py` | PlanningScene collision-object registration, bolt attach/detach |
| `markers.py` | RViz marker publishing |
| `selection.py` | Bolt selection (heuristic / learned / plan-only rollout). **Owns `_log_attempt()`**, the single exit point every `_pick()` outcome passes through |
| `bolt_scene.py` | Bin/bolt asset dimensions — single source shared by spawn (`launch/spawn_bolts.launch.py`) and MoveIt planning-scene |
| `grasp_selector.py` | Learned grasp selector (sklearn `SGDClassifier`, ROS-free) |
| `train_selector.py` | Offline hyperparameter search over accumulated `attempts.jsonl`; still saves an SGD-compatible model (GBT is compared but not deployed — see file docstring) |
| `desktop_bridge.py` | **Independent node.** Desktop app ↔ robot communication bridge — REST API (commands) + WebSocket (telemetry stream only) hybrid on port 8765, Bearer-token auth, optional TLS (aiohttp). See `docs/desktop_protocol.md` §4 |
| `protocol.py` | Pure, ROS-free translation layer for the desktop protocol — `FAIL_REASON_MAP`/`map_fail_reason()` is the **single source of truth** for internal-reason → Appendix-D-code mapping, and `joint_margins()` |

## For AI Agents

### Working In This Directory
- **Dependency direction is one-way, no cycles**: `config` → `geometry` → `grasp_planning` →
  `pick_place_node`; the ROS-aware mixins (`sensing`, `robot_state`, `moveit_io`, `gripper`,
  `scene`, `markers`, `selection`) all feed into `pick_place_node` as sibling Mixins, not into
  each other. `grasp_selector.py` feeds `selection.py` for learning only. Don't introduce a
  reverse or lateral import between mixins — see `docs/architecture.md` for the full graph.
- **`_all_bolt_poses()` (`sensing.py`) is the single entry point** for bolt pose data. Neighbor
  judgment and aperture calculation must go through it — iterating `_bolt_sensed` directly
  breaks fallback mode (neighbors read as 0, truncating the descend phase). This is called out
  explicitly in `docs/architecture.md` as a regression hotspot.
- **`_log_attempt()` (`selection.py`) is the single exit point** every `_pick()` outcome passes
  through. `desktop_bridge.py`'s `RESULT` publishing hooks into this exact point (one publish
  call added, grasp logic untouched) — if you add a new pick outcome path, route it through
  `_log_attempt()` or the desktop bridge and the learned-selector logging will both miss it.
- **Task vs machine constants.** Before adding a constant, decide which it is: a *task* value
  (bolt dimensions, bin layout, blacklist policy — same on any robot) stays a literal in
  `config.py`; a *machine* value (joint names/limits, gripper command units, fingertip geometry,
  reachability limits, MoveIt config location — differs per vendor) belongs in a robot profile
  (`robot_profiles/data/*.yaml`) and gets injected by `apply_profile()`. Ask "would this be the
  same on a UR5e?" Never re-hardcode `fr3_*` names anywhere — read them off `self.X`/`cls.X`.
- **`apply_profile()` writes to the *class*, not instances** — several pure calculations are
  `@classmethod` (`_grasp_z_for`, `_finger_width_is_grasp`, `_grasp_frame`) and read `cls.X`.
  Injecting into an instance would leave those reading stale values: the robot would be renamed
  but keep the old physics. If you convert one of these to an instance method, keep both paths
  reading the same source.
- **Derived constants** (e.g. `GRASP_FLOOR_Z`, `GRASP_DETECT_MIN`) are computed
  from other constants — don't hardcode a duplicate value, change the source constant.
  Those that depend on profile values are recomputed inside `apply_profile()`; if you add a new
  derived constant that reads a profile value, it must be recomputed there too.
  Also don't flip `USE_PICK_BIN`/`PICK_BIN_FLOOR`/`REQUIRE_SENSING` defaults without
  understanding they're the values that currently produce ~100% grasp success (see
  `PROGRESS.md`'s 2026-07-21~23 entries for why).
- **`protocol.py`'s `FAIL_REASON_MAP` is the only source of truth** for mapping internal
  failure-reason strings (from `pick_place_node.py`'s `_pick()`) to the desktop protocol's
  Appendix-D codes. If `_pick()` grows a new internal failure string, add it here or it falls
  through to `UNKNOWN` (intentional — a loud signal of a missing mapping, not silent misrouting).
- `desktop_bridge.py` and `pick_place_node.py` are **deliberately separate processes/nodes**,
  not just separate files — a bug in the bridge must not be able to kill an in-flight grasp
  cycle, and the bridge must be independently startable without Gazebo/MoveIt for protocol-only
  testing. Don't merge them into one node.
- `protocol.py`, `geometry.py`, `grasp_selector.py` are intentionally ROS-free (no `rclpy`
  import) so they're unit-testable without sourcing ROS2. Keep new pure-logic code out of
  ROS-coupled files if it doesn't need `rclpy`.

### Testing Requirements
- `protocol.py` has real unit test coverage: `src/bin_picking/test/test_protocol.py`
  (`python3 -m pytest test/` from the package root, no ROS needed). Any change to
  `FAIL_REASON_MAP` should get a corresponding test case update.
- Everything else currently has no automated tests — verification is manual/simulation-based
  (launch the full stack, watch grasp success rate / RViz markers / bridge round-trips via
  `tools/mock_desktop_client.py`). If you add tests, prefer testing the ROS-free modules
  (`geometry.py`, `grasp_selector.py`, `bolt_scene.py`) directly since they need no ROS harness.

### Common Patterns
- Every Mixin module's docstring states "state is owned by the node instance" — these classes
  hold no `__init__`/state of their own; they assume `self` is an `IntegratedPickPlace`
  instance at runtime. Don't try to instantiate a Mixin standalone.
- Korean comments throughout explain *why* a value or approach was chosen (especially
  `config.py`); preserve that intent when editing rather than replacing with terser English.

<!-- MANUAL: Any manually added notes below this line are preserved on regeneration -->
