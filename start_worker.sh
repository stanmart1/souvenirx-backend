#!/bin/bash
set -e

echo "Starting SouvenirX ARQ Worker..."
exec arq app.arq_worker.WorkerSettings
