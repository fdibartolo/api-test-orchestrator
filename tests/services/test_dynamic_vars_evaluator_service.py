import pytest
import re
from apitest.dynamic_vars_evaluator_service import DynamicVarsEvaluatorService

def test_replace_dynamic_variables_replaces_today_with_default_format() -> None:
    result = DynamicVarsEvaluatorService().resolve_dynamic_value("date={{DynamicToday}}")
    assert re.fullmatch(r"date=\d{4}-\d{2}-\d{2}", result)

def test_replace_dynamic_variables_replaces_custom_datetime_format() -> None:
    result = DynamicVarsEvaluatorService().resolve_dynamic_value(
        "at={{DynamicNow}}:yy-MM-dd"
    )
    assert re.fullmatch(r"at=\d{2}-\d{2}-\d{2}", result)

@pytest.mark.parametrize("token", ["DynamicFuture", "DynamicPast"])
def test_replace_dynamic_variables_replaces_relative_datetime(token: str) -> None:
    result = DynamicVarsEvaluatorService().resolve_dynamic_value(
        f"{{{{{token}}}}}:1d:yyyy-MM-dd"
    )
    assert re.fullmatch(r"\d{4}-\d{2}-\d{2}", result)

def test_replace_dynamic_variables_generates_random_number() -> None:
    result = DynamicVarsEvaluatorService().resolve_dynamic_value(
        "{{DynamicRandomNumber}}:8"
    )
    assert re.fullmatch(r"\d{8}", result)

def test_replace_dynamic_variables_generates_guid() -> None:
    result = DynamicVarsEvaluatorService().resolve_dynamic_value("{{DynamicRandomGuid}}")
    assert re.fullmatch(
        r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}",
        result,
    )

def test_replace_dynamic_variables_returns_empty_values_unchanged() -> None:
    assert DynamicVarsEvaluatorService().resolve_dynamic_value(None) is None
    assert DynamicVarsEvaluatorService().resolve_dynamic_value("") == ""

def test_replace_dynamic_variables_in_json_walks_nested_values() -> None:
    data = {
        "date": "{{DynamicToday}}",
        "nested": {
            "items": ["{{DynamicRandomGuid}}", 42, "plain text {{DynamicToday}}"],
        }
    }
    result = DynamicVarsEvaluatorService().replace_dynamic_variables(data)

    assert re.fullmatch(r"\d{4}-\d{2}-\d{2}", result["date"])
    assert re.fullmatch(
        r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}",
        result["nested"]["items"][0],
    )
    assert result["nested"]["items"][1] == 42
    assert result["nested"]["items"][2] == "plain text {{DynamicToday}}"

def test_replace_dynamic_variables_in_json_handles_null_values() -> None:
    assert DynamicVarsEvaluatorService().replace_dynamic_variables(None) is None
