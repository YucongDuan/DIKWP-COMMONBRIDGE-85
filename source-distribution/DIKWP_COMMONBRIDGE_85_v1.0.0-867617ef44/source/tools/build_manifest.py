from __future__ import annotations
from pathlib import Path
import hashlib

ROOT=Path(__file__).resolve().parent.parent
out=ROOT/'MANIFEST.sha256'
exclude={out.resolve()}
rows=[]
for p in sorted(ROOT.rglob('*')):
    if not p.is_file() or p.resolve() in exclude:
        continue
    rel=p.relative_to(ROOT).as_posix()
    if rel.startswith(('var/','outputs/')) and p.name!='.gitkeep':
        continue
    if '__pycache__' in rel or rel.endswith('.pyc'):
        continue
    rows.append(f"{hashlib.sha256(p.read_bytes()).hexdigest()}  {rel}")
out.write_text('\n'.join(rows)+'\n',encoding='utf-8')
print(f"{len(rows)} files -> {out}")
