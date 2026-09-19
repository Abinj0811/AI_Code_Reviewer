"""Basic structured logging setup.

Emits one JSON object per log line so events (review_started,
llm_request, github_comment_posted, ...) are easy to grep or ship to a
log aggregator later. Never log secrets or full source code.
"""

import json
import logging
import sys
from typing import Any


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        extra = getattr(record, "event_data", None)
        if extra:
            payload.update(extra)
        if record.exc_info:
            payload["exc_info"] = self.formatException(record.exc_info)
        return json.dumps(payload, default=str)


def configure_logging(level: str = "INFO") -> None:
    """Configure the root logger to emit JSON lines to stdout."""
    root = logging.getLogger()
    root.setLevel(level)
    root.handlers.clear()

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JsonFormatter())
    root.addHandler(handler)


def log_event(logger: logging.Logger, event: str, **fields: Any) -> None:
    """Log a structured event with arbitrary key/value fields."""
    logger.info(event, extra={"event_data": {"event": event, **fields}})
