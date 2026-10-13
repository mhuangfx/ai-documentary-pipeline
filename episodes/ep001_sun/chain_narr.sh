#!/usr/bin/env bash
cd "$(dirname "$0")"
V="${HOST_RENDER_DIR:?set HOST_RENDER_DIR}"  # host renders (withheld)
log(){ echo "[$(date '+%F %T')] $*" >> logs/chain.log; }
log "waiting for CONFIRM_DONE"
until [ -f $V/renders/CONFIRM_DONE ]; do sleep 30; done
log "confirm done; waiting for GPU idle"
while true; do
  q=$(curl -s localhost:8199/queue | python3 -c "import json,sys;d=json.load(sys.stdin);print(len(d['queue_running'])+len(d['queue_pending']))")
  off=$(./gpu_free.sh)
  [ "$q" = "0" ] && [ -z "$off" ] && break
  sleep 30
done
log "GPU free; narration start"
../../pipeline/venv_tts/bin/python -u narration_gen.py > logs/narration_gen.log 2>&1
log "narration rc=$?"
