import json
import sys

from skoob_uploader.browser import prepare_browser
from skoob_uploader.config import AppConfig, default_config, load_config, save_config, validate_config
from skoob_uploader.main import _resolved_config, build_parser
from skoob_uploader.session import should_wait_for_login


def test_default_config_uses_user_data_directories() -> None:
    config = default_config()

    assert config.profile_dir.name == "profile"
    assert config.report.parts[-2:] == ("reports", "skoob-results.csv")
    assert ".skoob-profile" not in str(config.profile_dir)


def test_app_config_defaults_do_not_depend_on_current_directory() -> None:
    config = AppConfig()

    assert config.profile_dir == default_config().profile_dir
    assert config.report == default_config().report


def test_config_round_trip_preserves_paths(tmp_path) -> None:
    expected = AppConfig(
        pdf=tmp_path / "livros.pdf",
        profile_dir=tmp_path / "profile",
        report=tmp_path / "results.csv",
        browser="chromium",
        limit=3,
        headless=True,
    )
    path = tmp_path / "config.json"

    save_config(expected, path)
    actual = load_config(path)

    assert actual == expected


def test_invalid_config_is_rejected(tmp_path) -> None:
    path = tmp_path / "config.json"
    path.write_text(json.dumps(["invalid"]), encoding="utf-8")

    try:
        load_config(path)
    except ValueError as error:
        assert "objeto JSON" in str(error)
    else:
        raise AssertionError("invalid configuration was accepted")


def test_config_rejects_invalid_browser_and_limit() -> None:
    try:
        validate_config(AppConfig(browser="safari"))
    except ValueError as error:
        assert "Navegador inválido" in str(error)
    else:
        raise AssertionError("invalid browser was accepted")

    try:
        validate_config(AppConfig(limit=-1))
    except ValueError as error:
        assert "não pode ser negativo" in str(error)
    else:
        raise AssertionError("negative limit was accepted")


def test_cli_arguments_override_saved_config(tmp_path) -> None:
    saved = AppConfig(
        pdf=tmp_path / "saved.pdf",
        profile_dir=tmp_path / "saved-profile",
        report=tmp_path / "saved.csv",
        browser="chromium",
        limit=10,
        headless=True,
    )
    config_path = tmp_path / "config.json"
    save_config(saved, config_path)

    args = build_parser().parse_args(
        [
            "--config",
            str(config_path),
            str(tmp_path / "cli.pdf"),
            "--limit",
            "1",
            "--browser",
            "chrome",
        ]
    )

    actual = _resolved_config(args)

    assert actual.pdf == tmp_path / "cli.pdf"
    assert actual.limit == 1
    assert actual.browser == "chrome"
    assert actual.profile_dir == saved.profile_dir
    assert actual.headless is True


def test_prepare_browser_installs_playwright_chromium(monkeypatch) -> None:
    calls = []

    def fake_run(command, check):
        calls.append((command, check))

    monkeypatch.setattr("skoob_uploader.browser.subprocess.run", fake_run)

    prepare_browser("chromium")

    assert calls == [
        ([sys.executable, "-m", "playwright", "install", "chromium"], True)
    ]


def test_prepare_browser_rejects_missing_chrome(monkeypatch) -> None:
    monkeypatch.setattr("skoob_uploader.browser.chrome_executable", lambda: None)

    try:
        prepare_browser("chrome")
    except SystemExit as error:
        assert "Google Chrome não foi encontrado" in str(error)
    else:
        raise AssertionError("missing Chrome was accepted")


def test_login_wait_is_required_for_a_new_profile(tmp_path) -> None:
    args = build_parser().parse_args([])

    assert should_wait_for_login(args, tmp_path / ".login-confirmed") is True


def test_login_wait_is_skipped_after_confirmation(tmp_path) -> None:
    marker = tmp_path / ".login-confirmed"
    marker.touch()
    args = build_parser().parse_args([])

    assert should_wait_for_login(args, marker) is False


def test_login_wait_can_be_forced_or_disabled(tmp_path) -> None:
    marker = tmp_path / ".login-confirmed"
    marker.touch()

    force_args = build_parser().parse_args(["--login-wait"])
    skip_args = build_parser().parse_args(["--no-login-wait"])

    assert should_wait_for_login(force_args, marker) is True
    assert should_wait_for_login(skip_args, tmp_path / "missing-marker") is False
