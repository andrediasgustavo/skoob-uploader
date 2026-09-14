from pathlib import Path
from typing import Callable

from .browser import prepare_browser
from .config import AppConfig, config_path, load_config, save_config, validate_config
from .parser import validate_pdf


def setup(
    input_func: Callable[[str], str] = input,
    output_func: Callable[[str], None] = print,
) -> Path:
    path = config_path()
    current = load_config(path)
    output_func("Configuração do Skoob Uploader")
    pdf_input = input_func(f"Caminho do PDF [{current.pdf or 'não definido'}]: ").strip()
    browser_input = input_func(f"Navegador (chrome/chromium) [{current.browser}]: ").strip().lower()
    if browser_input and browser_input not in {"chrome", "chromium"}:
        raise SystemExit("Navegador inválido. Use 'chrome' ou 'chromium'.")
    pdf = Path(pdf_input).expanduser() if pdf_input else current.pdf
    if pdf is not None:
        try:
            books = validate_pdf(pdf)
        except ValueError as error:
            raise SystemExit(f"PDF inválido: {error}") from error
        output_func(f"PDF validado: {len(books)} livro(s) encontrado(s).")
    config = validate_config(
        AppConfig(
            pdf=pdf,
            profile_dir=current.profile_dir,
            report=current.report,
            browser=browser_input or current.browser,
            limit=current.limit,
            headless=current.headless,
        )
    )
    prepare_browser(config.browser)
    saved_path = save_config(config, path)
    output_func(f"Configuração salva em: {saved_path}")
    output_func(f"Perfil do navegador: {config.profile_dir}")
    output_func("Agora execute: skoob-uploader [caminho-do-pdf]")
    return saved_path
