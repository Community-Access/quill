"""File > WordPress > Media and Files, and the Media Library (wordpress.md 6.1 to 6.8).

A mixin of :class:`~quill.ui.wordpress_commands.WordPressCommands`, shared by
QUILL and QUILL Lite; it reaches the editor only through ``self.host``. It is
assembled from smaller mixins, one per part of section 6, so no module grows
past its size budget:

- :mod:`quill.ui.wordpress_media_library` -- the Media Library window (Used In,
  Attach, Featured Image, Suggest, Describe), Insert from Media Library and
  Insert Picture from This Computer;
- :mod:`quill.ui.wordpress_media_upload` -- Upload Files, Paste Image and Upload
  from Web Address, through one upload path with duplicate checks;
- :mod:`quill.ui.wordpress_image_commands` -- Image Size, Make a Smaller Copy and
  the Alt Text Review;
- :mod:`quill.ui.wordpress_media_ai` -- Suggest Alt Text and Describe Image, on
  the editor's own AI.

The Picture Maker, the site logo and Visual Review (6.9 to 6.11) are in
:mod:`quill.ui.wordpress_picture_commands`.
"""

from __future__ import annotations

from quill.ui.wordpress_image_commands import WordPressImageCommands
from quill.ui.wordpress_media_ai import WordPressMediaAi
from quill.ui.wordpress_media_library import WordPressMediaLibrary
from quill.ui.wordpress_media_upload import WordPressMediaUpload
from quill.ui.wordpress_player_commands import WordPressPlayerCommands


class WordPressMediaCommands(
    WordPressMediaLibrary,
    WordPressMediaUpload,
    WordPressImageCommands,
    WordPressMediaAi,
    WordPressPlayerCommands,
):
    pass
