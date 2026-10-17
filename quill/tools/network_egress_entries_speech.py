"""Cloud dictation providers' reviewed outbound call sites (D-31 to D-37).

Split from :mod:`quill.tools.network_egress_entries` under GATE-11 -- extract,
never rebaseline. Every provider in ``quill/core/windows_dictation/cloud/``
opens the network at its own uniquely named call site, through the shared
certificate-checked openers in ``cloud/transport.py``, so each provider's
fixed host is reviewed here on its own line.

Two rules hold for every entry, and are not repeated in each:

* **Dictation** (``_connect_*``, ``_send_*``, ``_init_*``) happens only after
  the person saved the provider's details on the Speech Providers page, chose
  it as the speech engine, and agreed in its own consent question (No is the
  default; saved per provider and version in
  ``windows_dictation_speech_provider_consent``). Only speech the voice
  detector heard is sent; nothing while nobody speaks. Refused in Safe Mode,
  and with consent declined no request is made (``cloud/consent.py::start_problem``).
* **Test Connection** (``_probe_*``, ``_token_*`` on test) runs only when the
  person presses it on the Speech Providers page, sends no speech and nothing
  of their writing, and is refused in Safe Mode.

Secrets travel only where each provider's protocol puts them (a header, or a
query parameter where the protocol has no header), are never logged and never
appear in an error sentence (``cloud/transport.py::failure``).
"""

from __future__ import annotations

_CLOUD = "core/windows_dictation/cloud/"

