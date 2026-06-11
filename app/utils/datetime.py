from datetime import UTC, datetime

import dateutil.parser


def get_utc_now() -> datetime:
    """Return timezone-aware current UTC time."""
    return datetime.now(UTC)


def parse_iso_datetime(iso_str: str) -> datetime:
    """Parse an ISO format datetime string into timezone-aware datetime."""
    dt = dateutil.parser.isoparse(iso_str)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=UTC)
    return dt.astimezone(UTC)
