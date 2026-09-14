import json
import os
import sys
from dataclasses import asdict, dataclass, field, fields
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class AppConfig:
    pdf: Path | None = None
    profile_dir: Path = field(default_factory=lambda: app_data_dir() / "profile")
    report: Path = field(default_factory=lambda: app_data_dir() / "reports/skoob-results.csv")
    browser: str = "chrome"
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
    return AppConfig()


def validate_config(config: AppConfig) -> AppConfig:
    if config.browser not in {"chrome", "chromium"}:
        raise ValueError("Navegador inválido. Use 'chrome' ou 'chromium'.")
    if config.limit < 0:
        raise ValueError("--limit não pode ser negativo.")
    if not isinstance(config.profile_dir, Path) or not isinstance(config.report, Path):
        raise ValueError("Os caminhos de perfil e relatório devem ser válidos.")
    return config


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
    return validate_config(AppConfig(**asdict(config) | values))


def save_config(config: AppConfig, path: Path | None = None) -> Path:
    target = path or config_path()
    target.parent.mkdir(parents=True, exist_ok=True)
    data = {name: str(value) if isinstance(value, Path) else value for name, value in asdict(config).items()}
    target.write_text(json.dumps(data, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")
    return target
