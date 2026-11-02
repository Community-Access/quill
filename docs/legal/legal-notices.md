# Licence and Legal Notices

## QUILL for All

QUILL for All is an independent open-source project by Community Access. It is
an accessibility-focused editor that helps people write, edit, convert,
compare, and publish documents in a screen-reader-friendly environment, and it
is the editor at the heart of the QuillVille family of apps.

QUILL for All and every app in the family are free and never sold. The family
is Jeff Bishop's personal project and is not used commercially. Donations only
cover the cost of the free AI service.

## Licence

The family's own code is released under the MIT License. The full text is in
the LICENSE file at the root of the source repository, and every installer and
portable copy ships it as LICENSE.txt beside the program.

The copyright holder of the family's own code is Jeff Bishop:

> Copyright (c) 2026 Jeff Bishop

The NOTICE file at the root of the repository carries the project's
independence statement and points to the third-party notices.

## Independence Notice

QUILL for All is not affiliated with, sponsored by, or endorsed by Quill.js,
QuillBot, Quill.org, or any other similarly named product, project, company,
or organisation.

Any references to third-party products, services, organisations, or projects
are for identification, compatibility, attribution, or documentation purposes
only. See [Trademarks and Naming](TRADEMARKS.md).

## Third-party components

The family includes software, data, models and sounds from other projects,
each under its own licence. They are listed, with their licences, copyright
holders and what each licence asks of us, in the
[Third-Party Notices](THIRD_PARTY_NOTICES.md).

The same notices reach people in three places:

- **In every app:** Help, then About, then the **Licences and Notices** button.
  In QUILL itself, Help > Open Third-Party Notices (also a button in Help >
  About QUILL) opens them in a new document tab.
- **Beside the program:** every installer and portable copy puts
  THIRD-PARTY-NOTICES.txt and LICENSE.txt in the app's own folder.
- **In the repository:** this folder. The notices are generated from
  quill/data/third_party/components.json by
  quill/tools/build_third_party_notices.py, and a test fails if any copy
  drifts from that catalogue or if a build ships a library it does not list.

Some components are under the GNU GPL, LGPL or AGPL. The exact source of every
one of them, for the version we ship, is published with each release, beside
LICENSE.txt and THIRD-PARTY-NOTICES.txt, and is also available on request.
QUILL's own source code is public at https://github.com/Community-Access/quill.

### PyMuPDF and the other copyleft components

The shared QuillVille Runtime includes PyMuPDF under the AGPL-3.0. QUILL keeps
it and complies with that licence: the installed apps are distributed under
the AGPL as combined works, each of QUILL's own files stays under MIT, and the
exact PyMuPDF source is published with every release. AGPL section 13 does not
apply to the desktop apps, because none of them runs a network service; GLOW's
web app links its own source on every page. The
[PyMuPDF licensing record](PYMUPDF-AGPL-REVIEW.md) has the details.

The family also distributes libmpv, mutagen and pillow-heif, which are GPL, and
keeps them on the same terms: their exact source is published with each
release. FFmpeg, eSpeak NG, Pandoc and Git run as separate programs; where the
family ships one, its source is published the same way.

The BASS audio libraries inside sound_lib are used under Un4seen's free
non-commercial licence, which fits because the family is never sold. DECtalk is
not distributed or linked: QUILL only drives a copy you install yourself, and
keeps nine short preview clips so you can hear it. All 39 Piper voices stay
available, each under the terms its model card names; several of those allow
only non-commercial use, which is the only way the family is used.

## Privacy and AI

How the family handles your data is in the [Privacy Statement](PRIVACY.md), and
how to use its AI features responsibly is in
[Responsible and Ethical AI Use](RESPONSIBLE_AI_USE.md).
