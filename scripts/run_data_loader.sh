#!/bin/bash
# Wrapper script to run data loader with venv

cd /home/ts/MIG/prod-grade
source venv/bin/activate
python3 scripts/load_real_data_chunked.py
