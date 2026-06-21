from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from app.modules.proxy._service.http_bridge.service_stubs import _service_time

if TYPE_CHECKING:
    from app.modules.proxy._service.support import _HTTPBridgeSession, _HTTPBridgeSessionKey

logger = logging.getLogger("app.modules.proxy.service")
_HTTP_BRIDGE_STREAM_IDLE_REBIND_TTL_SECONDS = 180.0


class _HTTPBridgeStreamIdleRebindMixin:
    def _consume_http_bridge_stream_idle_rebind(
        self,
        key: "_HTTPBridgeSessionKey",
        previous_response_id: str | None,
    ) -> bool:
        if previous_response_id is None:
            return False
        rebinds = getattr(self, "_http_bridge_stream_idle_rebinds", None)
        if not isinstance(rebinds, dict):
            return False
        now = _service_time().monotonic()
        for rebind_key, expires_at in tuple(rebinds.items()):
            if expires_at <= now:
                rebinds.pop(rebind_key, None)
        return rebinds.pop((key, previous_response_id), None) is not None

    async def _mark_http_bridge_stream_idle_timeout(
        self,
        session: "_HTTPBridgeSession",
        *,
        previous_response_id: str | None,
    ) -> None:
        durable_session_id = session.durable_session_id
        if durable_session_id is None:
            return
        try:
            await self._durable_bridge.delete_session(session_id=durable_session_id)
            session.durable_session_id = None
            session.durable_owner_epoch = None
            rebinds = getattr(self, "_http_bridge_stream_idle_rebinds", None)
            if previous_response_id is not None and isinstance(rebinds, dict):
                rebinds[(session.key, previous_response_id)] = (
                    _service_time().monotonic() + _HTTP_BRIDGE_STREAM_IDLE_REBIND_TTL_SECONDS
                )
        except Exception:
            logger.warning("Failed to delete stream-idle HTTP bridge durable session", exc_info=True)
