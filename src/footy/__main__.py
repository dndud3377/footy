"""footy CLI

    python -m footy ingest [--full]   수집 → 통합 → 검증 보고서
    python -m footy build             data/raw → data/processed 재생성만
    python -m footy check [--strict]  검증 보고서만
"""
from __future__ import annotations

import argparse
import json
import sys


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="footy")
    sub = p.add_subparsers(dest="cmd", required=True)
    pi = sub.add_parser("ingest")
    pi.add_argument("--full", action="store_true", help="지난 시즌까지 전부 다시 수집")
    sub.add_parser("build")
    pc = sub.add_parser("check")
    pc.add_argument("--strict", action="store_true")
    a = p.parse_args(argv)

    if a.cmd == "ingest":
        from .build import build
        from .check import run as check
        from .ingest.run import run as ingest

        log = ingest(full=a.full)
        print(json.dumps({k: v for k, v in log.items() if k != "skipped"}, ensure_ascii=False, indent=2))
        print(json.dumps(build(), ensure_ascii=False))
        return check(strict=False)
    if a.cmd == "build":
        from .build import build

        print(json.dumps(build(), ensure_ascii=False))
        return 0
    if a.cmd == "check":
        from .check import run as check

        return check(strict=a.strict)
    return 2


if __name__ == "__main__":
    sys.exit(main())
