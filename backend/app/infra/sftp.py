from __future__ import annotations

import asyncio
import posixpath
import stat
from collections.abc import Iterable

import paramiko


class SFTPClient:
    """SFTP client for ingesting scanned documents from the vendor drop folder."""

    def __init__(
        self,
        host: str,
        port: int,
        user: str,
        password: str,
        incoming_dir: str = "incoming",
        processed_dir: str = "processed",
        quarantine_dir: str = "quarantine",
    ) -> None:
        self._host = host
        self._port = port
        self._user = user
        self._password = password
        self._incoming_dir = incoming_dir
        self._processed_dir = processed_dir
        self._quarantine_dir = quarantine_dir

    async def list_incoming(self) -> list[str]:
        return await asyncio.to_thread(self._list_incoming_sync)

    async def fetch(self, remote_path: str) -> bytes:
        return await asyncio.to_thread(self._fetch_sync, remote_path)

    async def move_to_processed(self, remote_path: str) -> None:
        await asyncio.to_thread(self._move_sync, remote_path, self._processed_dir)

    async def move_to_quarantine(self, remote_path: str) -> None:
        await asyncio.to_thread(self._move_sync, remote_path, self._quarantine_dir)

    def _connect(self) -> tuple[paramiko.SSHClient, paramiko.SFTPClient]:
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(
            hostname=self._host,
            port=self._port,
            username=self._user,
            password=self._password,
            look_for_keys=False,
            allow_agent=False,
        )
        return ssh, ssh.open_sftp()

    def _list_incoming_sync(self) -> list[str]:
        ssh, sftp = self._connect()
        try:
            return list(self._walk_files(sftp, self._incoming_dir))
        finally:
            sftp.close()
            ssh.close()

    def _walk_files(self, sftp: paramiko.SFTPClient, directory: str) -> Iterable[str]:
        for entry in sftp.listdir_attr(directory):
            path = posixpath.join(directory, entry.filename)
            if self._is_directory(entry):
                yield from self._walk_files(sftp, path)
            else:
                yield path

    def _fetch_sync(self, remote_path: str) -> bytes:
        ssh, sftp = self._connect()
        try:
            with sftp.open(remote_path, "rb") as remote_file:
                return remote_file.read()
        finally:
            sftp.close()
            ssh.close()

    def _move_sync(self, remote_path: str, target_dir: str) -> None:
        ssh, sftp = self._connect()
        try:
            self._ensure_dir(sftp, target_dir)
            target_path = posixpath.join(target_dir, posixpath.basename(remote_path))
            sftp.rename(remote_path, target_path)
        finally:
            sftp.close()
            ssh.close()

    def _ensure_dir(self, sftp: paramiko.SFTPClient, directory: str) -> None:
        try:
            sftp.stat(directory)
        except OSError:
            sftp.mkdir(directory)

    @staticmethod
    def _is_directory(entry: paramiko.SFTPAttributes) -> bool:
        return entry.st_mode is not None and stat.S_ISDIR(entry.st_mode)
