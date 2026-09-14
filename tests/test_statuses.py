import pytest

from skoob_uploader.statuses import DEFAULT_STATUS, STATUS_LABELS, resolve_status_tag, status_label


@pytest.mark.parametrize("tag", ["lido", "LIDO", "Lído"])
def test_resolve_status_tag_normalizes_known_statuses(tag):
    status, ignored = resolve_status_tag(tag)

    assert status == "lido"
    assert ignored == ""


@pytest.mark.parametrize("tag, expected", [("lendo", "lendo"), ("quero ler", "quero ler"), ("relendo", "relendo"), ("abandonei", "abandonei")])
def test_resolve_status_tag_accepts_all_supported_statuses(tag, expected):
    assert resolve_status_tag(tag) == (expected, "")


def test_resolve_status_tag_falls_back_to_default_for_unknown_tag():
    assert resolve_status_tag("em pausa") == (DEFAULT_STATUS, "em pausa")


def test_status_label_falls_back_to_default_for_unknown_status():
    assert status_label("unknown") == STATUS_LABELS[DEFAULT_STATUS]
