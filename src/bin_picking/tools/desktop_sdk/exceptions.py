# -*- coding: utf-8 -*-
"""desktop_sdk 예외 계층."""


class BinPickingError(Exception):
    """SDK 최상위 예외."""


class ConnectionError(BinPickingError):
    """서버 연결/재연결 실패."""


class AuthenticationError(BinPickingError):
    """Bearer 토큰 인증 실패 (HTTP 401)."""


class CommandRejectedError(BinPickingError):
    """서버가 명령을 거부 (accepted=false)."""

    def __init__(self, errors: list[str] | None = None):
        self.errors = errors or []
        super().__init__(', '.join(self.errors) if self.errors else 'command rejected')


class TimeoutError(BinPickingError):
    """RESULT 대기 시간 초과."""
