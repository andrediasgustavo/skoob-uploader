import argparse
import asyncio
from pathlib import Path

from playwright.async_api import BrowserContext


def should_wait_for_login(args: argparse.Namespace, marker: Path) -> bool:
    return args.login_wait or (not args.no_login_wait and not marker.exists())


async def confirm_login(
    args: argparse.Namespace,
    marker: Path,
    context: BrowserContext,
    owns_context: bool,
) -> None:
    if not should_wait_for_login(args, marker):
        return
    if args.headless:
        if owns_context:
            await context.close()
        raise SystemExit("Remova --headless para fazer login e confirmar a sessão manualmente.")
    print(
        "\nNavegador aberto. Faça login no Skoob e deixe a página pronta. "
        "Quando terminar, pressione Enter neste terminal para iniciar o lote.",
        flush=True,
    )
    await asyncio.to_thread(input)
    marker.touch()
