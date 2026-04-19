import time
from dataclasses import dataclass, field
from datetime import datetime

import httpx
import structlog

from app.core.config import settings
from app.core.exceptions import BrokerError

log = structlog.get_logger()

_REFRESH_BUFFER_SECONDS = 300  # refresh 5 min before expiry


@dataclass
class KiwoomToken:
    access_token: str
    token_type: str
    expires_at: float = field(default=0.0)

    def is_valid(self) -> bool:
        return time.time() < self.expires_at - _REFRESH_BUFFER_SECONDS


_cache: KiwoomToken | None = None


def _parse_expires_dt(expires_dt: str) -> float:
    """Convert Kiwoom expires_dt (YYYYMMDDHHmmss) to unix timestamp."""
    return datetime.strptime(expires_dt, "%Y%m%d%H%M%S").timestamp()


async def get_token(override_settings=None) -> KiwoomToken:
    """Return a valid bearer token, refreshing from Kiwoom if needed."""
    global _cache

    cfg = override_settings or settings

    if _cache and _cache.is_valid():
        return _cache

    url = f"{cfg.active_base_url}{cfg.kiwoom_token_path}"
    payload = {
        "grant_type": "client_credentials",
        "appkey": cfg.active_app_key,
        "secretkey": cfg.active_app_secret,
    }

    log.info("kiwoom.token.fetch", url=url, trading_mode=cfg.trading_mode)

    async with httpx.AsyncClient() as client:
        resp = await client.post(
            url,
            json=payload,
            headers={"Content-Type": "application/json;charset=UTF-8"},
        )

    if resp.status_code != 200:
        raise BrokerError(
            f"Token issuance failed [{resp.status_code}]: {resp.text}"
        )

    data = resp.json()
    if data.get("return_code", -1) != 0:
        raise BrokerError(f"Token issuance error: {data.get('return_msg')}")

    expires_at = _parse_expires_dt(data["expires_dt"])
    _cache = KiwoomToken(
        access_token=data["token"],
        token_type=data.get("token_type", "Bearer"),
        expires_at=expires_at,
    )
    log.info("kiwoom.token.issued", expires_dt=data["expires_dt"])
    return _cache


def clear_token_cache() -> None:
    global _cache
    _cache = None
