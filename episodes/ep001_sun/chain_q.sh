#!/usr/bin/env bash
cd "$(dirname "$0")"
until grep -q "narration rc" logs/chain.log; do sleep 20; done
echo "[$(date '+%F %T')] queue start" >> logs/chain.log
python3 -u queue_run.py >> logs/queue_run.log 2>&1
echo "[$(date '+%F %T')] queue exit" >> logs/chain.log
