from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import json
import os
from typing import Any


@dataclass(frozen=True)
class BitgetConfig:
    exchange: str
    mode: str
    demo: bool
    product: str | None
    api_key_env: str
    api_secret_env: str
    passphrase_env: str
    base_url: str | None
    withdrawals_enabled: bool
    notes: dict[str, Any]


@dataclass(frozen=True)
class BitgetSetupReport:
    config: BitgetConfig
    env_status: dict[str, bool]
    ready_for_demo: bool
    checks: tuple[str, ...]


def _require_str(data: dict[str, Any], key: str, *, default: str | None = None) -> str:
    value = data.get(key, default)
    if value is None:
        raise ValueError(f"missing required '{key}' value")
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"'{key}' must be a non-empty string")
    return value


def _load_simple_env_file(path: str | Path) -> dict[str, str]:
    env_path = Path(path)
    if not env_path.exists():
        return {}

    data: dict[str, str] = {}
    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip()
        if not key:
            continue
        if value and value[0] == value[-1] and value[0] in {'"', "'"}:
            value = value[1:-1]
        data[key] = value
    return data


def load_bitget_config(path: str | Path = "state/bitget.json") -> BitgetConfig:
    config_path = Path(path)
    data = json.loads(config_path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("Bitget config must be a JSON object")

    exchange = _require_str(data, "exchange", default="bitget")
    if exchange.lower() != "bitget":
        raise ValueError("exchange must be 'bitget'")

    mode = _require_str(data, "mode", default="paper")
    demo = bool(data.get("demo", mode == "paper"))
    product = data.get("product")
    if product is not None and (not isinstance(product, str) or not product.strip()):
        raise ValueError("product must be a non-empty string or null")

    api_key_env = _require_str(data, "api_key_env", default="BITGET_API_KEY")
    api_secret_env = _require_str(data, "api_secret_env", default="BITGET_API_SECRET")
    passphrase_env = _require_str(data, "passphrase_env", default="BITGET_API_PASSPHRASE")
    base_url = data.get("base_url")
    if base_url is not None and (not isinstance(base_url, str) or not base_url.strip()):
        raise ValueError("base_url must be a non-empty string or null")

    withdrawals_enabled = bool(data.get("withdrawals_enabled", False))
    notes = data.get("notes", {})
    if not isinstance(notes, dict):
        raise ValueError("notes must be an object")

    return BitgetConfig(
        exchange=exchange,
        mode=mode,
        demo=demo,
        product=product,
        api_key_env=api_key_env,
        api_secret_env=api_secret_env,
        passphrase_env=passphrase_env,
        base_url=base_url,
        withdrawals_enabled=withdrawals_enabled,
        notes=notes,
    )


def _env_value(name: str, *, env_file: str | Path = "state/bitget.env") -> bool:
    if os.getenv(name):
        return True
    file_env = _load_simple_env_file(env_file)
    value = file_env.get(name)
    return bool(value)


def bitget_env_status(config: BitgetConfig, *, env_file: str | Path = "state/bitget.env") -> dict[str, bool]:
    return {
        config.api_key_env: _env_value(config.api_key_env, env_file=env_file),
        config.api_secret_env: _env_value(config.api_secret_env, env_file=env_file),
        config.passphrase_env: _env_value(config.passphrase_env, env_file=env_file),
    }


def build_bitget_setup_report(
    config: BitgetConfig,
    *,
    env_file: str | Path = "state/bitget.env",
) -> BitgetSetupReport:
    env_status = bitget_env_status(config, env_file=env_file)
    checks: list[str] = []

    if config.mode != "paper":
        checks.append("mode is not paper")
    if not config.demo:
        checks.append("demo flag is disabled")
    if config.product is None:
        checks.append("product is not set")
    if config.withdrawals_enabled:
        checks.append("withdrawals must stay disabled")
    if not all(env_status.values()):
        checks.append("all API credential env vars must be present")

    ready_for_demo = not checks
    return BitgetSetupReport(
        config=config,
        env_status=env_status,
        ready_for_demo=ready_for_demo,
        checks=tuple(checks),
    )


def format_bitget_setup_report(report: BitgetSetupReport) -> str:
    lines = ["Bitget setup"]
    lines.append(f"- exchange: {report.config.exchange}")
    lines.append(f"- mode: {report.config.mode}")
    lines.append(f"- demo: {report.config.demo}")
    lines.append(f"- product: {report.config.product or '(not set yet)'}")
    lines.append(f"- withdrawals_enabled: {report.config.withdrawals_enabled}")
    lines.append(f"- ready_for_demo: {report.ready_for_demo}")
    for name, present in report.env_status.items():
        lines.append(f"- {name}: {present}")
    if report.config.base_url:
        lines.append(f"- base_url: {report.config.base_url}")
    else:
        lines.append("- base_url: (not set yet)")
    if report.checks:
        lines.append("- checks:")
        for check in report.checks:
            lines.append(f"  - {check}")
    if report.config.notes:
        lines.append("- notes:")
        for key, value in report.config.notes.items():
            lines.append(f"  - {key}: {value}")
    return "\n".join(lines)
