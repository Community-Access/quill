# Licence and Legal Notices

## QUILL for All

QUILL for All is an independent open-source project by Community Access. It is
an accessibility-focused editor that helps people write, edit, convert,
compare, and publish documents in a screen-reader-friendly environment, and it
is the editor at the heart of the QuillVille family of apps.

QUILL for All and every app in the family are free and never sold. Donations
only cover the cost of the free AI service.

## Licence

The family's own code is released under the MIT License. The full text is in
the LICENSE file at the root of the source repository, and every installer and
portable copy ships it as LICENSE.txt beside the program.

The LICENSE file retains the existing holder and also names Jeff Bishop:

> Copyright (c) 2026 Blind Information Technology Solutions (BITS)
>
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

Some components are under the GNU GPL, LGPL or AGPL. The source code of the
version we ship is available on request, as the Third-Party Notices explain;
QUILL's own source code is public at https://github.com/Community-Access/quill.
QUILL retains PyMuPDF under AGPL-3.0. Its full licence text and version-specific
source archive details appear in every applicable notice. The scope of
Corresponding Source for QUILL's shared runtime and application packages is
under legal review; see the [PyMuPDF licensing review](PYMUPDF-AGPL-REVIEW.md).

### GPL-family components and release review

The family also distributes GPL-family components, including libmpv, mutagen
and some builds of pillow-heif. Their actual licences, copyright notices,
versions and source locations are listed in Third-Party Notices. FFmpeg,
eSpeak NG, Pandoc and Git can be distributed as separate programs, but running
a program separately is not by itself a legal conclusion about every possible
distribution or integration.

The project will preserve each component's applicable notices and source
information and review the exact binaries, build inputs, source and scripts for
each release. GPL and AGPL obligations, the boundary between separate and
combined works, and any source-offer requirements need review for the actual
distribution. Do not describe the whole family as MIT-only, or declare that
all original QUILL code is automatically relicensed, without resolving those
questions. If a component cannot be distributed on acceptable terms, replace
or omit it before release rather than assuming a source link alone suffices.

## Privacy and AI

How the family handles your data is in the [Privacy Statement](PRIVACY.md), and
how to use its AI features responsibly is in
[Responsible and Ethical AI Use](RESPONSIBLE_AI_USE.md).
