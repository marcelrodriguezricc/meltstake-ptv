#!/usr/bin/env bash

# Resolve ROOT as two levels up from this script's location (~/meltstake-ptv)
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

# Defaults
DEBUG=""
CONFIG="default_config.toml"
DATA="$ROOT/data"

# Parse arguments
while [[ $# -gt 0 ]]; do
    case "$1" in
        --debug)
            DEBUG="--debug"
            shift
            ;;
        --config)
            CONFIG="$2"
            shift 2
            ;;
        --data)
            DATA="$2"
            shift 2
            ;;
        *)
            echo "Unknown argument: $1"
            echo "Usage: $0 [--debug] [--config <filename>] [--data <path>]"
            exit 1
            ;;
    esac
done

source "$ROOT/.venv/bin/activate"
python -m meltstake_ptv $DEBUG --config "configs/$CONFIG" --data "$DATA"