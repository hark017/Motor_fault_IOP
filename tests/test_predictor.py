from pathlib import Path

from motor_fault.predictor import MotorFaultPredictor


def test_saved_models_can_run_inference():
    predictor = MotorFaultPredictor(Path(__file__).resolve().parent.parent)
    results = predictor.predict(-2.23046875, 0.51171875, 1.58984375)

    assert set(results) == {"binary", "severity", "phase", "load"}
    assert results["binary"].label in {"Healthy", "Faulty"}
    for result in results.values():
        assert isinstance(result.class_id, int)
        assert result.probabilities
