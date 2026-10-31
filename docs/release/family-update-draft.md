# QUILL family update: draft announcement

**Draft for review, not a release announcement.** The changes below are in the
working tree or are plans; product packages and release dates must be verified
before this text is published.

## QUILL and Quill Radio

The shared Radio code retires its built-in SomaFM source in response to
SomaFM's published terms for third-party clients. Known catalogue entries and
direct playback and recording paths are filtered or blocked. Review of
indirect paths, existing user data and previously published packages is still
open. The change is not a new public release.

QUILL no longer downloads or distributes a legacy voice engine while its
redistribution terms are unclear. Separately installed copies still work;
complete removal, previous packages and other distribution paths need review.
New Studio portable builds copy only the supported speech engine folders.

## QUILL Lite and the shared Windows runtime

The shared Windows OCR and Media projections move to PyWinRT 4.0.3 and the
Windows SDK 10.0.28000.2705 projection line. This includes the Windows OCR
path used by QUILL and QUILL Lite, and Windows Media paths used by Radio and
Studio. Device references and player event handlers are released at shutdown
to address a Windows Media exit crash. This is a runtime change, not a promise
of new functionality or publication of any product update.

## QUILL Studio and Quill Converter

Studio already offers shared audio conversion and offline caption generation
for supported audio and video. Its consolidated production plan proposes
accessible project-to-Converter round trips, capability checks, batch review
and richer local or explicitly consented cloud transcription and AI assistance.
These proposed workflows are not a claim that the features have shipped.
Converter support depends on the available codecs and valid media; no
guarantee is made for every format or protected file.

## Release and legal checks

Installed editions of QUILL, QUILL Lite, Radio, Cast, Studio, Weather, Inkwell,
Converter, Transcribe, Beacon and Social use the shared QuillVille Runtime.
The current runtime carries PyMuPDF 1.28.2 under AGPL-3.0. Only QUILL exposes
the GLOW feature that brings it in; the other apps carry it in the runtime.
Media Player uses its host's runtime. Standalone portable packages have
separate contents and must be checked individually.

PyMuPDF's legal and Corresponding Source review remains a public-release gate.
The remaining GPL-family, asset-licence, attribution and prior-distribution
reviews are not complete. Update product-specific release notes, validate
actual staged packages and obtain the necessary approvals before publishing
this draft.
