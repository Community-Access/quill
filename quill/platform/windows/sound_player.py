# Moved to quill.platform.sound_player (now cross-platform via sound_lib).
from quill.platform.sound_player import (  # noqa: F401
    SoundPlayer,
    _detect_backend,
    _NullBackend,
    _SoundLibBackend,
    _WavBackend,
    _WinsoundBackend,
)
