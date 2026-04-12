from __future__ import annotations

import random
import re
import string
from dataclasses import dataclass

from src.apps.iam.utils.hashid import decode_id

CURRENT_ORDER_REFERENCE_PATTERN = re.compile(r"^ORD-[A-Z0-9]{10}$")
LEGACY_ORDER_REFERENCE_PATTERN = re.compile(r"^ORD-\d{4}-[A-Z0-9]{4,}$")


@dataclass(frozen=True)
class ParsedOrderReference:
    raw: str
    normalized: str
    order_id: int | None
    is_order_number: bool


def build_order_reference(size: int = 10) -> str:
    suffix = "".join(random.choices(string.ascii_uppercase + string.digits, k=size))
    return f"ORD-{suffix}"


def parse_order_reference(value: str | int) -> ParsedOrderReference:
    raw = str(value).strip()
    normalized = raw.upper()
    is_order_number = bool(
        CURRENT_ORDER_REFERENCE_PATTERN.fullmatch(normalized)
        or LEGACY_ORDER_REFERENCE_PATTERN.fullmatch(normalized)
    )
    order_id = decode_id(raw) if raw else None
    return ParsedOrderReference(
        raw=raw,
        normalized=normalized,
        order_id=order_id,
        is_order_number=is_order_number,
    )


def is_supported_order_reference(value: str | int) -> bool:
    parsed = parse_order_reference(value)
    return parsed.is_order_number or parsed.order_id is not None
