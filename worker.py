#!/usr/bin/env python3
"""Entrypoint del worker (wrapper compatible con comandos actuales)."""

from video_translator.workers.runner import main


if __name__ == "__main__":
    main()
