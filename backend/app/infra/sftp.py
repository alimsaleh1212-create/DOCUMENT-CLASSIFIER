class SFTPClient:
    """SFTP client for ingesting scanned documents from the vendor drop folder."""

    def __init__(self, host: str, port: int, user: str, password: str) -> None:
        self._host = host
        self._port = port
        self._user = user
        self._password = password

    async def list_incoming(self) -> list[str]:
        raise NotImplementedError

    async def fetch(self, remote_path: str) -> bytes:
        raise NotImplementedError

    async def move_to_processed(self, remote_path: str) -> None:
        raise NotImplementedError

    async def move_to_quarantine(self, remote_path: str) -> None:
        raise NotImplementedError
