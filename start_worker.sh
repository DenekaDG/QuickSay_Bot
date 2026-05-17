#!/bin/bash
cd ~/ai_voice_bot
source venv/bin/activate
celery -A tasks worker --loglevel=info --concurrency=1
