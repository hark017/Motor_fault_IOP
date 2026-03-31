"""Sensor abstractions for Raspberry Pi deployment."""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Dict, Optional

from .config import AppConfig

try:
    import serial  # type: ignore
except ImportError:  # pragma: no cover - optional on non-Pi machines
    serial = None

try:
    import RPi.GPIO as GPIO  # type: ignore
except ImportError:  # pragma: no cover - optional on non-Pi machines
    GPIO = None


def parse_sensor_value(raw: str) -> Optional[float]:
    raw = raw.strip()
    if not raw:
        return None
    if raw[0] in "~+-":
        value = float(raw[1:])
        return -value if raw[0] == "-" else value
    return float(raw)


@dataclass
class CurrentSample:
    currents: Dict[str, float]
    timestamp: float


class MultiUSBSensorReader:
    """Reads one sensor per serial device."""

    def __init__(self, config: AppConfig):
        if serial is None:
            raise RuntimeError("pyserial is required to use the sensor readers")
        self.config = config
        self.connections: Dict[str, object] = {}

    def open(self) -> None:
        for name, port in self.config.sensor_ports.items():
            self.connections[name] = serial.Serial(
                port=port,
                baudrate=self.config.baud_rate,
                timeout=self.config.serial_timeout,
            )
            time.sleep(self.config.warmup_seconds)

    def close(self) -> None:
        for connection in self.connections.values():
            connection.close()
        self.connections.clear()

    def read_currents(self) -> CurrentSample:
        values = {}
        for name, connection in self.connections.items():
            connection.reset_input_buffer()
            line = connection.readline().decode("ascii", errors="ignore")
            values[name] = parse_sensor_value(line)
        if any(value is None for value in values.values()):
            raise RuntimeError(f"Incomplete sensor reading: {values}")
        return CurrentSample(currents=values, timestamp=time.time())


class MultiplexedUARTSensorReader:
    """Reads three sensors sharing one UART by gating each sensor with RST pins."""

    def __init__(self, config: AppConfig):
        if serial is None:
            raise RuntimeError("pyserial is required to use the sensor readers")
        if GPIO is None:
            raise RuntimeError("RPi.GPIO is required for multiplexed UART mode")
        self.config = config
        self.connection = None

    def open(self) -> None:
        GPIO.setmode(GPIO.BCM)
        GPIO.setwarnings(False)
        for pin in self.config.rst_pins.values():
            GPIO.setup(pin, GPIO.OUT)
            GPIO.output(pin, GPIO.HIGH)
        self.connection = serial.Serial(
            port=self.config.uart_port,
            baudrate=self.config.baud_rate,
            timeout=self.config.serial_timeout,
        )
        time.sleep(self.config.warmup_seconds)

    def close(self) -> None:
        if self.connection is not None:
            self.connection.close()
        if GPIO is not None:
            GPIO.cleanup()

    def read_currents(self) -> CurrentSample:
        values = {}
        for name in self.config.ordered_sensor_names():
            values[name] = self._read_sensor(name)
        for pin in self.config.rst_pins.values():
            GPIO.output(pin, GPIO.HIGH)
        return CurrentSample(currents=values, timestamp=time.time())

    def _read_sensor(self, name: str) -> float:
        for pin in self.config.rst_pins.values():
            GPIO.output(pin, GPIO.LOW)
        time.sleep(self.config.disable_delay_seconds)
        GPIO.output(self.config.rst_pins[name], GPIO.HIGH)
        time.sleep(self.config.settle_delay_seconds)
        self.connection.reset_input_buffer()
        time.sleep(self.config.buffer_delay_seconds)

        last_error = None
        for _ in range(self.config.read_attempts):
            line = self.connection.readline().decode("ascii", errors="ignore")
            try:
                value = parse_sensor_value(line)
            except ValueError as exc:
                last_error = exc
                value = None
            if value is not None:
                return value
        raise RuntimeError(f"Unable to read {name}: {last_error}")


def build_sensor_reader(config: AppConfig):
    if config.sensor_mode == "multi_usb":
        return MultiUSBSensorReader(config)
    if config.sensor_mode == "multiplexed_uart":
        return MultiplexedUARTSensorReader(config)
    raise ValueError(
        "Unsupported SENSOR_MODE. Use 'multiplexed_uart' or 'multi_usb'."
    )
