import argparse
import asyncio
import csv
import os
import shutil
import subprocess
import sys
from pathlib import Path

from playwright.async_api import Error as PlaywrightError
from playwright.async_api import async_playwright

from .config import AppConfig, config_path, load_config, save_config
from .parser import validate_pdf
from .skoob import SkoobUploader


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Marca os livros de um PDF como lidos no Skoob.")
    parser.add_argument("pdf", type=Path, nargs="?", help="Caminho para o PDF com a lista de livros.")
    parser.add_argument(
        "--config",
        type=Path,
        help="Caminho para uma configuração JSON alternativa.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Quantidade máxima de livros; 0 processa toda a lista (padrão: 0).",
    )
    parser.add_argument("--profile-dir", type=Path, default=None)
    parser.add_argument(
        "--browser",
        choices=("chromium", "chrome"),
        default=None,
        help="Navegador a abrir quando não usar --cdp-url (padrão: chromium).",
    )
    parser.add_argument(
        "--cdp-url",
        help="Conecta a um Chrome já iniciado com CDP, por exemplo http://127.0.0.1:9222.",
    )
    parser.add_argument("--report", type=Path, default=None)
    parser.add_argument("--headless", action="store_true", help="Executa sem abrir a janela do navegador.")
    parser.add_argument(
        "--no-login-wait",
        action="store_true",
        help="Não aguarda a confirmação manual de login antes do lote.",
    )
    return parser


def _resolved_config(args: argparse.Namespace) -> AppConfig:
    config = load_config(args.config)
    values = {
        "pdf": args.pdf if args.pdf is not None else config.pdf,
        "profile_dir": args.profile_dir if args.profile_dir is not None else config.profile_dir,
        "report": args.report if args.report is not None else config.report,
        "browser": args.browser if args.browser is not None else config.browser,
        "limit": args.limit if args.limit is not None else config.limit,
        "headless": args.headless or config.headless,
    }
    return AppConfig(**values)


def _chrome_executable() -> Path | None:
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


def _prepare_browser(browser: str) -> None:
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
    if _chrome_executable() is None:
        raise SystemExit(
            "O Google Chrome não foi encontrado. Instale o Chrome ou execute o setup "
            "novamente escolhendo 'chromium'."
        )
    print("Google Chrome encontrado.", flush=True)


def setup() -> None:
    path = config_path()
    current = load_config(path)
    print("Configuração do Skoob Uploader")
    pdf_input = input(f"Caminho do PDF [{current.pdf or 'não definido'}]: ").strip()
    browser_input = input(f"Navegador (chrome/chromium) [{current.browser}]: ").strip().lower()
    if browser_input and browser_input not in {"chrome", "chromium"}:
        raise SystemExit("Navegador inválido. Use 'chrome' ou 'chromium'.")
    pdf = Path(pdf_input).expanduser() if pdf_input else current.pdf
    if pdf is not None:
        try:
            books = validate_pdf(pdf)
        except ValueError as error:
            raise SystemExit(f"PDF inválido: {error}") from error
        print(f"PDF validado: {len(books)} livro(s) encontrado(s).")
    config = AppConfig(
        pdf=pdf,
        profile_dir=current.profile_dir,
        report=current.report,
        browser=browser_input or current.browser,
        limit=current.limit,
        headless=current.headless,
    )
    _prepare_browser(config.browser)
    saved_path = save_config(config, path)
    print(f"Configuração salva em: {saved_path}")
    print(f"Perfil do navegador: {config.profile_dir}")
    print("Agora execute: skoob-uploader [caminho-do-pdf]")


async def run(args: argparse.Namespace) -> None:
    config = _resolved_config(args)
    if config.pdf is None:
        raise SystemExit("Informe um PDF ou execute 'skoob-uploader setup' primeiro.")
    if config.limit < 0:
        raise SystemExit("--limit não pode ser negativo.")
    try:
        books = validate_pdf(config.pdf)
    except ValueError as error:
        raise SystemExit(f"PDF inválido: {error}") from error
    if config.limit > 0:
        books = books[: config.limit]
    if not books:
        raise SystemExit("Nenhum livro foi encontrado no PDF.")

    config.profile_dir.mkdir(parents=True, exist_ok=True)
    config.report.parent.mkdir(parents=True, exist_ok=True)
    async with async_playwright() as playwright:
        owns_context = args.cdp_url is None
        if args.cdp_url:
            try:
                browser = await playwright.chromium.connect_over_cdp(args.cdp_url)
            except PlaywrightError as error:
                if "ECONNREFUSED" in str(error):
                    raise SystemExit(
                        f"Não foi possível conectar ao Chrome em {args.cdp_url}.\n"
                        "Inicie o Chrome com --remote-debugging-port=9222 e tente novamente."
                    ) from error
                raise
            if not browser.contexts:
                raise SystemExit("O Chrome conectado por CDP não possui um contexto de navegador.")
            context = browser.contexts[0]
        else:
            launch_options = {
                "user_data_dir": str(config.profile_dir),
                "headless": config.headless,
                "viewport": {"width": 1440, "height": 1000},
            }
            if config.browser == "chrome":
                launch_options["channel"] = "chrome"
            context = await playwright.chromium.launch_persistent_context(**launch_options)
        uploader = SkoobUploader(context)
        page = await uploader.open_home()
        if not args.no_login_wait:
            if config.headless:
                if owns_context:
                    await context.close()
                raise SystemExit("Remova --headless para fazer login e confirmar a sessão manualmente.")
            print(
                "\nNavegador aberto. Faça login no Skoob e deixe a página pronta. "
                "Quando terminar, pressione Enter neste terminal para iniciar o lote.",
                flush=True,
            )
            await asyncio.to_thread(input)

        results = []
        for index, book in enumerate(books, start=1):
            result = await uploader.process(book)
            results.append(result)
            print(f"[{index}/{len(books)}] {book.title}: {result.status}")
            await asyncio.sleep(0.8)
            page = await uploader.open_home()

        with config.report.open("w", newline="", encoding="utf-8") as report_file:
            writer = csv.DictWriter(report_file, fieldnames=["title", "status", "url", "found_title", "reason"])
            writer.writeheader()
            writer.writerows(result.__dict__ for result in results)
        if owns_context:
            await context.close()


def main() -> None:
    if len(sys.argv) > 1 and sys.argv[1] == "setup":
        setup()
        return
    if len(sys.argv) > 1 and sys.argv[1] == "run":
        sys.argv.pop(1)
    args = build_parser().parse_args()
    asyncio.run(run(args))


if __name__ == "__main__":
    main()
