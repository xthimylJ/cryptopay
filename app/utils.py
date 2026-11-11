"""Small helpers for money conversion and ID generation."""
import re
import secrets
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation

WEI_PER_ETH = 10**18
ETH_ADDRESS_RE = re.compile(r"^0x[0-9a-fA-F]{40}$")
TX_HASH_RE = re.compile(r"^0x[0-9a-fA-F]{64}$")


def eth_to_wei(amount: str | Decimal) -> int:
    """'0.01' ETH -> 10000000000000000 wei. Uses Decimal, never float."""
    try:
        value = Decimal(str(amount))
    except InvalidOperation as exc:
        raise ValueError("Amount must be a number") from exc
    wei = value * WEI_PER_ETH
    if wei != wei.to_integral_value():
        raise ValueError("Amount has more than 18 decimal places")
    return int(wei)


def wei_to_eth(wei: int | str) -> str:
    """10000000000000000 wei -> '0.01' (string, no rounding errors)."""
    value = Decimal(int(wei)) / Decimal(WEI_PER_ETH)
    text = format(value.normalize(), "f")
    return text


def new_id(prefix: str) -> str:
    """Stripe-style readable IDs: 'pay_3f9a...', 'mer_81bc...'."""
    return f"{prefix}_{secrets.token_hex(12)}"


def is_eth_address(value: str) -> bool:
    return bool(ETH_ADDRESS_RE.match(value or ""))


def is_tx_hash(value: str) -> bool:
    return bool(TX_HASH_RE.match(value or ""))


def as_utc(dt: datetime | None) -> datetime | None:
    """SQLite returns dates without a timezone; treat them as UTC."""
    if dt is not None and dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt
