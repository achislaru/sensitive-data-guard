"""sdg command-line interface.

Exit codes: 0 = ok; 2 = refusal/hard stop (preflight refused, outbound PII
guard tripped, classification/path conflict). The agent MUST treat exit != 0
as a hard stop.
"""
import argparse
import json
import re
import sys

from . import __version__, paths


def _read(path: str) -> str:
    if path == "-":
        return sys.stdin.read()
    with open(path, encoding="utf-8") as f:
        return f.read()


def _is_csv(path: str, flag: bool) -> bool:
    return flag or path.lower().endswith(".csv")


def _pii_counts(spans) -> dict:
    out = {}
    for d in spans:
        out[d.entity_type] = out.get(d.entity_type, 0) + 1
    return out


# ----------------------------------------------------------------- commands

def _cmd_version(args):
    print(__version__)
    return 0


def _cmd_packs(args):
    from .packs.registry import available_locales
    print(json.dumps({"locales": available_locales()}))
    return 0


def _cmd_detect(args):
    from .detect import detect
    spans = detect(_read(args.file), locale=args.locale,
                   is_csv=_is_csv(args.file, args.csv))
    out = [{"type": d.entity_type, "start": d.start, "end": d.end,
            "score": round(d.score, 2)} for d in spans]
    print(json.dumps({"count": len(out), "spans": out}, ensure_ascii=False))
    return 0


def _cmd_classify(args):
    from .classify import classify_text
    res = classify_text(_read(args.file), locale=args.locale,
                        is_csv=_is_csv(args.file, args.csv))
    print(json.dumps(res, ensure_ascii=False))
    return 0


def _cmd_certify(args):
    from . import certify
    pp = certify.certify(run_benchmark=not args.no_benchmark, local_model=args.model)
    summary = {
        "machine_id": pp["machine_id"], "expires": pp["expires"],
        "paths_enabled": pp["paths_enabled"],
        "components": {k: v.get("status") for k, v in pp["components"].items()},
        "machine": {k: v.get("status") for k, v in pp["machine"].items()},
        "packs": {k: v.get("self_test") for k, v in pp["packs"].items()},
    }
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


def _cmd_preflight(args):
    from .guard import preflight
    res = preflight()
    print(json.dumps(res, ensure_ascii=False))
    return 0 if res["ok"] else 2


def _session_vault(session: str, locale: str):
    from .packs.registry import load_pack
    from .vault import Vault
    paths.ensure_state()
    db = paths.SESSIONS_DIR / f"{re.sub(r'[^A-Za-z0-9_-]', '_', session)}.db"
    return Vault(db=db, key=paths.VAULT_KEY, label_map=load_pack(locale).label_map)


def _cmd_pseudonymize(args):
    from .pipeline import OutboundPiiError, pseudonymize
    text = _read(args.file)
    vault = _session_vault(args.session, args.locale)
    try:
        out = pseudonymize(text, vault, locale=args.locale,
                           is_csv=_is_csv(args.file, args.csv))
    except OutboundPiiError as e:
        print(f"HARD STOP: {e}", file=sys.stderr)
        return 2
    if args.out and args.out != "-":
        with open(args.out, "w", encoding="utf-8") as f:
            f.write(out)
    else:
        sys.stdout.write(out)
    return 0


def _cmd_restore(args):
    vault = _session_vault(args.session, args.locale)
    out = vault.restore(_read(args.file))
    if args.out and args.out != "-":
        with open(args.out, "w", encoding="utf-8") as f:
            f.write(out)
    else:
        sys.stdout.write(out)
    return 0


def _cmd_protocol(args):
    from .protocols import engine, linter, loader
    sub = args.protocol_cmd
    if sub == "list":
        print(json.dumps(loader.list_protocols(), ensure_ascii=False, indent=2))
        return 0
    if sub == "validate":
        p = loader.load_file(__import__("pathlib").Path(args.file)) if args.file \
            else loader.load(args.id)
        errors, warnings = linter.validate(p)
        print(json.dumps({"ok": not errors, "errors": errors,
                          "warnings": warnings}, ensure_ascii=False, indent=2))
        return 0 if not errors else 2
    if sub == "dryrun":
        res = engine.dryrun(args.id, locale=args.locale)
        print(json.dumps(res, ensure_ascii=False, indent=2))
        return 0 if res.get("ok") else 2
    if sub == "run":
        params = dict(kv.split("=", 1) for kv in (args.param or []))
        try:
            res = engine.run(args.id, _read(args.file), args.session,
                             locale=args.locale, params=params,
                             is_csv=_is_csv(args.file, args.csv),
                             source_channel=args.channel)
        except engine.ProtocolError as e:
            print(f"HARD STOP: {e}", file=sys.stderr)
            return 2
        print(json.dumps(res, ensure_ascii=False))
        return 0
    if sub == "resume":
        try:
            res = engine.resume(args.session, _read(args.output))
        except engine.ProtocolError as e:
            print(f"HARD STOP: {e}", file=sys.stderr)
            return 2
        print(json.dumps(res, ensure_ascii=False))
        return 0
    if sub == "new":
        print(loader.TEMPLATE_PATH.read_text(encoding="utf-8"))
        return 0
    if sub == "export":
        p = loader.load(args.id)
        text = __import__("yaml").safe_dump(p, sort_keys=False, allow_unicode=True)
        print(text + f"# sdg-checksum: {loader.checksum(p)}")
        return 0
    if sub == "import":
        from pathlib import Path as _P
        p = loader.load_file(_P(args.file))
        errors, warnings = linter.validate(p)
        if errors:
            print(json.dumps({"imported": False, "errors": errors}), file=sys.stderr)
            return 2
        dry = engine.dryrun(p["id"], locale=p["locale_scope"][0])
        if not dry.get("ok"):
            print(json.dumps({"imported": False, "dryrun": dry}), file=sys.stderr)
            return 2
        dest = loader.user_dir() / f"{p['id']}.yaml"
        dest.write_text(_P(args.file).read_text(encoding="utf-8"), encoding="utf-8")
        print(json.dumps({"imported": True, "path": str(dest),
                          "warnings": warnings}))
        return 0
    return 1


