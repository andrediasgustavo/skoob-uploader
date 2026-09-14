from skoob_uploader.parser import normalize_text, normalize_volume_labels, parse_text, validate_pdf
from skoob_uploader.skoob import _title_matches


def test_parse_text_handles_headers_volumes_and_continuations() -> None:
    text = """
    2026
    Maio
    ● Carl, O Explorador de Masmorras - Matt Dinniman - livro
    ● Elric - Navegante Nos Mares do Destino - Vol 1 - Michael Moorcock, George
    Freeman e Michael T. Gilbert - Quadrinho
    ● The Dungeon Anarchist's Cookbook - Matt Dinniman - livro - inglês
    """

    books = parse_text(text)

    assert [book.title for book in books] == [
        "Carl, O Explorador de Masmorras",
        "Elric - Navegante Nos Mares do Destino - #1",
        "The Dungeon Anarchist's Cookbook",
    ]
    assert books[1].author == "Michael Moorcock, George Freeman e Michael T. Gilbert"
    assert books[2].format == "livro"


def test_normalize_text_ignores_accents_and_punctuation() -> None:
    assert normalize_text("O Poder da Espada") == normalize_text("o poder-da espada")


def test_parse_text_splits_bullets_extracted_on_the_same_line() -> None:
    text = "● O Hobbit - JRR Tolkien - Livro ● Xogun - James Clavell - Livro"

    books = parse_text(text)

    assert [book.title for book in books] == ["O Hobbit", "Xogun"]


def test_title_match_accepts_reordered_series_title() -> None:
    assert _title_matches(
        "Senhor dos Anéis - A Sociedade do Anel",
        "A Sociedade do Anel (O Senhor dos Anéis #1) -",
    )


def test_title_match_rejects_unrelated_title() -> None:
    assert not _title_matches("O Hobbit", "O Senhor dos Anéis")


def test_parse_text_accepts_plain_title_list() -> None:
    books = parse_text("O Hobbit\nXogun\nDuna")

    assert [book.title for book in books] == ["O Hobbit", "Xogun", "Duna"]


def test_normalize_volume_labels_uses_hash_number() -> None:
    assert normalize_volume_labels("Gantz Vol 1") == "Gantz #1"
    assert normalize_volume_labels("Blame! vol. 10") == "Blame! #10"


def test_parse_text_uses_status_tag_when_present() -> None:
    books = parse_text(
        "● Duna - Frank Herbert - livro - [lendo]\n"
        "● O Hobbit - J. R. R. Tolkien - livro"
    )

    assert books[0].desired_status == "lendo"
    assert books[0].ignored_status_tag == ""
    assert books[1].desired_status == "lido"


def test_parse_text_falls_back_to_lido_for_unknown_status_tag() -> None:
    books = parse_text("● Duna - Frank Herbert - livro - [em pausa]")

    assert books[0].desired_status == "lido"
    assert books[0].ignored_status_tag == "em pausa"


def test_validate_pdf_rejects_image_only_pdf(tmp_path, monkeypatch) -> None:
    pdf_path = tmp_path / "scan.pdf"
    pdf_path.write_bytes(b"pdf")
    monkeypatch.setattr("skoob_uploader.parser.extract_pdf_text", lambda _: "")

    try:
        validate_pdf(pdf_path)
    except ValueError as error:
        assert "texto extraível" in str(error)
    else:
        raise AssertionError("image-only PDF was accepted")


def test_validate_pdf_accepts_plain_title_list(tmp_path, monkeypatch) -> None:
    pdf_path = tmp_path / "books.pdf"
    pdf_path.write_bytes(b"pdf")
    monkeypatch.setattr("skoob_uploader.parser.extract_pdf_text", lambda _: "O Hobbit\nDuna")

    books = validate_pdf(pdf_path)

    assert [book.title for book in books] == ["O Hobbit", "Duna"]
