"""Cross-platform sound playback for the Deckhand OpenDeck plugin."""

from __future__ import annotations

import asyncio
import logging
import platform
import shutil
from pathlib import Path

logger = logging.getLogger("deckhand-audio")

SOUNDS_DIR = Path(__file__).parent / "sounds"


async def play_sound(filename: str) -> None:
    """Play a sound file from the sounds/ directory.

    Uses platform-native commands so we don't block the event loop.
    """
    path = SOUNDS_DIR / filename
    if not path.exists():
        logger.warning("Sound file not found: %s", path)
        return

    system = platform.system()
    if system == "Darwin":
        cmd = ["afplay", str(path)]
    elif system == "Linux":
        # Prefer paplay (PulseAudio), fall back to aplay (ALSA)
        if shutil.which("paplay"):
            cmd = ["paplay", str(path)]
        elif shutil.which("aplay"):
            cmd = ["aplay", str(path)]
        else:
            logger.warning("No audio player found on Linux (tried paplay, aplay)")
            return
    else:
        logger.warning("Unsupported platform for audio: %s", system)
        return

    try:
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.DEVNULL,
            stderr=asyncio.subprocess.DEVNULL,
        )
        await proc.wait()
    except OSError:
        logger.exception("Failed to play sound: %s", filename)
