import json
import os
import sys
from dataclasses import asdict, dataclass, fields
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class AppConfig:
    pdf: Path | None = None
    profile_dir: Path = Path(".skoob-profile")
    report: Path = Path("reports/skoob-results.csv")
    browser: str = "chromium"
    limit: int = 0
    headless: bool = False


def app_data_dir() -> Path:
    if sys.platform == "win32":
        root = os.environ.get("APPDATA")
        return Path(root) / "skoob-uploader" if root else Path.home() / "AppData/Roaming/skoob-uploader"
    if sys.platform == "darwin":
        return Path.home() / "Library/Application Support/skoob-uploader"
    root = os.environ.get("XDG_CONFIG_HOME")
    return Path(root) / "skoob-uploader" if root else Path.home() / ".config/skoob-uploader"


def config_path() -> Path:
    return app_data_dir() / "config.json"


def default_config() -> AppConfig:
    data_dir = app_data_dir()
    return AppConfig(
        profile_dir=data_dir / "profile",
        report=data_dir / "reports/skoob-results.csv",
    )


def _as_config_value(name: str, value: Any) -> Any:
    if name in {"pdf", "profile_dir", "report"} and value is not None:
        return Path(value).expanduser()
    return value


def load_config(path: Path | None = None) -> AppConfig:
    target = path or config_path()
    config = default_config()
    if not target.is_file():
        return config
    try:
        raw = json.loads(target.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise ValueError(f"Configuração inválida em {target}: {error}") from error
    if not isinstance(raw, dict):
        raise ValueError(f"Configuração inválida em {target}: esperava um objeto JSON.")
    known = {field.name for field in fields(AppConfig)}
    values = {name: _as_config_value(name, raw[name]) for name in known if name in raw}
    return AppConfig(**asdict(config) | values)


def save_config(config: AppConfig, path: Path | None = None) -> Path:
    target = path or config_path()
    target.parent.mkdir(parents=True, exist_ok=True)
    data = {name: str(value) if isinstance(value, Path) else value for name, value in asdict(config).items()}
    target.write_text(json.dumps(data, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")
    return target
