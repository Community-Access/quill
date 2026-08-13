"""Where system-wide expansion must not fire.

Expanding text into the wrong window is worse than not expanding at all: a
password manager's search box, a login prompt, or a lock screen are all places
where erasing characters and typing replacements could destroy a credential or
put one somewhere it does not belong.

The rule is deliberately conservative and decided from the foreground window
alone -- process name, window class, and title -- never from what was typed.
When in doubt, refuse: a missed expansion costs a keystroke, and the alternative
costs trust.

Pure and wx-free; the platform layer supplies the three strings.
"""

from __future__ import annotations

#: Executables where expansion never runs. Password managers first, then the
#: Windows credential and lock surfaces.
DENIED_PROCESSES: frozenset[str] = frozenset({
    "1password.exe",
    "bitwarden.exe",
    "credentialuibroker.exe",
    "dashlane.exe",
    "enpass.exe",
    "keepass.exe",
    "keepassxc.exe",
    "keeper.exe",
    "lastpass.exe",
    "lockapp.exe",
    "logonui.exe",
    "nordpass.exe",
    "roboform.exe",
    "consent.exe",  # the UAC prompt
})

#: Window classes that are credential or secure-desktop surfaces regardless of
#: which process owns them.
DENIED_WINDOW_CLASSES: frozenset[str] = frozenset({
    "Credential Dialog Xaml Host",
    "#32770 (Dialog)",  # only when paired with a denied title, see below
})

#: Title fragments (matched case-insensitively) that mean a credential prompt.
DENIED_TITLE_FRAGMENTS: tuple[str, ...] = (
    "sign in",
    "sign-in",
    "log in",
    "log on",
    "password",
    "passcode",
    "credential",
    "authenticat",
    "unlock",
    "windows security",
)


def is_denied_target(
    process_name: str,
    window_title: str = "",
    window_class: str = "",
    extra_processes: frozenset[str] | set[str] | None = None,
) -> bool:
    """Whether expansion must be suppressed for this foreground window.

    *extra_processes* carries the user's own exclusions (Options > Excluded
    applications), matched the same way as the built-in list.
    """
    process = process_name.strip().lower()
    if process:
        if process in DENIED_PROCESSES:
            return True
        if extra_processes and process in {p.strip().lower() for p in extra_processes}:
            return True
    if window_class.strip() == "Credential Dialog Xaml Host":
        return True
    title = window_title.strip().lower()
    return any(fragment in title for fragment in DENIED_TITLE_FRAGMENTS)


#: Applications that need the clipboard route rather than typed keystrokes.
#: Empty by design: rather than guessing which programs misbehave, Inkwell lets
#: someone add the one that does. ``injection_mode_for`` resolves it.
DEFAULT_PASTE_PROCESSES: frozenset[str] = frozenset()


def injection_mode_for(
    process_name: str,
    *,
    default_mode: str = "type",
    paste_processes: frozenset[str] | set[str] | None = None,
) -> str:
    """How to deliver an expansion to *process_name*: ``"type"`` or ``"paste"``.

    Typed keystrokes are right almost everywhere and never touch the clipboard.
    A few targets drop synthetic keys, and for those the answer has to be per
    application rather than a global switch -- otherwise fixing one stubborn app
    means every other app pays the cost of the clipboard being borrowed.
    """
    process = process_name.strip().lower()
    if process:
        listed = {p.strip().lower() for p in (paste_processes or set())}
        if process in listed or process in DEFAULT_PASTE_PROCESSES:
            return "paste"
    return default_mode if default_mode in ("type", "paste") else "type"
