import os
import shutil
import subprocess
import sys
from pathlib import Path

from playwright.async_api import BrowserContext, Error as PlaywrightError

from .config import AppConfig


def chrome_executable() -> Path | None:
    candidates = [
        Path("/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"),
        Path.home() / "Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
        Path(os.environ["PROGRAMFILES"]) / "Google/Chrome/Application/chrome.exe"
        if os.environ.get("PROGRAMFILES")
        else Path(),
        Path(os.environ["LOCALAPPDATA"]) / "Google/Chrome/Application/chrome.exe"
        if os.environ.get("LOCALAPPDATA")
        else Path(),
    ]
    for command in ("google-chrome", "google-chrome-stable", "chrome"):
        executable = shutil.which(command)
        if executable:
            return Path(executable)
    return next((candidate for candidate in candidates if candidate.is_file()), None)


def prepare_browser(browser: str) -> None:
    if browser == "chromium":
        print("Verificando o Chromium do Playwright...", flush=True)
        try:
            subprocess.run(
                [sys.executable, "-m", "playwright", "install", "chromium"],
                check=True,
            )
        except (OSError, subprocess.CalledProcessError) as error:
            raise SystemExit(
                "Não foi possível instalar o Chromium do Playwright. "
                "Tente executar manualmente: python -m playwright install chromium"
            ) from error
        return
    if chrome_executable() is None:
        raise SystemExit(
            "O Google Chrome não foi encontrado. Instale o Chrome ou execute o setup "
            "novamente escolhendo 'chromium'."
        )
    print("Google Chrome encontrado.", flush=True)


async def create_context(playwright, config: AppConfig, cdp_url: str | None) -> tuple[BrowserContext, bool]:
    if cdp_url:
        try:
            browser = await playwright.chromium.connect_over_cdp(cdp_url)
        except PlaywrightError as error:
            if "ECONNREFUSED" in str(error):
                raise SystemExit(
                    f"Não foi possível conectar ao Chrome em {cdp_url}.\n"
                    "Inicie o Chrome com --remote-debugging-port=9222 e tente novamente."
                ) from error
            raise
        if not browser.contexts:
            raise SystemExit("O Chrome conectado por CDP não possui um contexto de navegador.")
        return browser.contexts[0], False

    launch_options = {
        "user_data_dir": str(config.profile_dir),
        "headless": config.headless,
        "viewport": {"width": 1440, "height": 1000},
    }
    if config.browser == "chrome":
        launch_options["channel"] = "chrome"
    context = await playwright.chromium.launch_persistent_context(**launch_options)
    return context, True


def login_marker(profile_dir: Path) -> Path:
    return profile_dir / ".login-confirmed"
