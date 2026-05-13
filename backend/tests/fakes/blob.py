class FakeBlob:
    def __init__(self) -> None:
        self.store: dict[str, bytes] = {}
    def get(self, key: str) -> bytes:
        return self.store[key]
    def put(self, key: str, data: bytes) -> None:
        self.store[key] = data
