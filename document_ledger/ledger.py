"""A local append-only hash chain that records document digests, not documents."""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

GENESIS_HASH = "0" * 64


class LedgerError(ValueError):
    """Raised when ledger data cannot be read or safely appended."""


@dataclass(frozen=True, slots=True)
class LedgerEntry:
    index: int
    document_sha256: str
    previous_hash: str
    recorded_at: str
    entry_hash: str


@dataclass(frozen=True, slots=True)
class VerificationResult:
    valid: bool
    checked_entries: int
    message: str


def _canonical_bytes(data: dict[str, object]) -> bytes:
    return json.dumps(data, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode(
        "utf-8"
    )


def _entry_digest(data: dict[str, object]) -> str:
    return hashlib.sha256(_canonical_bytes(data)).hexdigest()


class Ledger:
    """JSON Lines ledger; only SHA-256 digests and chain metadata are persisted."""

    def __init__(self, path: str | Path):
        self.path = Path(path)

    def entries(self) -> list[LedgerEntry]:
        if not self.path.exists():
            return []
        result: list[LedgerEntry] = []
        try:
            with self.path.open("r", encoding="utf-8") as stream:
                for line_number, line in enumerate(stream, 1):
                    if not line.strip():
                        raise LedgerError(f"line {line_number}: blank lines are not valid entries")
                    try:
                        raw = json.loads(line)
                        if not isinstance(raw, dict):
                            raise TypeError("entry must be an object")
                        result.append(LedgerEntry(**raw))
                    except (json.JSONDecodeError, TypeError, ValueError) as error:
                        raise LedgerError(f"line {line_number}: invalid entry: {error}") from error
        except UnicodeError as error:
            raise LedgerError(f"ledger is not valid UTF-8: {error}") from error
        return result

    def add_document(self, content: bytes) -> LedgerEntry:
        existing = self.entries()
        verification = self.verify_entries(existing)
        if not verification.valid:
            raise LedgerError(f"refusing to append to invalid ledger: {verification.message}")
        previous = existing[-1].entry_hash if existing else GENESIS_HASH
        payload: dict[str, object] = {
            "index": len(existing),
            "document_sha256": hashlib.sha256(content).hexdigest(),
            "previous_hash": previous,
            "recorded_at": datetime.now(timezone.utc).isoformat(),
        }
        entry = LedgerEntry(**payload, entry_hash=_entry_digest(payload))
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("a", encoding="utf-8", newline="\n") as stream:
            stream.write(json.dumps(asdict(entry), sort_keys=True, ensure_ascii=False) + "\n")
        return entry

    def verify(self) -> VerificationResult:
        try:
            entries = self.entries()
        except LedgerError as error:
            return VerificationResult(False, 0, str(error))
        return self.verify_entries(entries)

    @staticmethod
    def verify_entries(entries: Iterable[LedgerEntry]) -> VerificationResult:
        previous = GENESIS_HASH
        count = 0
        for expected_index, entry in enumerate(entries):
            count += 1
            if entry.index != expected_index:
                return VerificationResult(
                    False, count, f"entry {expected_index}: unexpected index {entry.index}"
                )
            if entry.previous_hash != previous:
                return VerificationResult(
                    False, count, f"entry {expected_index}: previous-hash link does not match"
                )
            if not _is_sha256(entry.document_sha256):
                return VerificationResult(
                    False, count, f"entry {expected_index}: invalid document SHA-256 digest"
                )
            payload: dict[str, object] = {
                "index": entry.index,
                "document_sha256": entry.document_sha256,
                "previous_hash": entry.previous_hash,
                "recorded_at": entry.recorded_at,
            }
            if not _is_sha256(entry.entry_hash) or _entry_digest(payload) != entry.entry_hash:
                return VerificationResult(
                    False, count, f"entry {expected_index}: entry hash does not match contents"
                )
            previous = entry.entry_hash
        return VerificationResult(True, count, f"verified {count} entries")

    def verify_document(self, index: int, content: bytes) -> bool:
        entries = self.entries()
        if not self.verify_entries(entries).valid:
            return False
        if index < 0 or index >= len(entries):
            return False
        return hashlib.sha256(content).hexdigest() == entries[index].document_sha256


def _is_sha256(value: str) -> bool:
    return (
        isinstance(value, str)
        and len(value) == 64
        and all(character in "0123456789abcdef" for character in value)
    )
