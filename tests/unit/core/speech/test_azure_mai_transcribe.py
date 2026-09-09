"""Azure MAI-Transcribe-2 as a host-only cloud kind.

The same provider QUILL's sibling podHarvest offers, wired the same way and
built from the same PRD, so a transcript from one is a transcript from the
other.

The security-relevant part is why it is *host-only*. Every other cloud kind
carries a fixed, vetted endpoint, which is what makes "a Quillin may only name
a known kind" a real guarantee about where audio goes. Azure's endpoint is
your own Speech resource's address, which comes from QUILL's settings -- so if
it were declarable, a manifest could aim the host at any server it liked.
"""

from __future__ import annotations

import json

import pytest

from quill.core.speech import cloud_transcribers as ct


class TestTheRequestShape:
    def _definition(self, **kwargs) -> dict:
        return json.loads(ct.azure_mai_definition(**kwargs))

    def test_enhanced_mode_names_the_model(self) -> None:
        definition = self._definition()
        assert definition["enhancedMode"]["enabled"] is True
        assert definition["enhancedMode"]["model"] == "MAI-Transcribe-2"

    def test_automatic_detection_sends_no_locale_at_all(self) -> None:
        """Microsoft's own guidance: a locale is a strong hint, and a strong
        hint towards the wrong language is worse than none."""
        assert "locales" not in self._definition(language="auto")

    def test_naming_a_language_sends_exactly_one(self) -> None:
        for code in ("en", "es"):
            assert self._definition(language=code)["locales"] == [code]

    def test_an_unsupported_language_is_dropped_rather_than_sent(self) -> None:
        """The service handles English and Spanish. Sending anything else is
        a silent downgrade nobody asked for."""
        assert "locales" not in self._definition(language="fr")

    def test_the_style_reaches_the_request(self) -> None:
        for style in ("clean", "verbatim"):
            options = self._definition(style=style)["enhancedMode"]["modelOptions"]
            assert options["transcribeStyle"] == style

    def test_a_nonsense_style_falls_back(self) -> None:
        options = self._definition(style="sideways")["enhancedMode"]["modelOptions"]
        assert options["transcribeStyle"] == "clean"

    def test_word_timings_are_asked_for_only_when_wanted(self) -> None:
        assert (
            self._definition(word_timestamps=True)["enhancedMode"]["modelOptions"]["timestamps"]
            == "word"
        )
        assert (
            self._definition(word_timestamps=False)["enhancedMode"]["modelOptions"]["timestamps"]
            == "segment"
        )

    def test_diarization_is_asked_for_only_when_wanted(self) -> None:
        assert "diarization" in self._definition(diarize=True)
        assert "diarization" not in self._definition(diarize=False)

    def test_phrases_are_sent_and_blanks_are_not(self) -> None:
        definition = self._definition(phrases=["ACB Media", " ", "", "Pinecast"])
        assert definition["phraseList"]["phrases"] == ["ACB Media", "Pinecast"]

    def test_no_phrases_means_no_phrase_list(self) -> None:
        assert "phraseList" not in self._definition(phrases=[])

    def test_it_is_valid_json(self) -> None:
        json.loads(ct.azure_mai_definition())


class TestTheUrl:
    def test_it_is_the_documented_path(self) -> None:
        url = ct.azure_mai_url("https://r.cognitiveservices.azure.com")
        assert "/speechtotext/transcriptions:transcribe" in url
        assert "api-version=2025-10-15" in url

    def test_a_trailing_slash_does_not_double_up(self) -> None:
        url = ct.azure_mai_url("https://r.cognitiveservices.azure.com/")
        assert "//speechtotext" not in url

    def test_the_api_version_can_be_changed(self) -> None:
        """A preview API that changes shape under a released program is a bug
        report nobody can act on."""
        url = ct.azure_mai_url("https://r.example.com", api_version="2099-01-01")
        assert "api-version=2099-01-01" in url


