#!/bin/sh
# Ensure the docscanner user owns the incoming directory inside the chroot.
# Docker volumes are created with root ownership; this script fixes that
# on every container start so the user can write incoming files.
#
# Also pre-create the processed/ and quarantine/ directories that sftp-ingest
# moves files into. The chroot root (/home/docscanner) is root-owned and
# unwritable, so the worker cannot mkdir these itself.
set -e
# The volume is mounted at /home/docscanner (the chroot root). Create each
# subdir if missing and make sure docscanner owns it. The chroot root itself
# stays root-owned (required by sshd's ChrootDirectory).
for d in incoming processed quarantine; do
  mkdir -p "/home/docscanner/$d"
  chown 1001:100 "/home/docscanner/$d"
  chmod 755 "/home/docscanner/$d"
done
