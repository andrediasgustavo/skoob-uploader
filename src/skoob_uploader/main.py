import argparse
import asyncio
import sys
from pathlib import Path

from playwright.async_api import async_playwright

from .application import process_batch
from .browser import create_context, login_marker
from .config import AppConfig, load_config, validate_config
from .onboarding import setup as setup_onboarding
from .parser import validate_pdf
from .session import confirm_login
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
        help="Navegador a abrir quando não usar --cdp-url (padrão: chrome).",
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
    parser.add_argument(
        "--login-wait",
        action="store_true",
        help="Força a confirmação manual de login, mesmo com uma sessão já configurada.",
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
    return validate_config(AppConfig(**values))


async def run(args: argparse.Namespace) -> None:
    config = _resolved_config(args)
    if config.pdf is None:
        raise SystemExit("Informe um PDF ou execute 'skoob-uploader setup' primeiro.")
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
    session_marker = login_marker(config.profile_dir)
    async with async_playwright() as playwright:
        context, owns_context = await create_context(playwright, config, args.cdp_url)
        uploader = SkoobUploader(context)
        page = await uploader.open_home()
        if "accounts.google.com" in page.url:
            if owns_context:
                await context.close()
            raise SystemExit(
                "O Google bloqueou o login neste navegador automatizado. "
                "Feche o Chrome e inicie uma janela dedicada com CDP, depois execute "
                "novamente usando --cdp-url http://127.0.0.1:9222. "
                "Veja a seção 'Login com Chrome via CDP' no README."
            )
        await confirm_login(args, session_marker, context, owns_context)

        await process_batch(uploader, books, config.report)
        if owns_context:
            await context.close()


def main() -> None:
    if len(sys.argv) > 1 and sys.argv[1] == "setup":
        setup_onboarding()
        return
    if len(sys.argv) > 1 and sys.argv[1] == "run":
        sys.argv.pop(1)
    args = build_parser().parse_args()
    asyncio.run(run(args))


if __name__ == "__main__":
    main()
