import re
import unicodedata
from math import ceil
from dataclasses import dataclass

from playwright.async_api import BrowserContext, Page, TimeoutError as PlaywrightTimeoutError

from .models import Book, ProcessResult
from .parser import STATUS_LABELS, normalize_volume_labels


def _normalized(value: str) -> str:
    decomposed = unicodedata.normalize("NFKD", value)
    plain = "".join(char for char in decomposed if not unicodedata.combining(char))
    return re.sub(r"[^a-z0-9]+", " ", plain.casefold()).strip()


def _title_matches(search_title: str, found_title: str) -> bool:
    expected_tokens = set(_normalized(normalize_volume_labels(search_title)).split())
    found_tokens = set(_normalized(found_title).split())
    if not expected_tokens or not found_tokens:
        return False
    expected_text = _normalized(normalize_volume_labels(search_title))
    found_text = _normalized(found_title)
    if expected_text in found_text or found_text in expected_text:
        return True
    matched_tokens = expected_tokens & found_tokens
    required_matches = len(expected_tokens) if len(expected_tokens) <= 2 else max(2, ceil(len(expected_tokens) * 0.6))
    return len(matched_tokens) >= required_matches


@dataclass
class SkoobUploader:
    context: BrowserContext
    base_url: str = "https://www.skoob.com.br/pt/home"
    timeout_ms: float = 15_000
    search_timeout_ms: float = 30_000
    home_timeout_ms: float = 60_000

    async def page(self) -> Page:
        return self.context.pages[0] if self.context.pages else await self.context.new_page()

    async def open_home(self) -> Page:
        page = await self.page()
        await page.goto(self.base_url, wait_until="domcontentloaded")
        search = page.get_by_placeholder("Busque por título, autor, editora, ISBN...")
        try:
            await search.wait_for(timeout=self.home_timeout_ms)
        except PlaywrightTimeoutError:
            print(
                "A página inicial ainda não terminou de carregar. "
                "Verifique o login e aguarde o campo de busca aparecer.",
                flush=True,
            )
            await search.wait_for(timeout=300_000)
        return page

    async def process(self, book: Book) -> ProcessResult:
        page = await self.page()
        search = page.get_by_placeholder("Busque por título, autor, editora, ISBN...")
        try:
            await search.fill(normalize_volume_labels(book.title))
            results = page.locator('a[href^="/book/"]')
            await page.wait_for_timeout(300)
            await results.first.wait_for(state="visible", timeout=self.search_timeout_ms)
            result_link = results.first
            result_title = await result_link.locator("h2").inner_text()
            await result_link.click()
            await page.locator("h1").first.wait_for(state="visible", timeout=self.timeout_ms)
            found_title = (await page.locator("h1").first.inner_text()).strip()
            if not _title_matches(book.title, found_title):
                return ProcessResult(
                    title=book.title,
                    status="titulo_divergente",
                    url=page.url,
                    found_title=found_title,
                    reason=f"Primeiro resultado: {result_title}",
                    desired_status=book.desired_status,
                    ignored_status_tag=book.ignored_status_tag,
                )

            desired_label = STATUS_LABELS.get(book.desired_status, STATUS_LABELS["lido"])
            status_button = page.get_by_role(
                "button",
                name=re.compile(r"^(Adicionar|Lido|Lendo|Quero ler|Relendo|Abandonei)$"),
                exact=True,
            )
            await status_button.wait_for(state="visible", timeout=self.timeout_ms)
            current_status = (await status_button.inner_text()).strip()
            if current_status == desired_label:
                return ProcessResult(
                    title=book.title,
                    status=f"ja_{book.desired_status}",
                    url=page.url,
                    found_title=found_title,
                    desired_status=book.desired_status,
                    current_status=current_status,
                    ignored_status_tag=book.ignored_status_tag,
                )

            await status_button.click()
            await page.get_by_role("menuitemradio", name=desired_label, exact=True).click()
            await page.get_by_role("button", name=desired_label, exact=True).wait_for(
                state="visible", timeout=self.timeout_ms
            )
            return ProcessResult(
                title=book.title,
                status="atualizado",
                url=page.url,
                found_title=found_title,
                desired_status=book.desired_status,
                current_status=current_status,
                ignored_status_tag=book.ignored_status_tag,
            )
        except PlaywrightTimeoutError as error:
            return ProcessResult(
                title=book.title,
                status="nao_encontrado",
                url=page.url,
                reason=str(error),
                desired_status=book.desired_status,
                ignored_status_tag=book.ignored_status_tag,
            )
        except Exception as error:
            return ProcessResult(
                title=book.title,
                status="erro",
                url=page.url,
                reason=str(error),
                desired_status=book.desired_status,
                ignored_status_tag=book.ignored_status_tag,
            )
