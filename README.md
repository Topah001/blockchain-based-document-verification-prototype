# Blockchain-Based Document Verification Prototype

A local, append-only **hash-chain ledger** prototype. Adding a file calculates
its SHA-256 digest and appends that digest, a timestamp, a sequence number, the
previous entry hash, and the new entry hash as JSON Lines. The file's contents
are read only to calculate the digest; they are not persisted by this project.

## Run (Python 3.13)

```powershell
python -m document_ledger --ledger ledger.jsonl add lesson.pdf
python -m document_ledger --ledger ledger.jsonl verify
python -m document_ledger --ledger ledger.jsonl verify-document 0 lesson.pdf
python -m unittest discover -s tests -v
```

`verify` checks sequence numbers, document-digest formatting, each entry hash,
and every previous-hash link. `verify-document` additionally compares the
selected recorded digest to a file supplied again by the caller.

Despite the project title, this is **not a decentralized blockchain**: it has
no consensus protocol, peer network, distributed identity, or external trusted
checkpoint. A person able to rewrite the entire file can recompute the chain;
for durable audit evidence, anchor the latest chain hash in an independently
controlled system. The local JSONL ledger is metadata and hashes only.
