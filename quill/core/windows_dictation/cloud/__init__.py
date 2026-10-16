"""Cloud dictation with the person's own account (D-31 to D-37).

Local dictation stays the default and the recommendation. This package lets a
person who already has an account with a speech provider use it, by entering
only what that provider needs on the Speech Providers page
(:mod:`quill.ui.speech_providers_dialog`):

* :mod:`.types` -- the provider shape (fields, capabilities, ``live``, ``phrase``);
* :mod:`.registry` -- the list, and the ``cloud-<id>`` engine ids;
* :mod:`.credentials` -- secrets in the credential store, never in settings;
* :mod:`.consent` -- the question generated from each provider's facts;
* :mod:`.recognizer` -- the provider behind the built-in engines' listening loop;
* :mod:`.transport` and :mod:`.ws_base` -- the network, and its sentences;
* one module per provider family: :mod:`.azure`, :mod:`.google`,
  :mod:`.amazon`, :mod:`.streaming_providers`, :mod:`.streaming_more`,
  :mod:`.rest_providers`, :mod:`.ibm`, :mod:`.openai_provider`.

wx-free throughout. Design record: section 23 of
``docs/design/2026-10-05-dictation-plan-and-status.md``.
"""
