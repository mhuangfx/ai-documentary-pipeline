"""Compose an API-shaped full-episode request (system + user) for one dossier.
usage: python3 compose_full.py <round> <topic>  -> tests/prompt_tuning/r<round>/<topic>_request.txt
reads tools/prompts/test_inputs/<topic>_dossier.txt"""
import sys, pathlib
root = pathlib.Path(__file__).resolve().parents[2]
rnd, topic = sys.argv[1], sys.argv[2]
system = (root/'tools/prompts/script_writer_system.md').read_text()
system = '\n'.join(l for l in system.splitlines() if not l.startswith('# '))  # drop file-header comments
user = (root/'tools/prompts/script_writer_user.md').read_text().replace(
    '{DOSSIER}', (root/f'tools/prompts/test_inputs/{topic}_dossier.txt').read_text().strip())
out = root/f'tests/prompt_tuning/r{rnd}'; out.mkdir(parents=True, exist_ok=True)
(out/f'{topic}_request.txt').write_text(f'=== SYSTEM ===\n{system.strip()}\n\n=== USER ===\n{user.strip()}\n')
print(out/f'{topic}_request.txt')
