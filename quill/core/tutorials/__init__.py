"""Guided tutorials: the shared engine every Quill app teaches from.

Four apps have lessons -- Quill Radio, QUILL Cast, Quill Weather and QUILL
itself -- and they share everything except the lessons. This package is the
shared half:

* :mod:`quill.core.tutorials.model` -- what a step, a tutorial and a track are,
  the pure text that renders one, and :class:`TutorialSet`, which is what an
  app hands to the window.
* :mod:`quill.core.tutorials.progress` -- where somebody got to, one small
  JSON file per app.

An app's own lessons live with that app's other domain code
(``quill/core/radio/tutorials/``, ``quill/core/podcasts/tutorials/``,
``quill/core/weather/tutorials/``, ``quill/core/quill_tutorials/``), each
exporting a ``CATALOGUE`` built with :func:`quill.core.tutorials.model.build`.
Nothing here knows which app it is serving.
"""

from __future__ import annotations

from quill.core.tutorials.model import (
    KeyLookup as KeyLookup,
)
from quill.core.tutorials.model import (
    Progress as Progress,
)
from quill.core.tutorials.model import (
    Step as Step,
)
from quill.core.tutorials.model import (
    Track as Track,
)
from quill.core.tutorials.model import (
    Tutorial as Tutorial,
)
from quill.core.tutorials.model import (
    TutorialSet as TutorialSet,
)
from quill.core.tutorials.model import (
    build as build,
)
from quill.core.tutorials.model import (
    contents_label as contents_label,
)
from quill.core.tutorials.model import (
    key_phrase as key_phrase,
)
from quill.core.tutorials.model import (
    render_step as render_step,
)
from quill.core.tutorials.model import (
    render_tutorial as render_tutorial,
)
from quill.core.tutorials.model import (
    step_heading as step_heading,
)
from quill.core.tutorials.model import (
    track_titles as track_titles,
)
from quill.core.tutorials.model import (
    validate as validate,
)