class TestItIsHostOnly:
    def test_it_is_not_something_a_manifest_can_name(self) -> None:
        assert "azure_mai" in ct.HOST_ONLY_PROVIDER_KINDS
        assert "azure_mai" not in ct.TRANSCRIPTION_PROVIDER_KINDS

    def test_its_spec_says_the_address_comes_from_the_caller(self) -> None:
        spec = ct.CLOUD_REST_SPECS["azure_mai"]
        assert spec.endpoint_from_caller is True
        assert spec.endpoint == "", "there is no constant address to give"

    def test_it_uses_azures_own_key_header(self) -> None:
        spec = ct.CLOUD_REST_SPECS["azure_mai"]
        assert spec.key_header == "Ocp-Apim-Subscription-Key"
        assert spec.key_scheme == ""

    def test_the_transcript_is_read_from_where_azure_puts_it(self) -> None:
        spec = ct.CLOUD_REST_SPECS["azure_mai"]
        payload = {"combinedPhrases": [{"text": "Hello there."}]}
        assert ct._dig(payload, spec.text_path) == "Hello there."


class TestRefusingToGuess:
    def test_a_spec_needing_an_address_will_not_run_without_one(self, tmp_path):
        """Falling back to the placeholder would post audio to nowhere, or --
        worse, one day -- to somewhere."""
        audio = tmp_path / "clip.mp3"
        audio.write_bytes(b"\0" * 16)
        with pytest.raises(ct.CloudTranscribeError, match="your own resource"):
            ct.transcribe_rest(ct.CLOUD_REST_SPECS["azure_mai"], audio, "a-key")

    def test_an_insecure_address_is_refused(self, tmp_path):
        audio = tmp_path / "clip.mp3"
        audio.write_bytes(b"\0" * 16)
        with pytest.raises(ct.CloudTranscribeError, match="secure"):
            ct.transcribe_rest(
                ct.CLOUD_REST_SPECS["azure_mai"], audio, "a-key", endpoint="http://r.example.com/x"
            )

    def test_the_other_kinds_still_work_without_an_endpoint(self):
        """The new rule must not have quietly broken the existing providers."""
        for kind in ("groq", "elevenlabs"):
            spec = ct.CLOUD_REST_SPECS[kind]
            assert spec.endpoint_from_caller is False
            assert spec.endpoint.startswith("https://")


class TestTheJsonPart:
    def test_a_json_part_is_typed_as_json(self, tmp_path):
        """Most providers accept an untyped text part. Azure rejects one."""
        audio = tmp_path / "clip.mp3"
        audio.write_bytes(b"\0" * 8)
        body, content_type = ct._multipart_body(
            audio, "audio", (), json_fields=(("definition", '{"a": 1}'),)
        )
        assert content_type.startswith("multipart/form-data; boundary=")
        assert b"Content-Type: application/json" in body
        assert b'name="definition"' in body

    def test_a_plain_field_is_still_untyped(self, tmp_path):
        audio = tmp_path / "clip.mp3"
        audio.write_bytes(b"\0" * 8)
        body, _ct = ct._multipart_body(audio, "file", (("model", "x"),))
        assert b"Content-Type: application/json" not in body

    def test_the_audio_is_still_in_there(self, tmp_path):
        audio = tmp_path / "clip.mp3"
        audio.write_bytes(b"AUDIOBYTES")
        body, _ct = ct._multipart_body(audio, "audio", (), json_fields=(("definition", "{}"),))
        assert b"AUDIOBYTES" in body
        assert b'filename="clip.mp3"' in body


def test_it_adds_no_new_way_out_of_the_process() -> None:
    """Azure goes through the same reviewed egress call as every other kind.

    A second `urlopen` would be a second thing to audit, and the audit is the
    reason anybody can say where audio goes.
    """
    import inspect

    source = inspect.getsource(ct)
    # One call site. The import above it is `from urllib.request import
    # Request, urlopen`, with no parenthesis, so this counts calls only.
    assert source.count("urlopen(") == 1, "a second call site is a second thing to audit"
