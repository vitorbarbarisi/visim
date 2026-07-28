"""Resolve secrets from the process environment or a repo-root .env file.

Deliberately hand-rolled rather than pulling in python-dotenv: this repo has
no dependency manifest, and the parsing needed here is a few lines.

Nothing in this module ever logs a secret value — only which source supplied
it, so a misconfiguration is diagnosable without leaking the key.
"""
import os
from typing import Dict, Optional, Union

_QUOTES = ("'", '"')
_FALSEY = ("false", "0", "no", "off")
_TRUTHY = ("true", "1", "yes", "on")


def repo_env_path() -> str:
    """Path to the .env at the repository root (one level above app/)."""
    return os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env")


def parse_env_file(path: str) -> Dict[str, str]:
    """Parse a KEY=VALUE file. Never raises — a missing or unreadable file
    yields {} so callers can run at startup without guarding."""
    values: Dict[str, str] = {}
    try:
        with open(path, "r", encoding="utf-8") as handle:
            lines = handle.readlines()
    except OSError:
        return values

    for raw in lines:
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("export "):
            line = line[len("export "):].lstrip()
        key, sep, value = line.partition("=")  # first "=" only; values may contain "="
        if not sep:
            continue
        key = key.strip()
        if not key:
            continue
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in _QUOTES:
            value = value[1:-1]
        values[key] = value
    return values


def read_setting(name: str, default: Optional[str] = None) -> Optional[str]:
    """Non-secret config value: environment first, then the repo-root .env.

    Values are stripped: a stray trailing space in a .env has bitten this
    project's sibling repo (hanzi-api) before.
    """
    from_env = (os.environ.get(name) or "").strip()
    if from_env:
        return from_env
    from_file = (parse_env_file(repo_env_path()).get(name) or "").strip()
    return from_file or default


def read_secret(name: str) -> Optional[str]:
    """Return `name` from the environment, else from the repo-root .env.

    The environment wins so a value can be overridden per-run without editing
    the file. Logs which source supplied it — never the value itself.
    """
    if (os.environ.get(name) or "").strip():
        print(f"{name}: lido do ambiente")
        return os.environ[name].strip()

    path = repo_env_path()
    from_file = (parse_env_file(path).get(name) or "").strip()
    if from_file:
        print(f"{name}: lido de {path}")
        return from_file

    print(f"{name}: não configurado (nem no ambiente nem em {path})")
    return None


def read_ssl_verify() -> Union[bool, str]:
    """Value for requests' `verify=`: True, False, or a CA-bundle path.

    Mirrors the SSL_VERIFY convention of the sibling hanzi-api repo, which
    sets it false because this network intercepts TLS with a self-signed root
    (requests then fails with CERTIFICATE_VERIFY_FAILED). Pointing SSL_VERIFY
    at the corporate CA bundle is the safer option where one is available;
    the default stays full verification.
    """
    raw = (read_setting("SSL_VERIFY", "true") or "true").strip()
    lowered = raw.lower()
    if lowered in _FALSEY:
        return False
    if lowered in _TRUTHY:
        return True
    return raw  # anything else is treated as a path to a CA bundle
