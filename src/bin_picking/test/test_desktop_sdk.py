# -*- coding: utf-8 -*-
"""desktop_sdk 단위 테스트 (ROS/rclpy 무의존)."""
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'tools'))

import pytest

from desktop_sdk.models import (
    ArmState,
    Envelope,
    GraspResult,
    Heartbeat,
    PickResult,
    Status,
    Alert,
)
from desktop_sdk.exceptions import (
    BinPickingError,
    AuthenticationError,
    CommandRejectedError,
    ConnectionError,
    TimeoutError,
)


class TestEnvelope:

    def test_from_dict_full(self):
        d = {
            'v': 3, 'type': 'heartbeat', 'id': 's1-001', 'corr': None,
            'prio': 'NORMAL', 't_wall': 100, 't_sim': 99,
            'use_sim_time': True, 'seq': 42,
            'args': {'state': 'IDLE', 'moveit_ok': True},
        }
        env = Envelope.from_dict(d)
        assert env.v == 3
        assert env.type == 'heartbeat'
        assert env.seq == 42
        assert env.args['state'] == 'IDLE'

    def test_from_dict_missing_fields_use_defaults(self):
        env = Envelope.from_dict({})
        assert env.v == 0
        assert env.type == ''
        assert env.corr is None
        assert env.args == {}


class TestModels:

    def test_arm_state_from_args(self):
        a = ArmState.from_args({
            'q': [0.1] * 7, 'tcp': [0.3, 0.0, 0.5],
            'tcp_quat': [0, 0, 0, 1], 'gripper_width': 0.04,
            'joint_margin': [0.5] * 7, 'moving': True,
            'last_cycle_id': 5,
        })
        assert len(a.q) == 7
        assert a.moving is True
        assert a.last_cycle_id == 5

    def test_heartbeat_from_args(self):
        h = Heartbeat.from_args({'state': 'PLANNING', 'moveit_ok': True, 'last_cycle_id': 3})
        assert h.state == 'PLANNING'
        assert h.moveit_ok is True

    def test_heartbeat_defaults(self):
        h = Heartbeat.from_args({})
        assert h.state == 'IDLE'
        assert h.moveit_ok is False
        assert h.last_cycle_id is None

    def test_status_from_args(self):
        s = Status.from_args({
            'estop': True, 'robot_phase': 'SAFE_STOP',
            'connected_clients': 2, 'joint_state_recv': True,
            'cmd_state': {}, 'robot_model': 'fr3', 'robot_model_pending': 'ur5e',
        })
        assert s.estop is True
        assert s.robot_phase == 'SAFE_STOP'
        assert s.robot_model == 'fr3'

    def test_pick_result_from_envelope(self):
        env = Envelope.from_dict({
            'v': 3, 'type': 'RESULT', 'id': 'r1', 'corr': 's1-001',
            'prio': 'NORMAL', 't_wall': 0, 't_sim': 0,
            'use_sim_time': False, 'seq': 1,
            'args': {
                'success': False, 'fail_reason': 'UNREACHABLE',
                'retry_suggested': False, 'bolt_id': 'b-1',
                'matched_bolt_id': 'b-1-matched', 'origin': 'DESKTOP',
            },
        })
        r = PickResult.from_envelope(env)
        assert r.corr == 's1-001'
        assert r.success is False
        assert r.fail_reason == 'UNREACHABLE'
        assert r.origin == 'DESKTOP'

    def test_grasp_result_from_args(self):
        g = GraspResult.from_args({
            'bolt_id': 'b-5', 'success': True, 'fail_reason': None,
            'bolt_rise_m': 0.003, 'gripper_width_m': 0.008,
        })
        assert g.success is True
        assert g.bolt_rise_m == 0.003

    def test_alert_from_args(self):
        a = Alert.from_args({
            'severity': 'ERROR', 'code': 'JOINT_LIMITS_INCOMPLETE',
            'msg': 'missing j7', 'context': {'joint': 'j7'},
        })
        assert a.severity == 'ERROR'
        assert a.context['joint'] == 'j7'


class TestExceptions:

    def test_hierarchy(self):
        assert issubclass(AuthenticationError, BinPickingError)
        assert issubclass(CommandRejectedError, BinPickingError)
        assert issubclass(ConnectionError, BinPickingError)
        assert issubclass(TimeoutError, BinPickingError)

    def test_command_rejected_stores_errors(self):
        exc = CommandRejectedError(['missing bolt_id', 'invalid pose'])
        assert 'missing bolt_id' in str(exc)
        assert len(exc.errors) == 2

    def test_command_rejected_empty(self):
        exc = CommandRejectedError()
        assert exc.errors == []
        assert 'rejected' in str(exc)


class TestClientImport:

    def test_public_api_importable(self):
        from desktop_sdk import BinPickingClient
        assert BinPickingClient is not None

    def test_all_exports(self):
        import desktop_sdk
        assert hasattr(desktop_sdk, '__all__')
        for name in desktop_sdk.__all__:
            assert hasattr(desktop_sdk, name)
