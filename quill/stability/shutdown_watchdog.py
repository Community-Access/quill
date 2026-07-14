"""Last-resort hard-exit watchdog for application shutdown (#210).

When an application close has been committed, the graceful wx shutdown should
end the main loop within a second or two. But a single shutdown step that
*blocks* the UI thread (rather than raising), or a wx main loop that never
returns, can leave the process running with no window the user can act on.
No wx-side call can rescue a wedged UI thread; only an independent thread can.
"""

from __future__ import annotations

import logging
import os
import threading

logger = logging.getLogger(__name__)


def arm_hard_exit(timeout: float = 5.0) -> threading.Timer:
    """Return a started daemon timer that force-exits the process after *timeout*.

    The timer runs on its own daemon thread, the only thing that can still
    terminate a wedged UI thread. If the normal shutdown wins the race the
    interpreter is already gone and the callback never runs.

    The grace period only has to outlast a *normal* shutdown (the bounded
    sound-backend join plus socket teardown, a few seconds at most) so it never
    force-kills a healthy exit. Critical persistence is written before any
    blocking teardown step (see MainFrame._on_close), so if the timer does fire
    no user data is lost.
    """

    def _force_exit() -> None:
        logger.error(
            "Graceful shutdown did not finish within %.1fs; forcing exit (#210)",
            timeout,
        )
        os._exit(0)

    timer = threading.Timer(timeout, _force_exit)
    timer.daemon = True
    timer.start()
    return timer
