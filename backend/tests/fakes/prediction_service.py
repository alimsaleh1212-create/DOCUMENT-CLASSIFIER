""" tests/fakes/prediction_service.py — Fake prediction recorder. """
from backend.app.domain.contracts import PredictionOut

class FakePredictionService:
    def __init__(self):
        self.records: list[PredictionOut] = []

    def record_prediction(self, record: PredictionOut) -> None:
        self.records.append(record)