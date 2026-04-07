"""Configuration helpers for local and Raspberry Pi deployment."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Tuple


DEFAULT_RST_PINS = {"I1": 17, "I2": 27, "I3": 22}
DEFAULT_SENSOR_PORTS = {
    "I1": "/dev/ttyUSB0",
    "I2": "/dev/ttyUSB1",
    "I3": "/dev/ttyUSB2",
}


def _load_env_file() -> None:
    """Load a local .env file without requiring python-dotenv."""
    root = Path(__file__).resolve().parent.parent
    candidates = (Path.cwd() / ".env", root / ".env")

    for env_path in candidates:
        if not env_path.exists():
            continue
        for raw_line in env_path.read_text(encoding="utf-8").splitlines():
            line = raw_line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            key = key.strip()
            value = value.strip().strip("'").strip('"')
            os.environ.setdefault(key, value)
        break


_load_env_file()


def _env_int(name: str, default: int) -> int:
    raw = os.getenv(name)
    return default if raw is None else int(raw)


def _env_float(name: str, default: float) -> float:
    raw = os.getenv(name)
    return default if raw is None else float(raw)


def _env_bool(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def _detect_model_dir() -> Path:
    root = Path(__file__).resolve().parent.parent
    candidates = (
        Path(os.getenv("MODEL_DIR", "")) if os.getenv("MODEL_DIR") else None,
        root / "trained_models",
        root,
    )
    for candidate in candidates:
        if candidate and (candidate / "scaler.joblib").exists():
            return candidate
    return root


@dataclass(frozen=True)
class AppConfig:
    sensor_mode: str = os.getenv("SENSOR_MODE", "multiplexed_uart")
    uart_port: str = os.getenv("UART_PORT", "/dev/serial0")
    baud_rate: int = _env_int("BAUD_RATE", 9600)
    serial_timeout: float = _env_float("SERIAL_TIMEOUT", 1.0)
    sample_interval: float = _env_float("SAMPLE_INTERVAL", 15.0)
    warmup_seconds: float = _env_float("SENSOR_WARMUP_SECONDS", 0.1)
    disable_delay_seconds: float = _env_float("SENSOR_DISABLE_DELAY_SECONDS", 0.05)
    settle_delay_seconds: float = _env_float("SENSOR_SETTLE_DELAY_SECONDS", 0.1)
    buffer_delay_seconds: float = _env_float("SENSOR_BUFFER_DELAY_SECONDS", 0.2)
    read_attempts: int = _env_int("SENSOR_READ_ATTEMPTS", 5)
    sensor_read_fallback_enabled: bool = _env_bool(
        "SENSOR_READ_FALLBACK_ENABLED",
        False,
    )
    sensor_read_fallback_value: float = _env_float("SENSOR_READ_FALLBACK_VALUE", 0.0)
    sensor_ports: Dict[str, str] = field(
        default_factory=lambda: {
            name: os.getenv(f"{name}_PORT", default)
            for name, default in DEFAULT_SENSOR_PORTS.items()
        }
    )
    rst_pins: Dict[str, int] = field(
        default_factory=lambda: {
            name: _env_int(f"{name}_RST_PIN", default)
            for name, default in DEFAULT_RST_PINS.items()
        }
    )
    model_dir: Path = field(default_factory=_detect_model_dir)
    thingspeak_api_key: str = os.getenv(
        "THINGSPEAK_API_KEY",
        "REPLACE_WITH_YOUR_THINGSPEAK_WRITE_API_KEY",
    )
    thingspeak_url: str = os.getenv(
        "THINGSPEAK_URL",
        "https://api.thingspeak.com/update",
    )
    thingspeak_enabled: bool = os.getenv("THINGSPEAK_ENABLED", "false").lower() == "true"

    def ordered_sensor_names(self) -> Tuple[str, str, str]:
        return ("I1", "I2", "I3")
