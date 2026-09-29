# KSPN drop test plan

Purpose: find out why Quill Radio 3.0.3 connects to KSPN, plays a few seconds,
loses the stream and reconnects in a loop, while VLC plays the same address
without trouble on the same machine.

## Established so far

From the developer's machine:

- Both KSPN mounts play for 60 seconds through the shipped libmpv with the
  app's exact options, on the null output and on a real WASAPI device. The
  station, Amperwave, and the mpv build are fine here.
- A server that ends a session cleanly is reported by mpv as end of file.
  The app then announces "Reconnecting", reloads, succeeds, resets its
  counter, and repeats. Play stays pressed by design while reconnecting.
- An audio output device that fails while a stream is playing produces the
  SAME report: mpv ends the file within a fifth of a second and the app says
  "Reconnecting" as if the connection had dropped. A device that cannot be
  opened at load time produces an error and a fall back to Windows Media.
- Nothing in quill.log records which of these happened.

From the reporter's machine (2026-09-28):

- VLC plays the address.
- ffmpeg (step 5 below) held the address for the full 120 seconds: 2
  connections (one redirect), 0 retries, 0 reconnections, 0 decode errors.
  ffmpeg's HTTP client and the network path are fine on that machine.

So the fault is inside the app process and is NOT the station or the network.
Remaining candidates, in order:

1. The audio output device. A Bluetooth or USB headset that sleeps, a device
   chosen in Preferences whose id has changed, or a device the screen reader
   and the app contend for. VLC recovers from device loss on its own; ffmpeg
   in step 5 used no device at all.
2. Sound Enhancements or exact OptiLab on, which routes audio through a local
   ffmpeg relay with its own HTTP fetch.
3. The mpv engine not actually in use (fell back to Windows Media).
4. Security software that treats the Quill Radio process differently from
   ffmpeg.exe and VLC.

Run the steps in order. Stop at the first one that changes the behaviour and
send everything recorded up to that point.

## Before starting

Record these once.

- Windows version (Settings, System, About).
- Security software installed (name and whether web or HTTPS protection is on).
- Whether the machine is on home wifi, a workplace network, a VPN, or a hotspot.
- The exact address of the KSPN favorite: Favorites, select KSPN, open its
  properties or edit view, copy the stream address. Paste it here:

  Favorite address: 

- How many seconds of audio play before each drop, over three drops:

  Drop 1: 
  Drop 2: 
  Drop 3: 

- Audio output. What plays the sound: built-in speakers, a wired headset, a
  USB headset, a Bluetooth headset or speaker, or an HDMI display:

  Output hardware: 

- Whether the screen reader speaks through the same device:

  Same device as screen reader (yes / no): 

## Step 1: Output device (most likely)

1. Preferences, radio output device. Note the current setting:

   Current setting: 

2. If it is anything other than System default, set it to System default.
   Play KSPN for two minutes.

   Result: 

3. If the sound goes through Bluetooth or a USB headset, switch Windows'
   default output to the built-in speakers (or plug in wired headphones),
   keep the app on System default, and play KSPN for two minutes.

   Result on a wired or built-in device: 

4. Play KSPN and, while it plays, make the screen reader talk continuously
   for thirty seconds (read a long document). Note whether a drop happens
   while it is speaking.

   Drops while the screen reader speaks (yes / no): 

## Step 2: Sound Enhancements and OptiLab off

1. Open Preferences.
2. Turn off Sound Enhancements (equalizer, compressor, night mode, mono).
3. Make sure OptiLab is off, including any "exact" or "live" OptiLab option.
4. Play KSPN for two minutes.

Result (plays two minutes / drops after N seconds): 

## Step 3: Which engine is playing

1. Open Help, then Media Health (or the media health notice if one is shown).
2. Read the line about the mpv playback engine.

Record the exact wording: 

If it says the mpv engine is missing or Windows Media is in use, reinstall
Quill Radio 3.0.3 and check again before continuing.

## Step 4: Engine switch

1. Preferences, playback engine. Note the current setting: 
2. Set it to mpv. Play KSPN for two minutes.

   Result: 

3. Set it to Windows Media. Play KSPN for two minutes.

   Result: 

4. Put the setting back to what it was.

## Step 5: ffmpeg from a command prompt (DONE, passed)

Run on 2026-09-28 with ffmpeg 8.1.2. Held the stream for 120 seconds, 0
reconnections. Nothing more needed here.

## Step 6: Security software

Only for one test, then turn it back on.

1. Pause the security suite's web protection, HTTPS scanning, or web shield.
2. Play KSPN for two minutes.

   Result: 

3. Turn protection back on.

If KSPN played for two minutes, add Quill Radio to the suite's exclusions
and confirm it still plays with protection on:

   Result with exclusion: 

## Step 7: Another station on a different host

Play a station that is not on Amperwave for five minutes, for example
Quill Radio's own SomaFM entries, and note whether it drops the same way.

   Station tried: 
   Result: 

If it drops too, the station was never the cause and step 1 is where the
answer is.

## What to send back

- This file with the blanks filled in.
- quill.log from the Quill data folder (Help, Open data folder, then logs).

## Note for the developer

This file is a temporary worksheet in the repository root. The root layout
gate will flag it; delete it when the data is in rather than committing it.
