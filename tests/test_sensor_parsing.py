import pytest

from motor_fault.sensors import parse_sensor_value


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("~0.123", 0.123),
        ("+1.500", 1.5),
        ("-2.250", -2.25),
        ("3.75", 3.75),
    ],
)
def test_parse_sensor_value(raw, expected):
    assert parse_sensor_value(raw) == pytest.approx(expected)


def test_parse_sensor_value_returns_none_for_empty_string():
    assert parse_sensor_value("") is None
