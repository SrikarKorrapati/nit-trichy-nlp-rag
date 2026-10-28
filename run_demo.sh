#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
python3 scripts/use_demo_data.py
exec python3 -m streamlit run app.py --server.headless true --server.port 8501
