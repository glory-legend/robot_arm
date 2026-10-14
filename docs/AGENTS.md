<!-- Parent: ../AGENTS.md -->
<!-- Generated: 2026-08-04 | Updated: 2026-08-04 -->

# docs

## Purpose
Design and contract documentation for the bin-picking project. These are the authoritative
sources for *why* the code is shaped the way it is — read before refactoring across module
boundaries or changing the desktop↔robot wire format.

## Key Files
| File | Description |
|------|-------------|
| `architecture.md` | Why `pick_place_node.py`'s original 3350-line god-class was split into Mixin modules, the resulting dependency graph, and regression-risk hotspots to watch when editing |
| `desktop_protocol.md` | The desktop-app ↔ robot data contract: message envelope, command/telemetry catalog (§2), enums, `fail_reason` codes (Appendix D), and precise field specs (Appendix F). Communication transport (WebSocket+JSON via `desktop_bridge.py`) is decided and implemented (§4); the desktop app itself is out of scope (separate team) |
| `desktop_protocol_upgrade_plan.md` | 2026-08-25 protocol audit and Claude-ready v4 backlog: confirmed clock/ACK/event-loss/auth gaps, target command state machine, schemas, migration order, acceptance tests |
| `ros_supervisor_design.md` | PLC-less cell orchestration design and Claude-ready backlog: cell/command/cycle state machines, custom Actions, admission, cancel/recovery, restart reconciliation, and migration boundaries from `pick_place_node.py` |
| `desktop_connection_guide.md` | Practical companion to `desktop_protocol.md`: how to actually connect — host/port, WSL2 networking caveats, quick verification with `mock_desktop_client.py`, a real-vs-ACK-only command status table, troubleshooting, and dated evidence of what was actually run and verified |

## For AI Agents

### Working In This Directory
- These docs are living specs, not historical notes — `desktop_protocol.md` in particular is
  actively updated as the wire protocol changes (see its dated changelog entries inline).
- If you change `src/bin_picking/bin_picking/protocol.py` (fail-reason mapping) or
  `desktop_bridge.py` (message handling), update `desktop_protocol.md` in the same change —
  the doc explicitly claims the code is the source of truth, so a drift here is a bug in the doc.
- If you change the Mixin dependency direction in `bin_picking/bin_picking/` (e.g. making
  `geometry.py` depend on a ROS-aware module), update the dependency graph in `architecture.md`.
- Both docs are written in Korean; match that style when editing.

### Testing Requirements
- No executable content here. `test/test_protocol.py` (in `src/bin_picking/test/`) is the
  executable proof that `protocol.py` matches the tables in `desktop_protocol.md` §Appendix D/F.

<!-- MANUAL: Any manually added notes below this line are preserved on regeneration -->

- `bin_picking_analysis_and_upgrade_plan.md`는 2026-08-25 기준 전체 정밀 분석과
  Claude 실행용 작업 백로그다. 프로젝트 전반 결함/성능/실물 전환 작업은 이 문서의
  작업 ID와 수용 기준을 기준으로 진행하고, 완료 시 해당 문서와 `PROGRESS.md`를 함께
  현행화한다.
- 통신 작업은 `desktop_protocol_upgrade_plan.md`의 CP 작업 ID를 함께 따른다. 현재
  계약을 설명하는 `desktop_protocol.md`와 목표 v4 설계를 설명하는 계획서를 혼동하지
  말고, 구현 완료 전에는 전자를 현재 wire source로 유지한다.
- PLC 없는 운전의 셀 orchestration은 `ros_supervisor_design.md`의 SUP 작업 ID와
  불변조건을 따른다. Supervisor를 기능 안전이나 실시간 controller로 표현하지 않는다.
