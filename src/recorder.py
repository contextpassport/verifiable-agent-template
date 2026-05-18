"""
Wires Context Passport into a LangGraph agent.

The recorder is intentionally thin. It:
  - Loads or generates a persistent Ed25519 keypair (./.keys/agent.key)
  - Creates a LangGraphPassportCallback that signs every commit
  - Persists each passport to ./passports/<id>.json as it is created
  - Returns the handler so it can be attached to a LangGraph invocation

For production you would:
  - Replace the local keypair with HSM-backed signing
  - Replace the local passports/ directory with a remote receiving server
  - Add external anchoring (see docs/external-anchoring.md in the spec repo)

See https://github.com/contextpassport/spec/tree/main/docs for the patterns.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

from context_passport.integrations.langgraph import LangGraphPassportCallback
from context_passport.signing import (
    Ed25519PrivateKey,
    generate_keypair,
    public_key_to_base64,
    sign_passport,
)
from cryptography.hazmat.primitives import serialization

KEY_DIR = Path("./.keys")
KEY_PATH = KEY_DIR / "agent.key"
KEY_ID = "agent-template-key-1"

PASSPORTS_DIR = Path("./passports")


def _load_or_create_key() -> Ed25519PrivateKey:
    """Persistent dev key. Generated on first run, reused after."""
    KEY_DIR.mkdir(exist_ok=True)
    if KEY_PATH.exists():
        with KEY_PATH.open("rb") as f:
            return serialization.load_pem_private_key(f.read(), password=None)
    private, _ = generate_keypair()
    with KEY_PATH.open("wb") as f:
        f.write(private.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption(),
        ))
    KEY_PATH.chmod(0o600)
    return private


def _persist_passport(passport: dict) -> None:
    """Write each passport to ./passports/<id>.json as it is created."""
    PASSPORTS_DIR.mkdir(exist_ok=True)
    path = PASSPORTS_DIR / f"{passport['id']}.json"
    with path.open("w", encoding="utf-8") as f:
        json.dump(passport, f, indent=2, sort_keys=True)


def make_recorder(
    *,
    agent_id: str = "verifiable-agent-template",
    agent_name: str = "Verifiable Agent Template",
    provider: str = "anthropic",
    model: str = "claude-opus-4-6",
    trace_id: Optional[str] = None,
) -> LangGraphPassportCallback:
    """Return a configured callback handler ready to attach to a LangGraph invocation."""
    private_key = _load_or_create_key()

    def sign_and_persist(passport: dict) -> None:
        signed = sign_passport(passport, private_key, key_id=KEY_ID)
        _persist_passport(signed)

    handler = LangGraphPassportCallback(
        agent_id=agent_id,
        agent_name=agent_name,
        provider=provider,
        model=model,
        trace_id=trace_id,
        commit_fn=sign_and_persist,
    )
    return handler


def public_key_base64() -> str:
    """Convenience for printing the agent's public key (for sharing with verifiers)."""
    return public_key_to_base64(_load_or_create_key().public_key())
