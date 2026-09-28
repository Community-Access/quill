# KSPN drop test plan

Purpose: find out why Quill Radio 3.0.3 connects to KSPN, plays a few seconds,
loses the stream and reconnects in a loop, while VLC plays the same address
without trouble on the same machine.

Established so far (from the developer's machine):

- Both KSPN mounts play for 40 seconds with no reconnect under ffmpeg with the
  app's exact options. The station and Amperwave are healthy from here.
- A server that ends a session cleanly is reported by mpv as end of file. The
  app then announces "Reconnecting", reloads, succeeds, resets its counter,
  and repeats. That is the loop the reporter hears. Play stays pressed by
  design while reconnecting.
- Nothing in quill.log records why a stream ended.

Because VLC works on the reporter's machine, the remaining candidates are all
on that machine and all differ between VLC and Quill Radio:

1. Security software or a web filter that inspects HTTPS per process and
   cuts long responses; VLC is usually exempt, Quill Radio is not.
2. Sound Enhancements or exact OptiLab on, which routes audio through a local
   ffmpeg relay with its own HTTP fetch.
3. The mpv engine not actually in use (fell back to Windows Media).
4. Something in ffmpeg's HTTP request on that path (Range header, ICY
   metadata request, TLS backend).

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

## Step 1: Sound Enhancements and OptiLab off

1. Open Preferences.
2. Turn off Sound Enhancements (equalizer, compressor, night mode, mono).
3. Make sure OptiLab is off, including any "exact" or "live" OptiLab option.
4. Play KSPN for two minutes.

Result (plays two minutes / drops after N seconds): 

## Step 2: Which engine is playing

1. Open Help, then Media Health (or the media health notice if one is shown).
2. Read the line about the mpv playback engine.

Record the exact wording: 

If it says the mpv engine is missing or Windows Media is in use, reinstall
Quill Radio 3.0.3 and check again before continuing.

## Step 3: Engine switch

1. Preferences, playback engine. Note the current setting: 
2. Set it to mpv. Play KSPN for two minutes.

   Result: 

3. Set it to Windows Media. Play KSPN for two minutes.

   Result: 

4. Put the setting back to what it was.

Different results on the two engines means the fault is in the HTTP client,
not the station.

## Step 4: Security software

Only for one test, then turn it back on.

1. Pause the security suite's web protection, HTTPS scanning, or web shield.
2. Play KSPN for two minutes.

   Result: 

3. Turn protection back on.

If KSPN played for two minutes, add Quill Radio to the suite's exclusions
and confirm it still plays with protection on:

   Result with exclusion: 

## Step 5: The decisive test, from a command prompt

This uses the same ffmpeg that Quill Radio ships and writes a log file that
names the reason the stream ended. Close Quill Radio first so the two are not
competing.

1. Press Windows key, type cmd, press Enter.
2. Paste each line and press Enter after it.

```
cd %LOCALAPPDATA%\QuillVille\Runtime\3.13\tools\ffmpeg
ffmpeg -report -reconnect 1 -reconnect_streamed 1 -reconnect_on_network_error 1 -reconnect_delay_max 30 -user_agent "Quill Radio/3.0.3" -i "https://live.amperwave.net/direct/goodkarma-kspnamaac-ibc?source=TuneIn&gdpr=0" -t 120 -f null -
```

3. Let it run. It should take about two minutes and then stop on its own. If
   it stops in under a minute, that is the fault reproduced outside the app.
4. In that same folder there is now a file named ffmpeg-<date>-<time>.log.
   Send that file.

Record:

- Did it run the full two minutes (yes / no, stopped after N seconds): 
- Log file name: 

If the folder above does not exist, find ffmpeg.exe by searching the Quill
Radio install folder and run the same command from there.

## Step 6: Only if step 5 ran the full two minutes

Then ffmpeg's HTTP client is fine on this machine and the fault is inside the
app process. Repeat step 5 with Quill Radio open and KSPN playing at the same
time, and note whether either one drops:

- ffmpeg alone: 
- ffmpeg with Quill Radio playing KSPN: 

## What to send back

- This file with the blanks filled in.
- The ffmpeg-<date>-<time>.log from step 5.
- quill.log from the Quill data folder (Help, Open data folder, then logs).

## Note for the developer

This file is a temporary worksheet in the repository root. The root layout
gate will flag it; delete it when the data is in rather than committing it.
