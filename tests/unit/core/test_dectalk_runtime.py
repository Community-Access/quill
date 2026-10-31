from __future__ import annotations

from pathlib import Path

import pytest

from quill.core import dectalk_runtime as dectalk_module
from quill.core.read_aloud import ReadAloudUnavailableError


def test_dectalk_download_is_retired_without_writing_files(tmp_path: Path) -> None:
    with pytest.raises(ReadAloudUnavailableError, match="no longer distributes DECtalk"):
        dectalk_module.download_dectalk_runtime(tmp_path)
    assert list(tmp_path.iterdir()) == []
