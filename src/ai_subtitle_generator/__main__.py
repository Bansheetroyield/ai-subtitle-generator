"""CLI bootstrap for ai-subtitle-generator.

Entry point wired via pyproject `[project.scripts]`. Delegates to
`cli.app` so the Typer surface stays testable without importing the
whole host.
"""

from __future__ import annotations

import sys

from ai_subtitle_generator.cli import app


def main() -> int:
    """Run the CLI. Returns a process exit code."""
    try:
        app()
    except KeyboardInterrupt:
        return 130
    return 0


if __name__ == "__main__":
    sys.exit(main())