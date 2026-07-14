## Translation: [Language name] ([lang code])

**Language code:** <!-- e.g. fr, de, es, pt_BR -->
**Language name:** <!-- e.g. French, German, Spanish, Brazilian Portuguese -->

## Coverage

Run `python -m quill.tools.check_translation` and paste the coverage line here:

```
check_translation: OK — fr: 87% (412/474 strings)
```

## Checklist

- [ ] Created from `quill/locale/quill.pot` (current version)
- [ ] File placed at `quill/locale/{lang}/LC_MESSAGES/quill.po`
- [ ] `python -m quill.tools.check_translation` passes with no errors
- [ ] Tested locally with `pybabel compile -d quill/locale -D quill` and launched QUILL
- [ ] Mnemonic `&` markers preserved on all menu and button strings
- [ ] Placeholders (`{name}`, `%(name)s`) preserved and not translated
- [ ] Plural forms header matches language rules (if language has non-English plurals)
- [ ] Screen reader strings (`# SPEECH:` comments in .pot) reviewed for natural speech

## Notes for reviewers

<!-- Any strings that were hard to translate, terminology decisions, or known gaps. -->
