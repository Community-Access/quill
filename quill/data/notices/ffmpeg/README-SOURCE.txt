FFmpeg for QuillVille apps -- provenance and corresponding source
=================================================================

This folder contains ffmpeg.exe and ffprobe.exe from FFmpeg, redistributed
unmodified. QUILL and the QuillVille apps (Quill Converter, Quill Radio,
Audio Studio, Quill Cast) run them as separate programs to convert, play and
inspect sound and video files -- bundled in the installers, or fetched when
you ask QUILL to get FFmpeg.

Binary provenance
-----------------
Version: FFmpeg 8.1.2
Build:   gyan.dev "essentials" build for 64-bit Windows
Asset:   ffmpeg-8.1.2-essentials_build.zip
         SHA-256 db580001caa24ac104c8cb856cd113a87b0a443f7bdf47d8c12b1d740584a2ec
         (mirrored unmodified at
         https://github.com/Community-Access/quill/releases/download/assets-v1/)
URL:     https://www.gyan.dev/ffmpeg/builds/

License
-------
This build of FFmpeg is configured with --enable-gpl --enable-version3 and is
therefore licensed under the GNU General Public License, version 3 or (at your
option) any later version. The full licence text is in LICENSE.GPLv3.txt in
this folder. Running "ffmpeg -L" prints the same notice.

FFmpeg is a trademark of Fabrice Bellard, originator of the FFmpeg project.

Corresponding source
--------------------
- FFmpeg 8.1.2:   https://ffmpeg.org/releases/ffmpeg-8.1.2.tar.xz
                  https://git.ffmpeg.org/ffmpeg.git (tag n8.1.2)
- The build:      https://www.gyan.dev/ffmpeg/builds/ lists the source of
                  every library linked into the essentials build.

On request, Community Access will provide a copy of the corresponding source
for three years from the date of distribution. Write to
support@community-access.org.

The QuillVille apps themselves are MIT-licensed, with source at
https://github.com/Community-Access/quill. They are not linked with FFmpeg;
they start it as a separate program.
