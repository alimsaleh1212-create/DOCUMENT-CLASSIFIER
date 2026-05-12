class FakePredictionService:
    def __init__(self):
        self.records = []
    def record_prediction(self, record):
        self.records.append(record.dict() if hasattr(record, 'dict') else record)