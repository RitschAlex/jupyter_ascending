import os
import re
from loguru import logger

EXECUTE_HOST = os.getenv("JUPYTER_ASCENDING_EXECUTE_HOST", "localhost")
EXECUTE_PORT = os.getenv("JUPYTER_ASCENDING_EXECUTE_PORT", 8888)

EXECUTE_HOST_LOCATION = (EXECUTE_HOST, EXECUTE_PORT)
EXECUTE_HOST_URL = f"http://{EXECUTE_HOST_LOCATION[0]}:{EXECUTE_HOST_LOCATION[1]}/jupyter_ascending"

LOG_LEVEL = os.getenv("JUPYTER_ASCENDING_LOG_LEVEL", "INFO")
SHOW_TO_STDOUT = os.getenv("JUPYTER_ASCENDING_SHOW_TO_STDOUT", False)

_DEFAULT_SYNC_EXTENSION = "sync"
_VALID_SYNC_EXTENSION = re.compile(r"^[a-zA-Z0-9_-]+$")


def _validate_sync_extension(value: str,
                             fallback: str = _DEFAULT_SYNC_EXTENSION) -> str:
    value = value.strip()
    if not value or not _VALID_SYNC_EXTENSION.fullmatch(value):
        logger.warning(
            f"Invalid sync extension '{value}'."
            f"Must be alphanumeric, underscores, or hyphens. Falling back to '{fallback}'."
        )
        return fallback
    return value


def _get_sync_extension() -> str:
    return _validate_sync_extension(
        os.getenv("JUPYTER_ASCENDING_SYNC_EXTENSION", _DEFAULT_SYNC_EXTENSION))


SYNC_EXTENSION = _get_sync_extension()
