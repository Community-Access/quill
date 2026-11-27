"""List Speech Templates: let people choose how list rows are spoken.

See ``docs/design/list-speech-templates.md``. The package is wx-free:

- :mod:`catalog`    the list types, their fields, presets and sample rows;
- :mod:`template`   the declarative template model and its validation;
- :mod:`render`     a row plus a template becomes the spoken sentence;
- :mod:`library`    saved templates and which one each list uses;
- :mod:`store`      the JSON file, with damaged-file handling;
- :mod:`row_fields` field values from GitHub and WordPress row models;
- :mod:`speak`      the single call a list makes.
"""
