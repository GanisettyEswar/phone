#!/usr/bin/env bash
# Start Gunicorn with memory-optimized settings for Render free tier
# - Only 1 worker to save RAM (multiple workers = multiple copies of the model)
# - Increased timeout to 120s to prevent 502 on slow boots
gunicorn face_detection_system.wsgi:application --bind 0.0.0.0:$PORT --workers 1 --threads 8 --timeout 120
