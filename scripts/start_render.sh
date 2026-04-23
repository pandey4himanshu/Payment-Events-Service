#!/usr/bin/env bash
set -e

PYTHONPATH=. python scripts/seed_if_empty.py
uvicorn app.main:app --host 0.0.0.0 --port "${PORT:-8000}"
