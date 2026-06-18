# Third-Party Notices

QUILL includes vendored or directly-referenced open-source components.
Full license texts are reproduced below and in the relevant source directories.

---

## autoupdate

- **Source:** quill/_vendor/autoupdate/
- **Upstream:** https://github.com/accessibleapps/app_updater
- **Author:** Christopher Toth
- **License:** MIT

```
Copyright (c) 2012 Christopher Toth

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```

---

## html_to_text (AccessibleApps)

- **Source:** installed as `html_to_text` package dependency
- **Upstream:** https://github.com/accessibleapps/html_to_text
- **Author:** AccessibleApps contributors (Christopher Toth and community)
- **License:** MIT
- **Used for:** Detecting HTML content on the clipboard and converting it to clean, structured plain text. Powers the intelligent HTML paste feature (`quill/ui/html_paste_cleaner.py`).

```
Copyright (c) AccessibleApps contributors

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```

---

## words_alpha.txt

- **Source:** quill/data/words_alpha.txt
- **Upstream:** https://github.com/dwyl/english-words
- **License:** Unlicense (public domain)

---

## thesaurus data (th_en_US_v2)

- **Source:** quill/data/th_en_US_v2.dat
- **Upstream:** https://mythes.sourceforge.net/
- **License:** LGPL 2.1 — see quill/data/th_en_US_LICENSE.txt

The WordNet portion of the thesaurus data is additionally covered by the
Princeton WordNet license — see quill/data/th_en_US_WordNet_LICENSE.txt.
