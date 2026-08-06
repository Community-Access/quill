# Media Player -- not part of public QUILL 1.0

> **Not part of the public 1.0 product.** **Tools > Media > Media Player...**
> (`app.open_media_player`) is gated for QUILL 1.0.0: `main_frame_menu.py` only
> appends the item when `is_app_released("player")` is true, and `player` is not
> in `RELEASED_APPS` (`quill/core/app_launcher.py`). The command is absent from
> the menu bar and from the command palette in a public build.
>
> The Media Player never had a chapter of its own in the user guide or a section
> of its own in the PRD -- it appeared only as passing mentions inside otherwise
> public prose about dictation and voice interaction. Those sentences were
> rewritten to drop the mention during the 1.0.0 documentation consolidation, and
> the removed material is preserved here so nothing is lost. When the player
> ships publicly, this is the material to promote back.

**Where each part came from**

| Relocated from | Source section |
|---|---|
| `docs/user guide/userguide.md` | "Locked Dictation (Ctrl+F9)" -- "Teach dictation your words" bullet |
| `docs/user guide/voice-interaction.md` | "Teaching dictation your words" -- where the profile applies |
| `docs/user guide/voice-interaction.md` | "Choosing a speech engine and model" -- which engine the player uses |
| `docs/user guide/voice-interaction.md` | "Roadmap" -- the shipped hands-free-voice item |
| `QUILL-PRD.md` | (nothing -- the PRD has no Media Player section) |

---

# Relocated material

## The dictation profile applies to the Media Player too

_From the user guide's "Teach dictation your words" bullet, and from
`voice-interaction.md`'s "Teaching dictation your words" section. Both now list
only Locked Dictation and the Dictate (Offline) toggle._

The `dictation.md` profile in your QUILL data folder -- your own vocabulary,
spoken-to-written replacements, and custom spoken command phrases -- applies
everywhere dictation transcribes: **Locked Dictation**, the **Dictate (Offline)**
toggle, and the **Media Player's** hands-free voice commands.

## The Media Player's speech engine

_From `voice-interaction.md`, "Choosing a speech engine and model". The public
text now ends with the list of engines._

The engine you set as default in QUILL is the one the Media Player uses for
hands-free voice too. For short commands the player automatically prefers a
small, fast model.

## Roadmap entry

_From `voice-interaction.md`, "Roadmap". The public list of shipped polish
refinements no longer names the player._

Hands-free voice commands in the **Media Player** shipped as part of the voice
interaction polish refinements, alongside true silence detection, personalized
and optionally-spoken prompts with screen-reader parity, the Speak Voice Status
check, and the editable dictation profile (`dictation.md`).

## Gating reference

- Command id: `app.open_media_player` (`quill/ui/main_frame_media_player.py`).
- Menu path when released: **Tools > Media > Media Player...**
  (`quill/ui/main_frame_menu.py`, guarded by `is_app_released("player")`).
- Default key binding: none (`quill/core/keymap.py` maps it to the empty string).
- Sign-off expectation for 1.0.0: verified **absent** from every public surface
  (`docs/planning/signoff/QUILL-1.0.0-SIGNOFF.md`, section G).