SPEECH_EGRESS: dict[str, str] = {
    # -- Microsoft Azure AI Speech (D-32) -------------------------------------
    _CLOUD + "azure.py::_probe_azure": (
        "Test Connection for Azure: POST with an empty body to "
        "<region>.api.cognitive.microsoft.com/sts/v1.0/issueToken, or to the "
        "person's own *.cognitiveservices.azure.com endpoint (host-checked). The key "
        "only in Ocp-Apim-Subscription-Key; the token returned is discarded."
    ),
    _CLOUD + "azure.py::_connect_azure": (
        "Azure live dictation: one WebSocket per dictation session to "
        "<region>.stt.speech.microsoft.com (or the person's own "
        "*.cognitiveservices.azure.com endpoint). Key only in the handshake header; "
        "sends the configuration, the phrase list (My Words, up to 500) and 16 kHz "
        "PCM of each heard phrase."
    ),
    _CLOUD + "azure.py::_send_azure": (
        "Azure a phrase at a time (fast transcription): one heard phrase as a WAV "
        "and its definition (locale, phrase list) to the region's or the person's "
        "own endpoint. Key only in Ocp-Apim-Subscription-Key."
    ),
    # -- Google Cloud Speech-to-Text v2 (D-33) --------------------------------
    _CLOUD + "google.py::_token_google": (
        "Google: exchanges a JWT signed with the person's own service-account key "
        "(kept DPAPI-protected on disk) for an access token at "
        "oauth2.googleapis.com/token. Sends the signed assertion only; the private "
        "key never leaves the computer. On Test Connection or before a phrase."
    ),
    _CLOUD + "google.py::_probe_google": (
        "Test Connection for Google: lists one recognizer of the person's own "
        "project at <location>-speech.googleapis.com with the access token. No audio."
    ),
    _CLOUD + "google.py::_send_google": (
        "Google a phrase at a time: one heard phrase as base64 WAV to the project's "
        "recognizer :recognize at <location>-speech.googleapis.com, with the "
        "language, model and My Words as inline adaptation phrases."
    ),
    # -- Amazon Transcribe streaming (D-34) -----------------------------------
    _CLOUD + "amazon.py::_probe_amazon": (
        "Test Connection for Amazon: one SigV4-signed ListVocabularies call "
        "(MaxResults 1) to transcribe.<region>.amazonaws.com. No audio; the secret "
        "access key signs and is never sent."
    ),
    _CLOUD + "amazon.py::_connect_amazon": (
        "Amazon live dictation: a SigV4-presigned WebSocket to "
        "transcribestreaming.<region>.amazonaws.com:8443, with the language and the "
        "person's own vocabulary name; 16 kHz PCM of each heard phrase in "
        "event-stream frames. The secret key signs and is never sent."
    ),
    # -- Streaming providers (D-35) -------------------------------------------
    _CLOUD + "streaming_providers.py::_probe_deepgram": (
        "Test Connection for Deepgram: GET api.deepgram.com/v1/projects with the "
        "key in Authorization. No audio."
    ),
    _CLOUD + "streaming_providers.py::_connect_deepgram": (
        "Deepgram live dictation: one WebSocket to api.deepgram.com/v1/listen per "
        "session, key in Authorization; Nova-3, My Words as keyterm (up to 100), "
        "16 kHz PCM of each heard phrase."
    ),
    _CLOUD + "streaming_providers.py::_probe_assemblyai": (
        "Test Connection for AssemblyAI: asks streaming(.eu).assemblyai.com/v3/token "
        "for a 60-second temporary token, key in Authorization. No audio."
    ),
    _CLOUD + "streaming_providers.py::_connect_assemblyai": (
        "AssemblyAI live dictation: one WebSocket to streaming(.eu).assemblyai.com/"
        "v3/ws, key in Authorization; My Words as keyterms_prompt (up to 100), "
        "16 kHz PCM of each heard phrase."
    ),
    _CLOUD + "streaming_providers.py::_probe_speechmatics": (
        "Test Connection for Speechmatics: GET asr.api.speechmatics.com/v2/jobs with "
        "the key as a Bearer token. No audio."
    ),
    _CLOUD + "streaming_providers.py::_connect_speechmatics": (
        "Speechmatics live dictation: one WebSocket to eu2 or us2.rt.speechmatics.com, "
        "key as a Bearer token; My Words as additional_vocab, 16 kHz PCM of each "
        "heard phrase."
    ),
    _CLOUD + "streaming_more.py::_probe_elevenlabs": (
        "Test Connection for ElevenLabs Scribe: GET api.elevenlabs.io/v1/user, key "
        "only in xi-api-key. No audio."
    ),
    _CLOUD + "streaming_more.py::_connect_elevenlabs": (
        "ElevenLabs Scribe live dictation (its own consent, separate from ElevenLabs "
        "voices): WebSocket to api.elevenlabs.io/v1/speech-to-text/realtime, key in "
        "xi-api-key, My Words as keyterms (up to 50), 16 kHz PCM of each heard phrase."
    ),
    _CLOUD + "streaming_more.py::_probe_gladia": (
        "Test Connection for Gladia: GET api.gladia.io/v2/live?limit=1, key only in "
        "x-gladia-key. No audio."
    ),
    _CLOUD + "streaming_more.py::_init_gladia": (
        "Gladia live dictation, step one: POST api.gladia.io/v2/live with the audio "
        "format, language and My Words (custom vocabulary, up to 100), key in "
        "x-gladia-key. No audio. The session address returned is accepted only when "
        "it is wss on a gladia.io host."
    ),
    _CLOUD + "streaming_more.py::_connect_gladia": (
        "Gladia live dictation, step two: the WebSocket at the session address the "
        "init returned (wss, gladia.io only), which itself authorises the session; "
        "16 kHz PCM of each heard phrase."
    ),
    _CLOUD + "streaming_more.py::_probe_revai": (
        "Test Connection for Rev.ai: GET api.rev.ai/speechtotext/v1/account with the "
        "access token as a Bearer token. No audio."
    ),
    _CLOUD + "streaming_more.py::_connect_revai": (
        "Rev.ai live dictation: WebSocket to api.rev.ai/speechtotext/v1/stream; the "
        "access token goes in the access_token query parameter because Rev.ai's "
        "streaming protocol has no header for it (inside TLS, never logged); the "
        "person's own custom vocabulary ID; 16 kHz PCM of each heard phrase."
    ),
    # -- Phrase-at-a-time providers (D-36) ------------------------------------
    _CLOUD + "rest_providers.py::_probe_groq": (
        "Test Connection for Groq: GET api.groq.com/openai/v1/models with the key as "
        "a Bearer token. No audio."
    ),
    _CLOUD + "rest_providers.py::_send_groq": (
        "Groq a phrase at a time: one heard phrase as a WAV to api.groq.com/openai/"
        "v1/audio/transcriptions (Whisper), with the language and My Words as the "
        "prompt. Key as a Bearer token."
    ),
    _CLOUD + "rest_providers.py::_probe_mistral": (
        "Test Connection for Mistral: GET api.mistral.ai/v1/models with the key as a "
        "Bearer token. No audio."
    ),
    _CLOUD + "rest_providers.py::_send_mistral": (
        "Mistral Voxtral a phrase at a time: one heard phrase as a WAV to "
        "api.mistral.ai/v1/audio/transcriptions with the language and My Words as "
        "context_bias (up to 100). Key as a Bearer token."
    ),
    # -- IBM Watson Speech to Text (D-37) -------------------------------------
    _CLOUD + "ibm.py::_token_ibm": (
        "IBM: exchanges the person's API key for a short-lived IAM token at "
        "iam.cloud.ibm.com/identity/token (the key in the form body, as IAM "
        "requires). On Test Connection or when a live session opens. No audio."
    ),
    _CLOUD + "ibm.py::_probe_ibm": (
        "Test Connection for IBM: GET <service URL>/v1/models on the person's own "
        "*.speech-to-text.watson.cloud.ibm.com instance (host-checked), IAM token as "
        "a Bearer token. No audio."
    ),
    _CLOUD + "ibm.py::_connect_ibm": (
        "IBM live dictation: WebSocket to the person's own instance's /v1/recognize "
        "(host-checked) with the short-lived IAM token in access_token, where IBM's "
        "socket protocol takes it (never the API key); 16 kHz PCM of each heard "
        "phrase. My Words are not sent."
    ),
}
