#!/bin/bash
docker exec memsearch memsearch index /home/pi-mono/.pi/agent/workspace/memory > /dev/null 2>&1
exec docker exec memsearch memsearch search "$@" -j
