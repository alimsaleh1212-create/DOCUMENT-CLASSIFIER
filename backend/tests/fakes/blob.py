class FakeBlob:
    def __init__(self):
        self.store = {}
    def get(self, key):
        return self.store[key]
    def put(self, key, data):
        self.store[key] = data