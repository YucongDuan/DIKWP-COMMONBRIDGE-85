from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

from .core import (
    compile_capsule,
    route_capsule,
    record_contribution,
    issue_true_value_receipt,
    create_exchange_bundle,
    verify_exchange_bundle,
    generate_open_calls,
    summary,
)
from .server import serve


def load(path: str | Path) -> dict:
    obj = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(obj, dict):
        raise ValueError(f"{path}: JSON object required")
    return obj


def dump(obj: object, path: str | Path | None = None) -> None:
    text = json.dumps(obj, ensure_ascii=False, indent=2) + "\n"
    if path:
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        Path(path).write_text(text, encoding="utf-8")
        print(path)
    else:
        print(text, end="")


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="commonbridge85", description="Capability-neutral DIKWP cooperation runtime")
    sub = p.add_subparsers(dest="cmd", required=True)

    sub.add_parser("summary")

    c = sub.add_parser("create-capsule")
    c.add_argument("input")
    c.add_argument("--out")

    r = sub.add_parser("route")
    r.add_argument("capsule")
    r.add_argument("profile")
    r.add_argument("--out")

    co = sub.add_parser("contribute")
    co.add_argument("capsule")
    co.add_argument("route")
    co.add_argument("contribution")
    co.add_argument("--out")

    vr = sub.add_parser("value-receipt")
    vr.add_argument("contribution")
    vr.add_argument("outcome")
    vr.add_argument("--out")

    b = sub.add_parser("bundle")
    b.add_argument("capsule")
    b.add_argument("route")
    b.add_argument("--contribution", action="append", default=[])
    b.add_argument("--receipt", action="append", default=[])
    b.add_argument("--out", required=True)

    vb = sub.add_parser("verify-bundle")
    vb.add_argument("bundle")

    oc = sub.add_parser("open-calls")
    oc.add_argument("--capsules", nargs="*", default=[])
    oc.add_argument("--routes", nargs="*", default=[])
    oc.add_argument("--contributions", nargs="*", default=[])
    oc.add_argument("--out")

    s = sub.add_parser("serve")
    s.add_argument("--host", default="127.0.0.1")
    s.add_argument("--port", type=int, default=8784)
    s.add_argument("--db")

    args = p.parse_args(argv)
    root = Path(__file__).resolve().parent.parent

    if args.cmd == "summary":
        dump(summary())
    elif args.cmd == "create-capsule":
        dump(compile_capsule(load(args.input)), args.out)
    elif args.cmd == "route":
        dump(route_capsule(load(args.capsule), load(args.profile)), args.out)
    elif args.cmd == "contribute":
        dump(record_contribution(load(args.capsule), load(args.route), load(args.contribution)), args.out)
    elif args.cmd == "value-receipt":
        dump(issue_true_value_receipt(load(args.contribution), load(args.outcome)), args.out)
    elif args.cmd == "bundle":
        result = create_exchange_bundle(
            load(args.capsule),
            load(args.route),
            args.out,
            [load(x) for x in args.contribution],
            [load(x) for x in args.receipt],
        )
        dump(result)
    elif args.cmd == "verify-bundle":
        dump(verify_exchange_bundle(args.bundle))
    elif args.cmd == "open-calls":
        obj = generate_open_calls(
            [load(x) for x in args.capsules],
            [load(x) for x in args.routes],
            [load(x) for x in args.contributions],
        )
        dump(obj, args.out)
    elif args.cmd == "serve":
        serve(root, args.host, args.port, args.db)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
