from __future__ import annotations

# Import keras patch FIRST, before any other backend imports
import backend._keras_patch  # noqa: F401

import uvicorn

from backend.api import app
from backend.settings import get_settings


def main() -> None:
    settings = get_settings()
    uvicorn.run(app, host=settings.host, port=settings.port)


if __name__ == "__main__":
    main()
