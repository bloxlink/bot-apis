#!/bin/sh
source .venv/bin/activate
ssh -R bot-api-local.blox.link:80:localhost:8000 localhost.run &
python3.12 run_apps.py