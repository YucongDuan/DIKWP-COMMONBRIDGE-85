from __future__ import annotations

from pathlib import Path
import json
import re
import sys

ROOT = Path(__file__).resolve().parent.parent
checks: list[tuple[str, bool, str]] = []

def add(name: str, ok: bool, detail: str = "") -> None:
    checks.append((name, ok, detail))

required = [
    "README.md", "README.zh-CN.md", "LICENSE", "NOTICE", "CITATION.cff",
    "index.html", "assets/styles.css", "assets/app.js", "commonbridge85/core.py",
    "commonbridge85/server.py", "commonbridge85/store.py", "run.py", "start_showcase.py",
    "TRUE_VALUE_CHARTER.md", "POLICY_PROFILE_GUIDE.md", "ATTENTION_AND_GATEKEEPER_THREAT_MODEL.md",
]
for item in required:
    add(f"required:{item}", (ROOT / item).exists())

all_text = "\n".join(
    p.read_text(encoding="utf-8", errors="ignore")
    for p in ROOT.rglob("*")
    if p.is_file() and p.suffix.lower() in {".py", ".js", ".html", ".md", ".json", ".yml", ".yaml", ".txt", ".toml"}
)

add("no_eval_js", "eval(" not in (ROOT / "assets/app.js").read_text(encoding="utf-8"))
add("no_external_cdn", not re.search(r"https?://[^\"']+(?:\.js|\.css)", (ROOT / "index.html").read_text(encoding="utf-8")))
add("person_grade_absent", "person_grade_absent" in all_text)
add("social_credit_false", "social_credit" in all_text and "false" in all_text.lower())
add("no_circumvention_boundary", "bypass_controls" in all_text and "network_circumvention" in all_text)
add("manual_fallback", "manual_fallback" in all_text)
add("true_value_nonfinancial", "financial_asset" in all_text and "transferable" in all_text)
add("generated_label_boundary", "generated_content_label_required" in all_text)
add("no_shell_runtime", "subprocess" not in (ROOT / "commonbridge85/core.py").read_text(encoding="utf-8"))
code_text = "\n".join(p.read_text(encoding="utf-8", errors="ignore") for p in (ROOT / "commonbridge85").glob("*.py"))
add("no_requests_dependency", "import requests" not in code_text and "from requests" not in code_text)
add("github_current_snapshot", '"public_repositories": 363' in (ROOT / "data/portfolio_snapshot_2026-08-18.json").read_text(encoding="utf-8"))

schemas = list((ROOT / "schemas").glob("*.json"))
for schema in schemas:
    try:
        json.loads(schema.read_text(encoding="utf-8"))
        add(f"json:{schema.name}", True)
    except Exception as exc:
        add(f"json:{schema.name}", False, str(exc))

failed = [x for x in checks if not x[1]]
report = {"suite": "static_audit", "passed": len(checks)-len(failed), "total": len(checks), "failed": [{"name":x[0],"detail":x[2]} for x in failed]}
print(json.dumps(report, ensure_ascii=False, indent=2))
sys.exit(1 if failed else 0)
