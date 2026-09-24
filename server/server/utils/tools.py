"""Small generic helpers shared across server modules."""

from datetime import UTC, datetime
import random
import re
import string
from uuid import UUID


EMAIL_PATTERN = re.compile(r"^[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}$", re.IGNORECASE)


def utc_now() -> datetime:
    """Return the current timezone-aware UTC datetime."""
    return datetime.now(UTC)


def normalize_email(email: str) -> str:
    """Normalize an email address for lookup and uniqueness checks."""
    return email.strip().lower()


def is_valid_email(email: str) -> bool:
    """Return whether a string looks like a valid email address."""
    return bool(EMAIL_PATTERN.fullmatch(normalize_email(email)))


def random_digits(length: int = 6) -> str:
    """Return a random numeric verification code."""
    return _random_from_alphabet(string.digits, length)


def random_alphanumeric(length: int = 32) -> str:
    """Return a random letter-and-number token."""
    alphabet = string.ascii_letters + string.digits
    return _random_from_alphabet(alphabet, length)


def clamp(value: int, *, minimum: int, maximum: int) -> int:
    """Clamp an integer into an inclusive range."""
    return max(minimum, min(value, maximum))


def parse_uuid(value: str) -> UUID:
    """Parse a string into a UUID value."""
    return UUID(value)


def _random_from_alphabet(alphabet: str, length: int) -> str:
    """Return a random string from the provided alphabet."""
    if length <= 0:
        raise ValueError("Random string length must be positive.")

    return "".join(random.SystemRandom().choice(alphabet) for _ in range(length))
