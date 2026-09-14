import asyncio

from skoob_uploader.models import Book
from skoob_uploader.skoob import PlaywrightTimeoutError, SkoobUploader, _title_matches


class FakeLocator:
    def __init__(self, text="", on_click=None, wait_error=None):
        self.text = text
        self.on_click = on_click
        self.wait_error = wait_error
        self.click_count = 0
        self.wait_count = 0

    @property
    def first(self):
        return self

    async def wait_for(self, **_kwargs):
        self.wait_count += 1
        if self.wait_error:
            raise self.wait_error

    async def inner_text(self):
        return self.text

    async def fill(self, _text):
        return None

    def locator(self, selector):
        if selector == "h2" and hasattr(self, "heading"):
            return self.heading
        raise AssertionError(f"unexpected nested locator: {selector}")

    async def click(self):
        self.click_count += 1
        if self.on_click:
            self.on_click()


class FakePage:
    url = "https://www.skoob.com.br/book/123"

    def __init__(self, current_status="Adicionar", found_title="Duna", result_title="Duna"):
        self.search = FakeLocator()
        self.result_link = FakeLocator()
        self.result_link.heading = FakeLocator(result_title)
        self.found_heading = FakeLocator(found_title)
        self.status_button = FakeLocator(current_status)
        self.selected_status = None
        self.menu_items = {}
        self.result_link.on_click = lambda: None

        for label in ("Lido", "Lendo", "Quero ler", "Relendo", "Abandonei"):
            self.menu_items[label] = FakeLocator(
                label,
                on_click=lambda label=label: self._select_status(label),
            )

    def _select_status(self, label):
        self.selected_status = label
        self.status_button.text = label

    def get_by_placeholder(self, _placeholder):
        return self.search

    def locator(self, selector):
        if selector.startswith('a[href^="/book/"]'):
            return self.result_link
        if selector == "h1":
            return self.found_heading
        raise AssertionError(f"unexpected locator: {selector}")

    def get_by_role(self, role, name, exact=True):
        assert exact is True
        if role == "button":
            return self.status_button
        if role == "menuitemradio":
            return self.menu_items[name]
        raise AssertionError(f"unexpected role: {role}")

    async def wait_for_timeout(self, _milliseconds):
        return None


class FakeContext:
    def __init__(self, page):
        self.pages = [page]


def run_process(page, book):
    return asyncio.run(SkoobUploader(FakeContext(page)).process(book))


def make_book(desired_status="lido", ignored_status_tag=""):
    return Book(
        title="Duna",
        author="Frank Herbert",
        format="livro",
        source="Duna - Frank Herbert - livro",
        desired_status=desired_status,
        ignored_status_tag=ignored_status_tag,
    )


def test_process_applies_requested_status_from_menu():
    page = FakePage(current_status="Adicionar")

    result = run_process(page, make_book("lendo"))

    assert result.status == "atualizado"
    assert result.desired_status == "lendo"
    assert result.current_status == "Adicionar"
    assert page.selected_status == "Lendo"
    assert page.menu_items["Lendo"].click_count == 1


def test_process_uses_lido_as_default():
    page = FakePage(current_status="Adicionar")

    result = run_process(page, make_book())

    assert result.status == "atualizado"
    assert result.desired_status == "lido"
    assert page.selected_status == "Lido"


def test_process_does_not_change_already_matching_status():
    page = FakePage(current_status="Lendo")

    result = run_process(page, make_book("lendo"))

    assert result.status == "ja_lendo"
    assert result.current_status == "Lendo"
    assert page.status_button.click_count == 0
    assert page.menu_items["Lendo"].click_count == 0


def test_process_changes_another_status():
    page = FakePage(current_status="Quero ler")

    result = run_process(page, make_book("abandonei"))

    assert result.status == "atualizado"
    assert result.current_status == "Quero ler"
    assert page.selected_status == "Abandonei"


def test_process_supports_every_known_status():
    expected_labels = {
        "lido": "Lido",
        "lendo": "Lendo",
        "quero ler": "Quero ler",
        "relendo": "Relendo",
        "abandonei": "Abandonei",
    }

    for desired_status, expected_label in expected_labels.items():
        page = FakePage(current_status="Adicionar")

        result = run_process(page, make_book(desired_status))

        assert result.status == "atualizado"
        assert page.selected_status == expected_label


def test_process_records_unknown_tag_while_using_lido():
    page = FakePage(current_status="Adicionar")

    result = run_process(page, make_book("lido", "em pausa"))

    assert result.status == "atualizado"
    assert result.ignored_status_tag == "em pausa"
    assert page.selected_status == "Lido"


def test_process_rejects_divergent_first_result_without_changing_status():
    page = FakePage(found_title="O Hobbit", result_title="O Hobbit")

    result = run_process(page, make_book("lendo"))

    assert result.status == "titulo_divergente"
    assert result.found_title == "O Hobbit"
    assert page.status_button.click_count == 0
    assert page.selected_status is None


def test_process_reports_search_timeout():
    page = FakePage()
    page.result_link.wait_error = PlaywrightTimeoutError("search timed out")

    result = run_process(page, make_book())

    assert result.status == "nao_encontrado"
    assert "search timed out" in result.reason


def test_title_matching_handles_empty_and_unrelated_titles():
    assert not _title_matches("", "Duna")
    assert not _title_matches("Duna", "O Hobbit")
    assert _title_matches("Duna Vol 1", "Duna #1")
