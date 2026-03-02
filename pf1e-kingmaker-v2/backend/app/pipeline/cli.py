"""CLI entrypoint for deterministic ingestion pipeline."""

from __future__ import annotations

import argparse
from pathlib import Path

from app.pipeline.extract import run_extract
from app.pipeline.load import run_load
from app.pipeline.parse import run_parse
from app.pipeline.validate import run_validate


def _cmd_extract(args: argparse.Namespace) -> None:
    run_path = run_extract(
        source=args.source,
        run_dir=Path(args.run_dir),
        input_path=Path(args.input) if args.input else None,
        run_key=args.run_key,
        mode=args.mode,
        psrd_root=Path(args.psrd_root) if args.psrd_root else None,
        d20_root=Path(args.d20_root) if args.d20_root else None,
        aon_timeout=args.aon_timeout,
        aon_max_retries=args.aon_max_retries,
        ai_short_fallback=args.ai_short_fallback,
        aon_offline_html_dir=Path(args.aon_offline_html_dir) if args.aon_offline_html_dir else None,
        catalog_kind=args.catalog_kind,
        catalog_limit=args.catalog_limit,
    )
    print(f"extract completed: {run_path}")


def _cmd_parse(args: argparse.Namespace) -> None:
    out = run_parse(Path(args.run))
    print(f"parse completed: {out}")


def _cmd_validate(args: argparse.Namespace) -> None:
    out = run_validate(Path(args.run))
    print(f"validate completed: {out}")


def _cmd_load(args: argparse.Namespace) -> None:
    result = run_load(Path(args.run), args.dsn)
    print("load completed:")
    for key, value in result.items():
        print(f"  {key}: {value}")


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="PF1e V2 deterministic ingestion pipeline")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_extract = sub.add_parser("extract", help="Extract source records")
    p_extract.add_argument("--source", choices=["aon", "psrd", "d20"], required=True)
    p_extract.add_argument("--run-dir", default="./runs")
    p_extract.add_argument("--input", default=None, help="Path to JSON list input")
    p_extract.add_argument("--run-key", default=None)
    p_extract.add_argument(
        "--mode",
        choices=["aon_live", "aon_catalog", "kairon_slice", "kairon_fixture"],
        default="kairon_slice",
        help="aon_live fetches Kairon slice AON pages; aon_catalog expands AON catalog; kairon_slice reads source data roots; kairon_fixture uses built-in fixtures",
    )
    p_extract.add_argument("--psrd-root", default=None, help="Path to PSRD sqlite book-*.db directory")
    p_extract.add_argument("--d20-root", default=None, help="Path to d20pfsrd data directory")
    p_extract.add_argument("--aon-timeout", type=int, default=20, help="AON page fetch timeout in seconds")
    p_extract.add_argument("--aon-max-retries", type=int, default=1, help="Retries per AON page")
    p_extract.add_argument(
        "--ai-short-fallback",
        action="store_true",
        help="Generate short descriptions with AI when missing (heuristic fallback always available)",
    )
    p_extract.add_argument(
        "--aon-offline-html-dir",
        default=None,
        help="Directory with pre-cached AON HTML files named by URL SHA256, for offline deterministic runs",
    )
    p_extract.add_argument(
        "--catalog-kind",
        choices=["all", "classes", "feats", "spells"],
        default="all",
        help="When mode=aon_catalog, choose which catalog families to expand",
    )
    p_extract.add_argument(
        "--catalog-limit",
        type=int,
        default=0,
        help="When mode=aon_catalog, cap number of fetched detail pages per family (0 = no cap)",
    )
    p_extract.set_defaults(func=_cmd_extract)

    p_parse = sub.add_parser("parse", help="Normalize extracted records")
    p_parse.add_argument("--run", required=True)
    p_parse.set_defaults(func=_cmd_parse)

    p_validate = sub.add_parser("validate", help="Validate parsed records")
    p_validate.add_argument("--run", required=True)
    p_validate.set_defaults(func=_cmd_validate)

    p_load = sub.add_parser("load", help="Load validated records")
    p_load.add_argument("--run", required=True)
    p_load.add_argument("--dsn", required=True, help="sqlite:///path.db or postgres DSN")
    p_load.set_defaults(func=_cmd_load)

    return parser


def main() -> None:
    parser = _build_parser()
    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
