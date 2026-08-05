import logging
import sys

import structlog
from structlog.typing import Processor


def configure_logging(service_name: str, json_logs: bool = False) -> None:
    """
    Call once at service startup. jons_logs = True in production (log aggregators
    parse JSON), False for readable console output in local dev."""
    logging.basicConfig(format="%(message)s", stream=sys.stdout, level=logging.INFO)

    # Explicit Processor annotation needed - without it mypy infers this
    # heterogeneous list (plain functions + class instances) as
    # list[object], which doesn't satisfy structlog.configure()'s actual
    # expected type. This surfaced only after adding structlog to the
    # pre-commit mypy hook's additional_dependencies - previously mypy
    # couldn't resolve structlog at all, so it never got far enough to
    # check this.
    shared_processors: list[Processor] = [
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.stdlib.PositionalArgumentsFormatter(),
    ]

    renderer = structlog.processors.JSONRenderer() if json_logs else structlog.dev.ConsoleRenderer()

    structlog.configure(
        processors=shared_processors + [renderer],
        wrapper_class=structlog.make_filtering_bound_logger(logging.INFO),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )

    structlog.contextvars.bind_contextvars(service=service_name)
