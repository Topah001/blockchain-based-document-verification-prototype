"""CLI for recording and checking document hashes in the local ledger."""

from __future__ import annotations

import argparse

from .ledger import Ledger, LedgerError


def main() -> int:
    parser = argparse.ArgumentParser(description="Record document hashes in a local hash chain.")
    parser.add_argument("--ledger", default="ledger.jsonl", help="ledger JSONL path")
    subparsers = parser.add_subparsers(dest="command", required=True)
    add_parser = subparsers.add_parser("add", help="record a file's SHA-256 hash")
    add_parser.add_argument("file")
    subparsers.add_parser("verify", help="validate every stored chain link and entry hash")
    document_parser = subparsers.add_parser("verify-document", help="compare file content to entry")
    document_parser.add_argument("index", type=int)
    document_parser.add_argument("file")
    args = parser.parse_args()
    ledger = Ledger(args.ledger)
    try:
        if args.command == "add":
            with open(args.file, "rb") as source:
                entry = ledger.add_document(source.read())
            print(f"recorded entry {entry.index}: {entry.document_sha256}")
            return 0
        if args.command == "verify":
            result = ledger.verify()
            print(result.message)
            return 0 if result.valid else 1
        with open(args.file, "rb") as source:
            matches = ledger.verify_document(args.index, source.read())
        print("document matches ledger entry" if matches else "document does not match ledger entry")
        return 0 if matches else 1
    except (OSError, LedgerError) as error:
        parser.error(str(error))
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
