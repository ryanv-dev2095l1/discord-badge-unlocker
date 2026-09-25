import argparse
import json
import os
import sys
from pathlib import Path

from discord_api import fetch_user, BadTokenError, ALL_BADGES

def _load_token_file(path: str) -> str:
    p = Path(path).expanduser()
    if not p.exists():
        print(f"token file not found: {p}", file=sys.stderr)
        sys.exit(1)
    return p.read_text().strip()

def _print_table(accounts: list[dict]) -> None:
    if not accounts:
        print("no accounts configured. add one with --token-file")
        return

    headers = ["account", "username", "unlocked", "missing"]
    col_widths = [len(h) for h in headers]

    rows = []
    for acc in accounts:
        unlocked = acc.get("badges", [])
        missing = [b for b in ALL_BADGES if b not in unlocked]
        rows.append({
            "label": acc.get("label", "?"),
            "username": f"{acc['username']}#{acc['discriminator']}",
            "unlocked": ", ".join(unlocked) if unlocked else "(none)",
            "missing": ", ".join(missing) if missing else "(none)",
        })

    for r in rows:
        col_widths[0] = max(col_widths[0], len(r["label"]))
        col_widths[1] = max(col_widths[1], len(r["username"]))
        col_widths[2] = max(col_widths[2], len(r["unlocked"]))
        col_widths[3] = max(col_widths[3], len(r["missing"]))

    print(f"{'account':<{col_widths[0]}}  {'username':<{col_widths[1]}}  {'unlocked':<{col_widths[2]}}  {'missing':<{col_widths[3]}}")
    print("-" * (sum(col_widths) + 6))
    for r in rows:
        print(f"{r['label']:<{col_widths[0]}}  {r['username']:<{col_widths[1]}}  {r['unlocked']:<{col_widths[2]}}  {r['missing']:<{col_widths[3]}}")

def _print_compare(accounts: list[dict]) -> None:
    if len(accounts) < 2:
        print("need at least 2 accounts to compare")
        return

    all_sets = {acc["label"]: set(acc.get("badges", [])) for acc in accounts}
    labels = list(all_sets.keys())

    for i, a in enumerate(labels):
        for b in labels[i + 1:]:
            sa, sb = all_sets[a], all_sets[b]
            only_a = sa - sb
            only_b = sb - sa
            if only_a or only_b:
                print(f"{a} vs {b}:")
                if only_a:
                    print(f"  only {a}: {', '.join(sorted(only_a))}")
                if only_b:
                    print(f"  only {b}: {', '.join(sorted(only_b))}")
            else:
                print(f"{a} vs {b}: identical badges")

def _load_accounts(args) -> list[dict]:
    accounts = []
    token_files = []

    if args.token_file:
        token_files.extend(args.token_file)
    if args.token_files_dir:
        d = Path(args.token_files_dir).expanduser()
        if d.exists():
            token_files.extend(sorted(p for p in d.iterdir() if p.is_file() and not p.name.startswith(".")))

    for tf in token_files:
        try:
            token = _load_token_file(str(tf))
        except SystemExit:
            continue
        if not token:
            continue
        try:
            user = fetch_user(token)
        except BadTokenError:
            print(f"bad token in {tf}", file=sys.stderr)
            continue
        label = Path(tf).stem
        accounts.append({
            "label": label,
            **user,
        })

    return accounts

def main() -> int:
    parser = argparse.ArgumentParser(
        prog="unlocker",
        description="Track Discord badge unlocks across multiple accounts.",
        usage="python -m unlocker --token-file ~/.discord_token",
    )
    parser.add_argument(
        "--token-file",
        action="append",
        help="Path to file containing Discord token (can be given multiple times)",
    )
    parser.add_argument(
        "--token-files-dir",
        default=os.environ.get("UNLOCKER_TOKEN_DIR"),
        help="Directory of token files (env: UNLOCKER_TOKEN_DIR)",
    )
    parser.add_argument(
        "--token",
        default=os.environ.get("UNLOCKER_TOKEN"),
        help="Discord token directly (env: UNLOCKER_TOKEN)",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output raw JSON instead of table",
    )
    parser.add_argument(
        "--compare",
        action="store_true",
        help="Compare badges across all loaded accounts",
    )
    args = parser.parse_args()

    if not args.token and not args.token_file and not args.token_files_dir:
        print("set UNLOCKER_TOKEN or UNLOCKER_TOKEN_FILE, or pass --token/--token-file", file=sys.stderr)
        return 2

    accounts = []

    if args.token:
        try:
            user = fetch_user(args.token)
        except BadTokenError:
            print("invalid or expired token", file=sys.stderr)
            return 1
        accounts.append({"label": "default", **user})

    accounts.extend(_load_accounts(args))

    if args.compare:
        _print_compare(accounts)
        return 0

    if args.json:
        print(json.dumps(accounts, indent=2))
        return 0

    _print_table(accounts)
    return 0

if __name__ == "__main__":
    try:
        sys.exit(main() or 0)
    except KeyboardInterrupt:
        sys.exit(130)
