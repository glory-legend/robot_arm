<!-- Generated: 2026-08-04 | Updated: 2026-08-04 -->

# robotarm_main

## Purpose
Self-contained ROS2 (Jazzy) + Gazebo (Harmonic) + MoveIt2 workspace that demos bin-picking:
a Franka **FR3** arm with a parallel gripper picks M8 bolts one at a time from a bin and
places them in another bin. Vision estimates bolt pose, a pick/place pipeline plans and
executes the grasp, and a WebSocket+JSON bridge exposes the robot to an (externally built)
desktop app for ranking/monitoring. Currently simulation-only; end goal is a real FR3.

Read `README.md` first (pipeline diagram + module map), then `PROGRESS.md` for what's
done/next, then `docs/desktop_protocol.md` if touching `desktop_bridge.py`/`protocol.py`.

## Key Files
| File | Description |
|------|-------------|
| `README.md` | Pipeline overview, directory map, module map, build/run instructions (Korean) |
| `PROGRESS.md` | Living project log/roadmap — completed tasks, current blockers, next steps |
| `LICENSE` / `NOTICE` | Apache-2.0; NOTICE attributes upstream Franka assets and the `PinkWink/robotarm_tutorials` base this project extends |
| `.gitignore` | Excludes colcon `build/`/`log/`/`install/` output and runtime state (`~/pick_place_logs/`, `*.pkl`) |

## Subdirectories
| Directory | Purpose |
|-----------|---------|
| `docs/` | Design docs: module architecture, desktop↔robot data contract (see `docs/AGENTS.md`) |
| `src/` | colcon workspace source — one custom package + three vendored Franka packages (see `src/AGENTS.md`) |
| `install/`, `log/`, `build/` | colcon build output — generated, not source. Do not hand-edit; `colcon build` regenerates them |

## For AI Agents

### Working In This Directory
- This repo is **self-contained**: `src/` includes the Franka robot assets it depends on
  (`franka_description`, `franka_fr3_moveit_config`, `franka_gazebo_bringup`) so the whole
  thing builds without fetching external ROS repos.
- The only actively-developed package is `src/bin_picking/` — start there for any feature
  work. The `franka_*` packages are vendored third-party assets (Apache-2.0, Franka Robotics
  GmbH); treat them as read-only unless a task explicitly requires patching upstream config.
- Runtime artifacts (`~/pick_place_logs/attempts.jsonl`, `selector_model.pkl`) live outside
  the repo and are gitignored by design — don't try to commit or "restore" them.
- Much of the project's own documentation is written in Korean; match that when editing
  `README.md`/`PROGRESS.md`/`docs/*.md` unless asked otherwise.

### Testing Requirements
- Python unit tests: `cd src/bin_picking && python3 -m pytest test/` (only `protocol.py` is
  currently covered — it's ROS-free by design so tests run without sourcing ROS).
- Full pipeline verification requires ROS2 Jazzy + Gazebo Harmonic + MoveIt2 sourced
  (`source /opt/ros/jazzy/setup.bash`, `colcon build --symlink-install`, `source install/setup.bash`).
  The default interactive shell here is zsh — sourcing the `.bash` variant directly under zsh
  fails (`setup.bash:.:11: ... setup.sh 없음`, since it locates itself via `$BASH_SOURCE`,
  which zsh doesn't set, so it falls back to `$PWD`). Either use the `.zsh` sibling files
  (`/opt/ros/jazzy/setup.zsh`, `install/setup.zsh`) or wrap the command in `bash -c '...'` to
  force real bash — both exist for this reason.
- See `README.md` "실행" section for the multi-terminal launch sequence, or
  `ros2 launch bin_picking desktop_integration_demo.launch.py` for the one-command demo.

### Common Patterns
- Data contracts (message schemas, enums, fail-reason codes) are documented in
  `docs/desktop_protocol.md` and must stay in sync with `src/bin_picking/bin_picking/protocol.py`
  — that file's `FAIL_REASON_MAP` is the single source of truth, not the doc's prose tables.
- Module boundaries in `bin_picking/bin_picking/` follow a Mixin decomposition (see
  `src/bin_picking/bin_picking/AGENTS.md`) — respect the documented dependency direction
  when adding code.

## Dependencies

### External
- ROS2 Jazzy, Gazebo Harmonic, MoveIt2
- Python: `scikit-learn`, `numpy` (learned bolt selector), `aiohttp` (desktop bridge —
  REST+WebSocket server), `websockets` (mock desktop client's WS reference only)

<!-- MANUAL: Any manually added notes below this line are preserved on regeneration -->
