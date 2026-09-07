from __future__ import annotations
from pathlib import Path
import hashlib,json,zipfile,sys,tempfile,subprocess

path=Path(sys.argv[1])
errors=[]
with zipfile.ZipFile(path) as zf:
    names=zf.namelist()
    unsafe=[n for n in names if n.startswith('/') or '..' in Path(n).parts]
    if unsafe: errors.append({'unsafe_paths':unsafe})
    bad=zf.testzip()
    if bad: errors.append({'bad_entry':bad})
    tops={Path(n).parts[0] for n in names if Path(n).parts}
    if len(tops)!=1: errors.append({'top_level':sorted(tops)})
    with tempfile.TemporaryDirectory() as td:
        zf.extractall(td)
        root=Path(td)/next(iter(tops))
        manifest=root/'MANIFEST.sha256'
        if not manifest.exists(): errors.append({'manifest':'missing'})
        else:
            for line in manifest.read_text(encoding='utf-8').splitlines():
                sha,rel=line.split('  ',1)
                p=root/rel
                if not p.exists() or hashlib.sha256(p.read_bytes()).hexdigest()!=sha:
                    errors.append({'hash':rel})
        proc=subprocess.run([sys.executable,'-m','unittest','discover','-s','tests'],cwd=root,capture_output=True,text=True)
        if proc.returncode: errors.append({'tests':proc.stdout+proc.stderr})
report={'schema':'dikwp-commonbridge.release-verification/1.0','file':path.name,'size':path.stat().st_size,'sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'valid':not errors,'errors':errors}
print(json.dumps(report,ensure_ascii=False,indent=2))
raise SystemExit(1 if errors else 0)
