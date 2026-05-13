from __future__ import annotations

import stat
from types import SimpleNamespace

from app.infra.sftp import SFTPClient


def file_entry(filename: str):
    return SimpleNamespace(filename=filename, st_mode=stat.S_IFREG)


def dir_entry(filename: str):
    return SimpleNamespace(filename=filename, st_mode=stat.S_IFDIR)


class FakeRemoteFile:
    def __init__(self, data: bytes) -> None:
        self.data = data

    def __enter__(self) -> "FakeRemoteFile":
        return self

    def __exit__(self, exc_type, exc, traceback) -> None:
        return None

    def read(self) -> bytes:
        return self.data


class FakeSFTPConnection:
    def __init__(self) -> None:
        self.closed = False
        self.created_dirs: list[str] = []
        self.renames: list[tuple[str, str]] = []

    def listdir_attr(self, directory: str):
        if directory == "incoming":
            return [dir_entry("batch"), file_entry("root.tif")]
        if directory == "incoming/batch":
            return [file_entry("nested.tif")]
        return []

    def open(self, remote_path: str, mode: str) -> FakeRemoteFile:
        return FakeRemoteFile(f"bytes:{remote_path}:{mode}".encode())

    def stat(self, directory: str) -> None:
        raise OSError("missing")

    def mkdir(self, directory: str) -> None:
        self.created_dirs.append(directory)

    def rename(self, source: str, target: str) -> None:
        self.renames.append((source, target))

    def close(self) -> None:
        self.closed = True


class FakeSSHConnection:
    def __init__(self) -> None:
        self.closed = False

    def close(self) -> None:
        self.closed = True


def make_client(sftp: FakeSFTPConnection, ssh: FakeSSHConnection) -> SFTPClient:
    client = SFTPClient("host", 22, "user", "password")
    client._connect = lambda: (ssh, sftp)  # type: ignore[method-assign]
    return client


def test_sftp_client_walks_incoming_files() -> None:
    sftp = FakeSFTPConnection()
    ssh = FakeSSHConnection()
    client = make_client(sftp, ssh)

    assert client._list_incoming_sync() == [
        "incoming/batch/nested.tif",
        "incoming/root.tif",
    ]
    assert sftp.closed is True
    assert ssh.closed is True


def test_sftp_client_fetches_bytes() -> None:
    client = make_client(FakeSFTPConnection(), FakeSSHConnection())

    assert client._fetch_sync("incoming/file.tif") == b"bytes:incoming/file.tif:rb"


def test_sftp_client_move_creates_target_dir_and_renames() -> None:
    sftp = FakeSFTPConnection()
    client = make_client(sftp, FakeSSHConnection())

    client._move_sync("incoming/batch/doc.tif", "processed")

    assert sftp.created_dirs == ["processed"]
    assert sftp.renames == [("incoming/batch/doc.tif", "processed/doc.tif")]
