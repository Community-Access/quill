# Dial tuning: decisions

Agreed with Jeff on 2026-11-07. The idea comes from BlindRadio by serrebidev (MIT),
github.com/serrebidev/blindradio, doc/readme.md "Dial tuning".

## Ships off

"Tune as I move through stations" is off by default, so nobody's arrow keys change
behaviour after an update. It is switched on in Preferences > Listening, or by a command
with its own key.

## Every part is a setting

Each row lives in Preferences > Listening, under the main setting, and has F1 help.

| Setting | Default | Choices |
|---|---|---|
| Tune as I move through stations | Off | On, Off |
| Wait before tuning | About a third of a second (350 ms) | Instant, 200 ms, 350 ms, 500 ms, 1 second |
| Keep the next and previous stations connected | On | On, Off |
| Stop keeping neighbours connected on a metered connection | On | On, Off |
| Sound between stations (soft hiss) | On | On, Off; level Low, Medium |
| Remember each station's volume | Off | On, Off |

## Behaviour

- Only live station lists tune: Favorites, Recently Played, Browse folders of stations,
  Networks and Search results. Podcasts, YouTube, folders and anything on demand never do.
- Stopping on a station plays it after the wait. Holding an arrow plays nothing until you stop.
- Nothing is spoken beyond the screen reader's own reading of the row (GATE-13).
- Enter commits: plays for real, starts a fresh time-shift buffer, adds to Recently Played.
  Stations only passed through are not added to Recently Played or song history.
- Leaving the list keeps the last station playing. Go to Playing Station finds its row.
- While recording, tuning pauses. Quill says so once, the first time you move.
- A dead station: the hiss stops. After a few seconds Quill says once that the station is
  not answering.
- At most three mpv players: the current station and up to two warm neighbours.
- Mute silences the hiss, which plays at a fixed level.
