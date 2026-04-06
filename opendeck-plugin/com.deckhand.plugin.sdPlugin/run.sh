#!/bin/bash
DIR="$(cd "$(dirname "$0")" && pwd)"

# Optional: set DECKHAND_URL to connect to a remote Deckhand Core
# export DECKHAND_URL="http://192.168.1.100:8000"

python3 "$DIR/plugin.py" "$@"
