<!-- Parent: ../AGENTS.md -->
<!-- Generated: 2026-08-04 | Updated: 2026-08-04 -->

# tools

## Purpose
Standalone developer/verification scripts. Not ROS nodes, not registered as console-script
entry points in `setup.py` — run directly with `python3`.

## Key Files
| File | Description |
|------|-------------|
| `mock_desktop_client.py` | Stand-in for the (separately built) desktop app. Talks to `desktop_bridge.py` over plain WebSocket+JSON — **no ROS dependency**, that's the point: it proves a non-ROS client can speak the protocol exactly as documented in `docs/desktop_protocol.md`. Two modes: interactive demo (`python3 mock_desktop_client.py [ws://host:port]`) and `--assert` (automated Tier-1 checks: required-field validation, `last_cycle_id` vs `cycle_id` naming, `joint_margin` shape, `seq` monotonicity under PING flooding, `PROTOCOL_VERSION`) — exits 1 on failure |

## For AI Agents

### Working In This Directory
- `mock_desktop_client.py` is the practical way to verify `desktop_bridge.py` changes without
  needing Gazebo/MoveIt running: `ros2 run bin_picking desktop_bridge` (bridge alone) +
  `python3 tools/mock_desktop_client.py --assert` (automated check) is the fast inner loop.
- If you add a new message type or field to the desktop protocol, extend this script's
  `--assert` checks in the same change — it's the only automated cross-check against
  `docs/desktop_protocol.md` at the wire level (as opposed to `test/test_protocol.py`, which
  only checks the internal `protocol.py` mapping function in isolation).
- Keep this script dependency-light (stdlib + `websockets` only) — its value is being runnable
  by a desktop developer with no ROS install.

<!-- MANUAL: Any manually added notes below this line are preserved on regeneration -->
