# prints offenders: non-resident GPU compute procs > 4GB
res=$(ss -tlnp 2>/dev/null | awk '$4 ~ /:8199$/' | grep -oP 'pid=\K[0-9]+' | head -1)
nvidia-smi --query-compute-apps=pid,used_memory --format=csv,noheader,nounits | awk -F', *' -v rp="$res" '$1!=rp && $2+0>4000 {print $1","$2}'
