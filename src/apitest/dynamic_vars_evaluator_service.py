import random
import re
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

_DEFAULT_DATE_FORMAT = "%Y-%m-%d"
_DEFAULT_DATETIME_FORMAT = "%Y-%m-%d %H:%M:%SZ"
_DYNAMIC_TODAY_PATTERN = re.compile(r"\{\{DynamicToday\}\}(?::([^:{}]+))?")
_DYNAMIC_NOW_PATTERN = re.compile(r"\{\{DynamicNow\}\}(?::([^:{}]+))?")
_DYNAMIC_FUTURE_PATTERN = re.compile(
    r"\{\{DynamicFuture\}\}:(\d+)([dhm])(?::([^:{}]+))?"
)
_DYNAMIC_PAST_PATTERN = re.compile(r"\{\{DynamicPast\}\}:(\d+)([dhm])(?::([^:{}]+))?")
_DYNAMIC_RANDOM_NUMBER_PATTERN = re.compile(r"\{\{DynamicRandomNumber\}\}:(\d+)")
_DYNAMIC_RANDOM_GUID_PATTERN = re.compile(r"\{\{DynamicRandomGuid\}\}")


class DynamicVarsEvaluatorService:
    """Resolve dynamic date, time, number, and GUID variables in values."""

    def replace_dynamic_variables(self, value: Any) -> Any:
        """Replace supported dynamic variables recursively in a value.

        Dictionaries and lists are traversed recursively. Strings beginning
        with ``{{`` are evaluated for supported dynamic tokens; all other
        values and strings are returned unchanged.

        Args:
            value: A scalar value, string, dictionary, list, or ``None`` to
                evaluate.

        Returns:
            The value with supported dynamic variables replaced.
        """
        if isinstance(value, dict):
            return {
                key: self.replace_dynamic_variables(item) for key, item in value.items()
            }
        if isinstance(value, list):
            return [self.replace_dynamic_variables(item) for item in value]
        if isinstance(value, str) and value.startswith("{{"):
            return self._resolve_dynamic_value(value)
        return value

    def _resolve_dynamic_value(self, value: str | None) -> str | None:
        if not value:
            return value

        utc_now = datetime.now(UTC)
        today_match = _DYNAMIC_TODAY_PATTERN.search(value)
        if today_match:
            date_format = today_match.group(1) or _DEFAULT_DATE_FORMAT
            value = value.replace(
                today_match.group(0),
                self._format_dynamic_datetime(utc_now, date_format),
            )

        now_match = _DYNAMIC_NOW_PATTERN.search(value)
        if now_match:
            date_format = now_match.group(1) or _DEFAULT_DATETIME_FORMAT
            value = value.replace(
                now_match.group(0),
                self._format_dynamic_datetime(utc_now, date_format),
            )

        for pattern, sign in (
            (_DYNAMIC_FUTURE_PATTERN, 1),
            (_DYNAMIC_PAST_PATTERN, -1),
        ):
            date_match = pattern.search(value)
            if date_match:
                amount = int(date_match.group(1)) * sign
                unit = date_match.group(2)
                date_format = date_match.group(3) or _DEFAULT_DATETIME_FORMAT
                delta = {
                    "d": timedelta(days=amount),
                    "h": timedelta(hours=amount),
                    "m": timedelta(minutes=amount),
                }[unit]
                value = value.replace(
                    date_match.group(0),
                    self._format_dynamic_datetime(utc_now + delta, date_format),
                )

        random_number_match = _DYNAMIC_RANDOM_NUMBER_PATTERN.search(value)
        if random_number_match:
            digits = int(random_number_match.group(1))
            minimum = 10 ** (digits - 1)
            maximum = 10**digits - 1
            return str(random.randint(minimum, maximum))

        if _DYNAMIC_RANDOM_GUID_PATTERN.search(value):
            return str(uuid.uuid4())

        return value

    def _format_dynamic_datetime(self, value: datetime, date_format: str) -> str:
        if date_format == _DEFAULT_DATETIME_FORMAT:
            return value.strftime(_DEFAULT_DATETIME_FORMAT)

        if date_format == _DEFAULT_DATE_FORMAT:
            return value.strftime(_DEFAULT_DATE_FORMAT)

        python_format = date_format
        replacements = (
            ("yyyy", "%Y"),
            ("yy", "%y"),
            ("MM", "%m"),
            ("dd", "%d"),
            ("HH", "%H"),
            ("mm", "%M"),
            ("ss", "%S"),
        )
        for input_token, python_token in replacements:
            python_format = python_format.replace(input_token, python_token)
        return value.strftime(python_format)
