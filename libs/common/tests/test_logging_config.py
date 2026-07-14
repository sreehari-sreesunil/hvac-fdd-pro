import structlog

from common.logging_config import configure_logging


def test_configure_logging_binds_service_name(capsys) -> None:
    configure_logging(service_name="test-service", json_logs=True)
    log = structlog.get_logger()
    log.info("hello")

    captured = capsys.readouterr()
    assert "test-service" in captured.out
    assert "hello" in captured.out


def test_configure_logging_console_mode_does_not_crash() -> None:
    # Just verifying the console (non-JSON) code path executes without error —
    # rendering format isn't asserted, that's cosmetic.
    configure_logging(service_name="test-service", json_logs=False)
