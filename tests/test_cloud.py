from motor_fault.cloud import ThingSpeakUploader
from motor_fault.predictor import PredictionResult


class DummyResponse:
    def __init__(self, status_code=200, text="1"):
        self.status_code = status_code
        self.text = text


def test_thingspeak_payload_shape():
    captured = {}

    def fake_get(url, params, timeout):
        captured["url"] = url
        captured["params"] = params
        captured["timeout"] = timeout
        return DummyResponse()

    uploader = ThingSpeakUploader(
        api_key="TEST_KEY",
        url="https://api.thingspeak.com/update",
        min_interval_seconds=0.0,
        request_get=fake_get,
    )
    predictions = {
        "binary": PredictionResult("binary", 1, "Faulty", {0: 0.1, 1: 0.9}),
        "severity": PredictionResult("severity", 2, "3u", {2: 0.8}),
        "phase": PredictionResult("phase", 3, "Phase 3", {3: 0.7}),
        "load": PredictionResult("load", 1, "Half Load", {1: 0.95}),
    }

    ok = uploader.upload({"I1": 1.0, "I2": 2.0, "I3": 3.0}, predictions)

    assert ok is True
    assert captured["params"]["field1"] == "1.000"
    assert captured["params"]["field7"] == 1
