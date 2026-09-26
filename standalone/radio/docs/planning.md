# Quill Radio Planning

Updated 2026-09-26, for the 3.0.0 release.

This is the list of Quill Radio work that has not been built yet. Features that
already shipped are in the release notes and the user guide, not here.

Every item below has to meet the same rule as the rest of the app: no paid tier,
no commercial agreement, no partner approval and no per-application developer
key. Directories that need any of those are non-goals, and the reasons are in
the PRD, section 7. Being allowed to read a directory's listings is also not the
same as being allowed to play or record its audio, so each source needs its own
check.

## Public software-defined radio receivers

Let a listener tune public SDR receivers (OpenWebRX with its Receiverbook
directory, KiwiSDR, WebSDR and UberSDR) from the keyboard. They pick a receiver,
a frequency, a mode such as AM, FM, USB or LSB, a filter width and a tuning
step, and Quill Radio speaks each change and the signal strength. This would
also give a practical way to hear marine VHF, airband, amateur, shortwave and
time-signal frequencies, with ready-made presets for each. Why: no accessible
receiver interface exists for blind radio listeners, and nothing else on this
list is as new. Constraint: a receiver being listed publicly does not mean it
may be embedded or automated, so this starts as open-in-browser and connects
directly only to receivers whose operators opt in. Status: not started. The
first step is a discovery-only prototype.

## Community feeds

Publish a simple manifest format that anyone who runs a feed can use to list it:
volunteer fire departments, emergency-management offices, universities, transit
agencies and local governments. A listing gives the stream URL, coverage area,
agencies included, any broadcast delay, a schedule, a contact, a rights
statement and the permitted uses. Quill Radio indexes the feed, and the audio
still comes straight from the provider. Why: there is no open nationwide catalog
of scanner or public-safety feeds, so this is the only keyless way to get one.
Constraint: each feed is listed by the person who owns it and states its own
rights, so nothing is scraped. Status: not started.

## Reading-services submission directory

Reading services already ship: a bundled, hand-checked list refreshed from Radio
Browser, available in Browse and in Find Stations. What is missing is a way for
the services themselves to submit and correct their own listings: the stream,
the service area, program schedules, who is eligible, and how to listen by
telephone or smart speaker. Why: the project treats this as mission-critical,
and no unified directory of these services exists anywhere. Constraint: listings
come directly from the services and are checked before they are published, with
no API or agreement involved. Status: not started.

## Amateur-radio network lookup

Look up AllStarLink and EchoLink nodes, show whether a node is online, and hand
off to the official client with an Open in EchoLink command. Why: repeater and
linked-network information is useful to blind radio amateurs, and every current
tool for it is visual. Constraint: node status is public, but connecting and
listening need a licensed, authenticated user, so Quill Radio only looks nodes
up and hands off; it never connects. RepeaterBook data is left out, because
RepeaterBook needs an approved partnership. Status: not started.
