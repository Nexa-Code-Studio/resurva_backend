import re


def is_valid_email(email: str) -> bool:
    """Validate email pattern."""
    pattern = r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$"
    return bool(re.match(pattern, email))


def is_valid_gps_coordinate(latitude: float, longitude: float) -> bool:
    """Validate latitude and longitude ranges."""
    return -90.0 <= latitude <= 90.0 and -180.0 <= longitude <= 180.0
