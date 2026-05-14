#!/bin/sh
# Ensure the docscanner user owns the incoming directory inside the chroot.
# Docker volumes are created with root ownership; this script fixes that
# on every container start so the user can write incoming files.
set -e
chown -R 1001:100 /home/docscanner/incoming
chmod 755 /home/docscanner/incoming
