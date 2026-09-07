from quilllite.commands import COMMANDS, shortcut_text


def test_every_item_has_a_key_and_handler():
    for _menu, label, key, handler, kind in COMMANDS:
        if kind == "sep":
            continue
        assert key, f"{label} has no key"
        assert handler.startswith("cmd_"), f"{label} handler {handler}"


def test_no_two_items_share_a_key():
    seen = {}
    for _menu, label, key, _handler, kind in COMMANDS:
        if kind == "sep":
            continue
        normalised = key.lower()
        assert normalised not in seen, f"{key} bound to both {seen[normalised]} and {label}"
        seen[normalised] = label


def test_window_switch_keys_are_reserved():
    keys = {key.lower() for _m, _l, key, _h, kind in COMMANDS if kind != "sep"}
    for digit in range(1, 10):
        assert f"alt+{digit}" not in keys


def test_no_duplicate_mnemonics_within_a_menu():
    per_menu: dict[str, dict[str, str]] = {}
    for menu, label, _key, _handler, kind in COMMANDS:
        if kind == "sep" or "&" not in label:
            continue
        letter = label[label.index("&") + 1].lower()
        taken = per_menu.setdefault(menu, {})
        assert letter not in taken, f"{menu}: & {letter} used by {taken[letter]} and {label}"
        taken[letter] = label


def test_shortcut_text_mentions_every_key():
    text = shortcut_text()
    for _m, _label, key, _h, kind in COMMANDS:
        if kind != "sep":
            assert key in text
