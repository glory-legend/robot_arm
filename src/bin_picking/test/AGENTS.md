<!-- Parent: ../AGENTS.md -->
<!-- Generated: 2026-08-04 | Updated: 2026-08-04 -->

# test

## Purpose
pytest unit tests, ROS-free by design so they run without sourcing ROS2/Gazebo.

## Key Files
| File | Description |
|------|-------------|
| `test_protocol.py` | Tests `bin_picking.protocol` against `docs/desktop_protocol.md` Appendix D/F. Covers all internal failure-reason strings `pick_place_node.py`'s `_pick()` actually produces, asserting they map to the correct desktop protocol code + `retry_suggested` value. This test passing is the concrete evidence that code and doc agree |

## For AI Agents

### Working In This Directory
- This is currently the **only** automated test coverage in the whole package — everything
  else (grasp planning, MoveIt integration, vision) is verified manually via simulation.
- If you change `bin_picking/protocol.py`'s `FAIL_REASON_MAP`, or `pick_place_node.py` starts
  emitting a new internal failure-reason string, add/update a case here in the same change —
  this is the mechanism that catches doc/code drift for the desktop protocol.
- Keep new tests ROS-free where the code under test allows it (mirrors the project's pattern
  of isolating pure logic — `geometry.py`, `grasp_selector.py`, `protocol.py` — from `rclpy`).

### Testing Requirements
- Run: `cd src/bin_picking && python3 -m pytest test/`. No ROS environment sourcing required.

<!-- MANUAL: Any manually added notes below this line are preserved on regeneration -->
