#!/bin/bash
gunicorn app.main:app \
  --workers 2 \
  --worker-class uvicorn.workers.UvicornWorker \
  --bind 0.0.0.0:$PORT \
  --timeout 600 \
  --access-logfile -