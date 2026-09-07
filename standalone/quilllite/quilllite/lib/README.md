The NVDA controller client DLL goes here.

It is not committed: `quilllite/speech.py` falls back to the copy that ships
inside `accessible_output2`, which QUILL already depends on, so a source
checkout reaches NVDA with nothing in this folder. A packaged build should
place `nvdaControllerClient64.dll` (and the 32-bit twin if you ship 32-bit)
here so the frozen app does not depend on accessible_output2 being importable.
