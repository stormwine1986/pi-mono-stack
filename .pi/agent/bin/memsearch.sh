#!/bin/bash
exec docker exec memsearch memsearch search "$@" -j