def _cmd_audit(args):
    from . import audit
    if args.audit_cmd == "retention":
        print(json.dumps(audit.apply_retention(), ensure_ascii=False))
    elif args.audit_cmd == "summary":
        print(json.dumps(audit.monthly_summary(args.month), ensure_ascii=False,
                         indent=2))
    elif args.audit_cmd == "log":
        types = json.loads(args.types) if args.types else {}
        audit.log_interaction(args.user, args.category, args.path, types,
                              source_channel=args.channel,
                              protocol_id=args.protocol, source_file=args.file or "",
                              model=args.model or "")
        print(json.dumps({"logged": True}))
    return 0


# ----------------------------------------------------------------- parser

def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="sdg", description="sensitive-data-guard")
    p.add_argument("--locale", default="ro_RO", help="country pack locale")
    sub = p.add_subparsers(dest="cmd", required=True)

    sub.add_parser("version").set_defaults(func=_cmd_version)
    sub.add_parser("packs").set_defaults(func=_cmd_packs)

    d = sub.add_parser("detect", help="detect PII (file or - for stdin)")
    d.add_argument("--file", required=True)
    d.add_argument("--csv", action="store_true")
    d.set_defaults(func=_cmd_detect)

    c = sub.add_parser("classify", help="classify data + allowed paths")
    c.add_argument("--file", required=True)
    c.add_argument("--csv", action="store_true")
    c.set_defaults(func=_cmd_classify)

    cert = sub.add_parser("certify", help="audit machine + write passport")
    cert.add_argument("--no-benchmark", action="store_true")
    cert.add_argument("--model", default="gemma3:27b")
    cert.set_defaults(func=_cmd_certify)

    sub.add_parser("preflight", help="verify passport, return enabled paths") \
        .set_defaults(func=_cmd_preflight)

    ps = sub.add_parser("pseudonymize", help="pseudonymize a file (fail-closed)")
    ps.add_argument("--file", required=True)
    ps.add_argument("--session", required=True)
    ps.add_argument("--csv", action="store_true")
    ps.add_argument("--out", default="-")
    ps.set_defaults(func=_cmd_pseudonymize)

    rs = sub.add_parser("restore", help="restore real values in a response")
    rs.add_argument("--file", required=True)
    rs.add_argument("--session", required=True)
    rs.add_argument("--out", default="-")
    rs.set_defaults(func=_cmd_restore)

    pr = sub.add_parser("protocol", help="work-protocol library")
    prsub = pr.add_subparsers(dest="protocol_cmd", required=True)
    prsub.add_parser("list")
    pv = prsub.add_parser("validate")
    pv.add_argument("--id"); pv.add_argument("--file")
    pd = prsub.add_parser("dryrun"); pd.add_argument("--id", required=True)
    prun = prsub.add_parser("run")
    prun.add_argument("--id", required=True)
    prun.add_argument("--file", required=True)
    prun.add_argument("--session", required=True)
    prun.add_argument("--param", action="append", help="key=value (repeatable)")
    prun.add_argument("--csv", action="store_true")
    prun.add_argument("--channel", default="cli")
    pres = prsub.add_parser("resume")
    pres.add_argument("--session", required=True)
    pres.add_argument("--output", required=True, help="AI output file or -")
    prsub.add_parser("new")
    pe = prsub.add_parser("export"); pe.add_argument("--id", required=True)
    pi = prsub.add_parser("import"); pi.add_argument("--file", required=True)
    pr.set_defaults(func=_cmd_protocol)

    au = sub.add_parser("audit", help="audit log / retention / summary")
    ausub = au.add_subparsers(dest="audit_cmd", required=True)
    al = ausub.add_parser("log")
    al.add_argument("--user", required=True)
    al.add_argument("--category", required=True)
    al.add_argument("--path", required=True)
    al.add_argument("--types", help='JSON like {"RO_CNP":20}')
    al.add_argument("--channel", default="cli")
    al.add_argument("--protocol", default="")
    al.add_argument("--file", default="")
    al.add_argument("--model", default="")
    ausub.add_parser("retention")
    asum = ausub.add_parser("summary")
    asum.add_argument("--month", required=True, help="YYYY-MM")
    au.set_defaults(func=_cmd_audit)

    return p


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
