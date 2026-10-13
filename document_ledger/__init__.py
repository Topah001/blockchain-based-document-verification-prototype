"""Tamper-evident hash-chain document ledger prototype."""

from .ledger import Ledger, LedgerEntry, LedgerError, VerificationResult

__all__ = ["Ledger", "LedgerEntry", "LedgerError", "VerificationResult"]
