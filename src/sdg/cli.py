"""sdg command-line interface.

F1 ships a minimal surface (version, detect, packs); certify/preflight/
pseudonymize/restore/audit/protocol are wired in later phases. Exit code != 0
always means a hard stop (e.g. outbound PII guard tripped).
"""
import argparse
import json
import sys

from . import __version__


def _cmd_version(args):
    print(__version__)
    return 0


def _cmd_packs(args):
    from .packs.registry import available_locales
    print(json.dumps({"locales": available_locales()}))
    return 0


def _cmd_detect(args):
    from .detect import detect
    text = sys.stdin.read() if args.file == "-" else open(args.file, encoding="utf-8").read()
    spans = detect(text, locale=args.locale, is_csv=args.csv)
    out = [{"type": d.entity_type, "start": d.start, "end": d.end,
            "score": round(d.score, 2)} for d in spans]
    print(json.dumps({"count": len(out), "spans": out}, ensure_ascii=False))
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="sdg", description="sensitive-data-guard")
    sub = p.add_subparsers(dest="cmd", required=True)

    sub.add_parser("version", help="print version").set_defaults(func=_cmd_version)
    sub.add_parser("packs", help="list installed country packs").set_defaults(func=_cmd_packs)

    d = sub.add_parser("detect", help="detect PII in a file (or - for stdin)")
    d.add_argument("--file", required=True)
    d.add_argument("--locale", default="ro_RO")
    d.add_argument("--csv", action="store_true", help="treat input as tabular CSV")
    d.set_defaults(func=_cmd_detect)

    return p


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
