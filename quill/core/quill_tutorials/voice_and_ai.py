"""QUILL, tracks 4 and 5: how much it says, and the assistant.

Three lessons on QUILL's own voice -- how talkative it is, what carries an
announcement, and what to do when you missed one -- and three on the AI
assistant, which is optional, explicit, and never quietly changes engines.
"""

from __future__ import annotations

from quill.core.tutorials.model import Step, Tutorial

TUTORIALS: tuple[Tutorial, ...] = (
    Tutorial(
        slug="how-much-it-says",
        title="Decide how much QUILL says",
        track="voice",
        minutes=6,
        surfaces=("QUILL",),
        summary=(
            "Verbosity profiles, the channels that carry an announcement, and the "
            "two settings that stop a burst of speech from burying you."
        ),
        steps=(
            Step(
                title="Open verbosity preferences",
                body=(
                    "Find it in the command palette by typing verbosity. This is "
                    "the window that decides how talkative QUILL is -- which is a "
                    "different question from how talkative your screen reader is, "
                    "and QUILL never duplicates what the reader already says."
                ),
                command="app.command_palette",
                hear="The verbosity window, with your current profile.",
            ),
            Step(
                title="Pick a talkativeness",
                body=(
                    "Beginner gives full context for every action; Normal is "
                    "informative and is the default; Expert suppresses routine "
                    "confirmations but never errors; Quiet turns speech and "
                    "earcons off, leaving braille and the status bar."
                ),
                hear="The profile you chose, announced as you switch.",
            ),
            Step(
                title="Choose what carries an announcement",
                body=(
                    "Speech, braille and sound can each be turned off. Visual -- "
                    "the status bar -- is always on and cannot be turned off, so "
                    "you never lose the on-screen record of what happened."
                ),
                hear="Each channel as you set it.",
            ),
            Step(
                title="Go quiet for a meeting",
                body=(
                    "Quiet Mode silences speech and earcons; Meeting Mode quiets "
                    "sound further. A Q or M indicator shows while one is on, the "
                    "status bar keeps updating, and Undo Verbosity Change steps "
                    "back the last change you made."
                ),
                hear="Quiet mode on -- and then nothing, which is the point.",
            ),
            Step(
                title="Stop a burst from burying you",
                body=(
                    "Collapse repeated announcements (on by default) stops QUILL "
                    "repeating itself when you hold a key at the end of a list. An "
                    "optional announcement budget caps how many are spoken in five "
                    "seconds. Both affect speech only: the status bar shows "
                    "everything."
                ),
                hear="One announcement instead of fifteen.",
            ),
            Step(
                title="Trim two specific cues",
                body=(
                    "Announce entering and leaving dialogs is off by default, "
                    "because your screen reader already announces dialogs and "
                    "reads their titles. Announce indentation depth on Tab is on, "
                    "because 4 spaces is more useful than Indented lines."
                ),
                hear="The setting read back.",
            ),
            Step(
                title="Read what it just said",
                body=(
                    "The Spoken Echo remembers the last twenty announcements as "
                    "text you can arrow through and copy. It records only what "
                    "QUILL speaks -- never your typing -- and it is the answer to "
                    "an announcement that went past while you were thinking."
                ),
                keys=("Alt+Shift+E",),
                hear="The recent announcements, newest first.",
            ),
        ),
        closing=(
            "QUILL speaks alongside your screen reader rather than instead of it. "
            "Every setting here is about how much of its own voice you want."
        ),
        then=("profiles-and-keys",),
    ),
    Tutorial(
        slug="set-up-the-assistant",
        title="Set up the assistant, or do not",
        track="ai",
        minutes=6,
        surfaces=("QUILL", "AI Hub"),
        summary=(
            "On-device or a provider, where the keys live, and the honesty rules "
            "the assistant follows about what it did with your text."
        ),
        steps=(
            Step(
                title="Know that it is optional",
                body=(
                    "QUILL includes an assistant; it does not require one. It runs "
                    "on-device with a local model, or connects to a provider you "
                    "choose explicitly -- Ollama, OpenAI, Claude, OpenRouter, "
                    "Gemini, or a custom endpoint. Nothing is configured for you."
                ),
                hear="Nothing: this is the fact that makes the rest optional.",
            ),
            Step(
                title="Open the AI Hub",
                body=(
                    "One window for every provider's key, model and test chat, "
                    "plus per-provider key removal. It replaced two separate menu "
                    "items, because a key and the model it unlocks are one "
                    "subject."
                ),
                hear="The Hub, with each provider and whether it is configured.",
            ),
            Step(
                title="Start with the one that needs no key",
                body=(
                    "Ollama needs no key at all: install it, run it, and QUILL "
                    "detects it on localhost. It is the shortest path to a working "
                    "assistant that sends nothing anywhere."
                ),
                hear="Ollama detected, and the models it holds.",
            ),
            Step(
                title="Know where a key is kept",
                body=(
                    "In the Windows Credential Manager, tied to your Windows "
                    "account -- or, in portable mode, in a DPAPI-encrypted file "
                    "beside your data. Never in a settings file, never in a log, "
                    "never in a diagnostic bundle, and never in QUILL's own "
                    "program files."
                ),
                hear="Nothing: this is the promise behind the field.",
            ),
            Step(
                title="Test it before you rely on it",
                body=(
                    "Test Chat in the Hub proves the key and the model work "
                    "together. Doing that once, deliberately, is better than "
                    "finding out in the middle of a document."
                ),
                hear="The model's reply, in the Hub.",
            ),
            Step(
                title="Know the honesty rules",
                body=(
                    "If your document had to be trimmed to fit the model, QUILL "
                    "says how much of it the answer used. If your provider was "
                    "unreachable and the chat started on the on-device model "
                    "instead, it says so the moment the chat opens. And it never "
                    "switches to a cloud engine without telling you that is what a "
                    "switch would mean."
                ),
                hear="The sentence naming which engine answered, and on how much of the document.",
            ),
        ),
        closing=(
            "Optional, explicit, and honest about what it did. If you never open "
            "the Hub, QUILL is a text editor and nothing else."
        ),
        then=("ask-and-prompts",),
    ),
    Tutorial(
        slug="ask-and-prompts",
        title="Ask, and run a prompt",
        track="ai",
        minutes=6,
        surfaces=("QUILL",),
        summary=(
            "The writing assistant, the one-shot question, and the prompt library "
            "-- including how to change what a built-in prompt actually says."
        ),
        steps=(
            Step(
                title="Ask a question",
                body=(
                    "The writing assistant is a message-style window where you can "
                    "ask, draft, propose edits and run QUILL commands -- with your "
                    "approval before any change is applied. The provider and model "
                    "in use are shown, and can be switched in the window."
                ),
                command="tools.ask_quill_chat",
                hear="The assistant, with focus in the prompt field when a model is configured.",
            ),
            Step(
                title="Send, and read the answer",
                body=(
                    "Ctrl+Enter sends. QUILL announces Sending and disables the "
                    "button while the request is in flight, so a slow model is "
                    "never mistaken for a dead one. The response opens read-only, "
                    "with Copy to Clipboard."
                ),
                keys=("Ctrl+Enter",),
                hear="Sending, then the reply as reviewable text.",
            ),
            Step(
                title="Open the prompt library",
                body=(
                    "A searchable list of prompts on the left, the selected "
                    "prompt's instruction on the right, and an optional input "
                    "field. With the field blank it uses your selection, or the "
                    "whole document."
                ),
                hear="The prompts, filtered as you type.",
            ),
            Step(
                title="Run one on a selection",
                body=(
                    "Select a paragraph, choose Summarize or Improve Clarity or "
                    "Make Concise, and run it. Nothing is applied automatically -- "
                    "the result opens as a response you read and decide about."
                ),
                hear="The result, in the response window.",
            ),
            Step(
                title="Change what a built-in prompt says",
                body=(
                    "Every built-in can have its wording overridden or be "
                    "disabled, though built-ins cannot be deleted. Edit Check "
                    "Grammar's text and the Check Grammar command picks up your "
                    "version automatically."
                ),
                hear="The prompt saved under your wording.",
            ),
            Step(
                title="Check grammar without being rewritten",
                body=(
                    "Check Grammar with AI lists corrections as original phrase, "
                    "arrow, corrected phrase, and a reason. It does not rewrite "
                    "the passage and it applies nothing: you make the changes you "
                    "agree with."
                ),
                command="tools.ai_grammar_style",
                hear="Each correction with its reason, and your document untouched.",
            ),
        ),
        closing=(
            "Ask for a question, the library for a job you do often, and neither "
            "one changes your document without you."
        ),
        then=("ai-on-a-selection",),
    ),
    Tutorial(
        slug="ai-on-a-selection",
        title="The assistant on one piece of text",
        track="ai",
        minutes=4,
        surfaces=("QUILL",),
        summary=(
            "Translate, thesaurus, describe an image, and the spell check that "
            "asks a model -- each on the thing you have selected."
        ),
        steps=(
            Step(
                title="Translate a selection",
                body=(
                    "Translate Selection works on what you have highlighted, so "
                    "you can bring one paragraph across without sending a whole "
                    "document anywhere."
                ),
                command="tools.ai_translate_selection",
                hear="The translation, as a response you can copy.",
            ),
            Step(
                title="Ask for a better word",
                body=(
                    "The AI thesaurus is the other half of the offline one: it "
                    "answers with alternatives in the sentence's own context "
                    "rather than a dictionary list."
                ),
                command="tools.ai_thesaurus",
                hear="The alternatives, with the sense each fits.",
            ),
            Step(
                title="Describe an image",
                body=(
                    "Describe Image is the command that matters most in somebody "
                    "else's document. It answers what a picture is, which is the "
                    "one thing a screen reader cannot do for you."
                ),
                command="tools.describe_image",
                hear="The description, as text you can review and copy.",
            ),
            Step(
                title="Run an AI spell check",
                body=(
                    "AI Spell Check and its interactive form are separate from the "
                    "ordinary dictionary check, because they answer a different "
                    "question: not is this word in a list, but is this the word "
                    "you meant."
                ),
                command="tools.ai_spell_check_interactive",
                hear="Each finding, one at a time.",
            ),
            Step(
                title="Switch engines deliberately",
                body=(
                    "Switch AI Engine changes which model answers. QUILL will "
                    "offer a switch when a call fails and the other kind of engine "
                    "could take it -- and it never makes that switch for you, "
                    "always saying when one would send your text to the cloud."
                ),
                command="tools.ai_switch_engine",
                hear="Which engine is now answering.",
            ),
        ),
        closing=(
            "Every one of these works on a selection, which is the honest unit: "
            "you decide how much text leaves the paragraph you are in."
        ),
    ),
)
