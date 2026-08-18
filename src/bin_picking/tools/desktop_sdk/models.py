# -*- coding: utf-8 -*-
"""desktop_sdk 데이터 모델 — desktop_protocol.md §2 봉투/페이로드."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class Envelope:
    """§2 공통 봉투."""
    v: int
    type: str
    id: str
    corr: str | None
    prio: str
    t_wall: int
    t_sim: int
    use_sim_time: bool
    seq: int
    args: dict[str, Any]

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> Envelope:
        return cls(
            v=d.get('v', 0),
            type=d.get('type', ''),
            id=d.get('id', ''),
            corr=d.get('corr'),
            prio=d.get('prio', 'NORMAL'),
            t_wall=d.get('t_wall', 0),
            t_sim=d.get('t_sim', 0),
            use_sim_time=d.get('use_sim_time', False),
            seq=d.get('seq', 0),
            args=d.get('args', {}),
        )


@dataclass(frozen=True)
class ArmState:
    """§2B arm_state 텔레메트리."""
    q: list[float]
    tcp: list[float]
    tcp_quat: list[float]
    gripper_width: float
    joint_margin: list[float | None]
    moving: bool
    last_cycle_id: int | None

    @classmethod
    def from_args(cls, args: dict[str, Any]) -> ArmState:
        return cls(
            q=args.get('q', []),
            tcp=args.get('tcp', []),
            tcp_quat=args.get('tcp_quat', []),
            gripper_width=args.get('gripper_width', 0.0),
            joint_margin=args.get('joint_margin', []),
            moving=args.get('moving', False),
            last_cycle_id=args.get('last_cycle_id'),
        )


@dataclass(frozen=True)
class Heartbeat:
    """§2B heartbeat."""
    state: str
    moveit_ok: bool
    last_cycle_id: int | None

    @classmethod
    def from_args(cls, args: dict[str, Any]) -> Heartbeat:
        return cls(
            state=args.get('state', 'IDLE'),
            moveit_ok=args.get('moveit_ok', False),
            last_cycle_id=args.get('last_cycle_id'),
        )


@dataclass(frozen=True)
class PickResult:
    """§2D RESULT — PICK_BOLT 비동기 결과."""
    corr: str | None
    success: bool
    fail_reason: str | None
    retry_suggested: bool
    bolt_id: str | None
    matched_bolt_id: str | None
    origin: str

    @classmethod
    def from_envelope(cls, env: Envelope) -> PickResult:
        a = env.args
        return cls(
            corr=env.corr,
            success=a.get('success', False),
            fail_reason=a.get('fail_reason'),
            retry_suggested=a.get('retry_suggested', False),
            bolt_id=a.get('bolt_id'),
            matched_bolt_id=a.get('matched_bolt_id'),
            origin=a.get('origin', 'DESKTOP'),
        )


@dataclass(frozen=True)
class GraspResult:
    """§2B grasp_result — 로봇 자체선택 사이클 결과."""
    bolt_id: str | None
    success: bool
    fail_reason: str | None
    bolt_rise_m: float | None
    gripper_width_m: float | None

    @classmethod
    def from_args(cls, args: dict[str, Any]) -> GraspResult:
        return cls(
            bolt_id=args.get('bolt_id'),
            success=args.get('success', False),
            fail_reason=args.get('fail_reason'),
            bolt_rise_m=args.get('bolt_rise_m'),
            gripper_width_m=args.get('gripper_width_m'),
        )


@dataclass(frozen=True)
class Alert:
    """§2B alert."""
    severity: str
    code: str
    msg: str
    context: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_args(cls, args: dict[str, Any]) -> Alert:
        return cls(
            severity=args.get('severity', 'WARN'),
            code=args.get('code', ''),
            msg=args.get('msg', ''),
            context=args.get('context', {}),
        )


@dataclass(frozen=True)
class Status:
    """§2A GET_STATUS / WS 접속 직후 STATUS 스냅샷."""
    estop: bool
    robot_phase: str
    connected_clients: int
    joint_state_recv: bool
    cmd_state: dict[str, Any]
    robot_model: str
    robot_model_pending: str

    @classmethod
    def from_args(cls, args: dict[str, Any]) -> Status:
        return cls(
            estop=args.get('estop', False),
            robot_phase=args.get('robot_phase', 'IDLE'),
            connected_clients=args.get('connected_clients', 0),
            joint_state_recv=args.get('joint_state_recv', False),
            cmd_state=args.get('cmd_state', {}),
            robot_model=args.get('robot_model', ''),
            robot_model_pending=args.get('robot_model_pending', ''),
        )
