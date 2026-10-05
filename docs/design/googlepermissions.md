# Google and YouTube Permissions for QUILL

*Written 2026-10-03 for Jeff. This covers what QUILL can do with YouTube
today, what needs Google's approval, and how to get that approval, from the
first form to the day the switch goes on for everyone. The section "For
listeners" is written to hand to people as it is.*

## The short version

- **Most of the YouTube features in Quill Radio need no approval from anyone.**
  They include playing, searching, comments, live chat, channels, notifications,
  sponsor skipping and the browser sign-in. They work the moment 3.2.0 ships.
- **One group of features needs Google's approval:** anything that goes
  through **Connect YouTube Account**, the official Google sign-in. That covers
  replying to comments, sending live chat messages, subscribing for real, liking
  and building playlists, and keeping your subscription list in sync live.
- **Getting that approval is a review, not a code change.** QUILL's Google sign-in
  has to pass Google's *OAuth app verification*. Both YouTube permissions QUILL
  asks for are what Google calls "sensitive". That means a review with a demo
  video and a privacy policy, but **not** the paid third-party security audit
  that only "restricted" permissions such as full Gmail or Drive access need.
- **The daily posting limit is a separate request.** QUILL starts with YouTube's
  standard daily allowance, shared by everyone who uses QUILL. Raising it means
  a second form and a check against YouTube's developer policies.
- **Until approval, nothing breaks.** Connect YouTube Account stays switched off
  in public builds. In a developer build it works for up to 100 test accounts
  you add yourself.

Google changes its forms and wording from time to time. The steps below match
how things work in late 2026. Check the links in "Where to read Google's own
rules" before you submit.

---

## For listeners: what Quill Radio does while we wait for Google

This section is written to be given to people as it is: copied into the Radio
guide, the release notes, the site or a reply to an email. It answers one
question: what can I do today, and what do I need for it?

There are three levels. Most people never go past the first.

### Level 1: no account, no sign-in, nothing to set up

Install Quill Radio and all of this works straight away. You don't need a Google
account, a YouTube account or a key of any kind, and Quill Radio never asks who
you are.

**Radio and podcasts**
- Every station Quill Radio can find, and your favourites, recordings and
  reminders.
- Finding podcasts and their categories, and following, playing and downloading
  episodes. The Podcast Index key that helps with this is built into Quill
  Radio, so there's nothing for you to sign up for.

**Playing YouTube**
- Any YouTube link you paste or open: a video, a live stream, a playlist or a
  channel.
- Chapters, speed, Where Am I, and captions read along as a transcript you can
  search.
- The YouTube Video window: whether something is live, finished or starting soon,
  its description, and the times listed in it, which you can jump to.
- Remind Me When It Goes Live, for premieres and upcoming streams.
- Save Audio, through Quill Radio's downloads.
- Skip Sponsor Segments, if you turn it on.

**Finding things on YouTube**
- Search YouTube for videos, playlists and channels (Ctrl+Shift+6).
- Search YouTube with Filters: type, upload date, length and sort order, plus
  YouTube Music songs (Ctrl+Alt+Shift+0).
- Any channel's Uploads, Shorts, Live and Playlists, and About This Channel.

**Reading what people say**
- Read Comments on any public video (Ctrl+Shift+7).
- Live Chat on any public live stream (Ctrl+Alt+Shift+7), and the chat of a
  finished stream played back in step with the video. Speaking new messages,
  pausing and filtering all work.

**Keeping up with channels**
- Follow a channel in Quill Radio, and Notify Me About New Videos.
- Bring in your YouTube subscriptions from a Google Takeout file, if you want
  them all at once.
- Subscribe on YouTube...: Quill Radio opens YouTube's own "Subscribe?" page in
  your browser, and you confirm it there, signed in as you normally are.

### Level 2: optional, using the YouTube sign-in already in your web browser

If you're signed in to YouTube in Edge, Chrome, Firefox, Brave, Opera or
Vivaldi, you can let Quill Radio use that sign-in. Turn on **Use my YouTube
sign-in from my web browser** in Preferences. This needs no approval from
Google, because it's simply your own browser's sign-in, read on your own
computer.

It adds:
- My YouTube: Home, Subscriptions, Watch Later, Liked Videos, Your Playlists and
  History.
- Videos only your account can watch: members-only videos, and age-restricted
  videos once your account has confirmed your age.

Good to know:
- Quill Radio never sees or stores your password. It keeps only which browser
  you chose, or the path of a cookies.txt file, and it scrubs sign-in data from
  its logs and problem reports.
- Some newer versions of Chrome and Edge lock their sign-in away from other
  programs. If yours does, Quill Radio says so and suggests Firefox or a
  cookies.txt file instead.
- Reading a members-only live chat works only with a cookies.txt file.
- This level can read, not post. It can't reply, send chat, subscribe or like.

### Level 3: waiting for Google, Connect YouTube Account

These features are built and tested, and they need Google to approve QUILL
before everyone can use them:
- Replying to comments, adding your own, and deleting your own.
- Sending messages in a live chat.
- Subscribing and unsubscribing directly, without the browser page.
- Like, Dislike, Add to Playlist and New Playlist.
- Keeping your subscription list in sync with YouTube automatically.

Until approval, **Connect YouTube Account** doesn't appear in Quill Radio. In
the meantime:
- To subscribe, use Subscribe on YouTube..., which works today.
- To reply, send a chat message or like a video, open the video on YouTube in
  your browser. Copy Stream Link on the video's row menu puts its address on the
  clipboard.

When Google says yes, an update switches these on, and the release notes will
say so.

*Internal note (not listener text):* until Google approves, all of the above
is hidden in Quill Radio, not merely disabled. `future.youtube_oauth` is
`released=False`, so a public build has no Connect/Disconnect rows on the
Station menu, no Reply / Add a Comment / Delete My Comment buttons in YouTube
Comments, no send box in Live Chat, no Like, Dislike, Remove Rating, Add to
Playlist, New Playlist or Add a Comment in the YouTube Video window, and
Subscribe on YouTube... always opens the confirm page -- even when a Google
client is baked into the build. The listener documents say nothing about any
of it; the removed passages are kept in "Ready to restore after approval",
below.

### Questions people ask

**Do I need a Google account to use Quill Radio?**
No. Everything in Level 1 works without one.

**Does Quill Radio ever see my Google password?**
No. The browser sign-in is read from your browser on your own computer. Connect
YouTube Account, when it arrives, signs you in on Google's own page in your
browser, and Quill Radio is handed a permission it keeps in Windows' secure
credential store. You can take that permission back at any time from your Google
account.

**Why can I read comments but not reply?**
Reading uses YouTube's public pages, the same as anyone visiting them. Posting
on your behalf needs Google's official permission, and Google reviews any app
that asks for it. QUILL's review is under way.

**Is anything sent to QUILL's own servers?**
No. QUILL has none. Quill Radio talks to YouTube directly, and to SponsorBlock
only if you turn sponsor skipping on.

**Will there be a limit on posting?**
Yes. YouTube gives each app a daily allowance shared by all of its users. If
it runs out, Quill Radio tells you once and you can try again the next day.

---

## What works without Google approval (the detail)

Everything in this section works without your Google account and without anyone
at Google signing off. It runs through yt-dlp, the chat reader (chat-downloader)
and YouTube's public pages, the same way a web browser reads them.

### Listening and watching

- Playing any YouTube link: videos, live streams, playlists and channels.
- The YouTube Video window: whether a video is live, finished or about to start,
  its description, the times listed in the description (press Enter to jump),
  Remind Me When It Goes Live, and Save Audio.
- Chapters, speed, Where Am I and captions read along as a transcript, with
  search and jump.
- Skip Sponsor Segments, which uses the community SponsorBlock list. It sends
  only a short code made from the video's address, never your identity.

### Finding things

- Search YouTube (Ctrl+Shift+6) for videos, playlists and channels.
- Search YouTube with Filters (Ctrl+Alt+Shift+0): type, upload date, length and
  sort order, plus YouTube Music songs.
- A channel's Uploads, Shorts, Live and Playlists, and About This Channel.

### Reading what people say

- Read Comments (Ctrl+Shift+7), with search, Top or Newest, Load More and Copy.
- Live Chat (Ctrl+Alt+Shift+7): reading a live chat, or the chat of a finished
  stream in step with the video. Speaking new messages, pausing and filtering
  are all included.

### Your channels, kept in Quill Radio

- Follow This Channel in Quill Radio, and Stop Following.
- Notify Me About New Videos, per channel.
- Importing your subscriptions from a Google Takeout file.
- **Subscribe on YouTube...** without the official sign-in: Quill Radio opens
  YouTube's own "Subscribe?" page in your browser, and you confirm it there.
  This works today for everyone.

### Your own YouTube, through your browser (no Google approval)

With **Use my YouTube sign-in from my web browser** turned on in Preferences,
Quill Radio reads your browser's YouTube sign-in each time it asks YouTube for
something. This is your own browser session on your own computer, used the way
yt-dlp always has. Google does not review it, because QUILL never asks Google
for a permission. It gives you:
- My YouTube: Home, Subscriptions, Watch Later, Liked Videos, Your Playlists
  and History.
- Members-only and age-restricted videos that your account can already watch.

What the browser sign-in **cannot** do is post anything: no comments, no chat
messages, no subscribing, no likes. Those go through Google's official sign-in,
below.

---

## What needs Google approval

These all go through **Station > Connect YouTube Account...** (the official
Google sign-in, using the QUILL app's Google client). They work today in a
developer build for test accounts. Everyone else gets them once Google has
verified the app.

| Feature | Permission it needs |
| --- | --- |
| Keep your subscriptions and playlists in sync live | Read only |
| Reply to a comment, add a comment, delete your own | Post on your behalf |
| Send messages in a live chat | Post on your behalf |
| Subscribe and Unsubscribe directly | Post on your behalf |
| Like, Dislike, Remove Rating | Post on your behalf |
| Add to Playlist and New Playlist | Post on your behalf |

Quill Radio asks for "post on your behalf" only the first time someone uses one
of those features. Someone who only ever reads never sees that request.

### The two permissions, in Google's terms

| What QUILL calls it | Google's scope | Google's class |
| --- | --- | --- |
| Read only | `https://www.googleapis.com/auth/youtube.readonly` | Sensitive |
| Post on your behalf | `https://www.googleapis.com/auth/youtube.force-ssl` | Sensitive |

Both are sensitive, not restricted. So the review needs a privacy policy,
a demo video and a written reason for each permission. It does **not** need the
CASA security assessment.

### What happens before approval

- **Testing mode** (where the app is now): only Google accounts you add as test
  users in the Google Cloud console can sign in, up to 100. Their sign-in
  expires after 7 days, so they connect again each week.
- **Published but not verified:** anyone can sign in, but Google shows a
  "Google hasn't verified this app" warning, and people must choose Advanced
  and continue. Google also caps how many new people an unverified app can sign
  in. **Do not ship to the public like this.** The warning frightens people,
  and a screen reader user may not find the way past it.
- **Verified:** a normal consent screen naming QUILL, with no warning and no
  user cap.

---

## Before you submit: a checklist

Google reviewers try the app and read the policy. These need to be true first.
Each item names who does it.

1. **Verify the domain** (you). Add quillforall.org to Google Search Console as
   a Domain property and add the DNS TXT record it gives you. The consent screen's
   home page, privacy policy and terms links must all be on a verified domain.
2. **Privacy policy covers YouTube** (done 2026-10-03). `docs/legal/PRIVACY.md`
   now has a "YouTube in Quill Radio" section and a row for the new-video check.
   Make sure the published page on quillforall.org shows it.
3. **Disconnect also revokes** (done 2026-10-03). **Disconnect YouTube
   Account...** now revokes QUILL's access at Google
   (`https://oauth2.googleapis.com/revoke`) and then forgets the sign-in on this
   computer. If Google can't be reached, the sign-in is still forgotten, and
   Quill Radio says to finish at `https://myaccount.google.com/permissions`.
4. **Say where to revoke** (us; docs and the consent text). The Radio guide and
   the privacy policy should tell people they can remove QUILL's access at any
   time at `https://myaccount.google.com/permissions`.
5. **YouTube attribution** (us; docs). YouTube's developer policies ask an app to
   say it uses YouTube API Services, and to link the YouTube Terms of Service
   and the Google Privacy Policy. Put this in the privacy policy and in Radio's
   About or the YouTube chapter.
6. **Fix one old description** (us; code). The Customize Features entry for
   Connect YouTube Account still says it is read-only. It now also covers
   posting, when asked for.
7. **Logo** (you or us). A square PNG of QUILL's icon, 120 by 120 pixels. If you
   add a logo, Google reviews the brand, which can add a few days. You can
   submit without one.
8. **Support email** (you). support@community-access.org, on a Google account
   you control, as the app's user support address.
9. **One Google Cloud project** (you). The same project holds the OAuth client
   that `tools/generate_youtube_oauth_client.py` bakes into builds. Note its
   project number; Google asks for it.

---

## Submitting for verification, step by step

In the Google Cloud console, open the QUILL project, then **Google Auth
Platform** (older screens call it the OAuth consent screen).

1. **APIs:** make sure **YouTube Data API v3** is enabled for the project.
2. **Clients:** the OAuth client is the **Desktop app** type. QUILL signs in
   through your browser and comes back to `http://127.0.0.1:8912/callback` on
   your own computer. Desktop clients accept that without registering it.
3. **Branding:**
   - App name: **QUILL**. Keep it exactly the same everywhere; a mismatch is a
     common reason for rejection.
   - User support email: support@community-access.org.
   - App logo: optional (see the checklist).
   - Application home page: `https://www.quillforall.org/`
   - Privacy policy: the published privacy page on quillforall.org.
   - Terms of service: the published terms page, if there is one.
   - Authorized domains: `quillforall.org`.
   - Developer contact email: an address you read.
4. **Audience:** choose **External**. While testing, add test users here. When
   you're ready, press **Publish app** to move from Testing to In production.
   Verification starts from there.
5. **Data Access:** add the two scopes, `youtube.readonly` and
   `youtube.force-ssl`. For each, paste the justification from "What to tell
   Google about each permission" below.
6. **Verification Center:** submit. Google asks for:
   - the demo video link (see "The demo video");
   - how each scope is used, which is the same justification text;
   - confirmation that you follow Google's API Services User Data Policy,
     including the Limited Use rules.
7. **Answer Google's emails.** A reviewer writes from Google's Trust and Safety
   team, usually within a few days. Reply in that same email thread. Common
   requests are a clearer video, a privacy policy wording change, or proof of
   the domain.
8. **Timing:** brand checks often take two or three working days. A review
   with sensitive scopes takes longer, typically one to a few weeks, depending on
   how many rounds of questions there are.

### What to tell Google about each permission

Paste these, adjusted if anything changes.

**youtube.readonly**

> QUILL is a free, screen-reader-first audio app for blind and low-vision
> people. With this permission, Quill Radio lists the channels and playlists the
> signed-in person follows, so they can listen to them without typing each
> address. It is only used when the person chooses Connect YouTube Account.
> Nothing is sent to any server of ours. The list is kept on the person's own
> computer, and they can disconnect at any time.

**youtube.force-ssl**

> Used only when the person asks QUILL to act on YouTube for them: posting a
> comment or reply they have written, deleting their own comment, sending a
> live chat message they have typed, subscribing or unsubscribing from a
> channel, rating a video, or adding a video to one of their playlists. Each
> action happens only when the person presses a button for it, and QUILL tells
> them the result. QUILL asks for this permission only the first time the
> person uses one of these features. QUILL is designed for screen reader users,
> and this lets them take part on YouTube through an accessible interface
> instead of a web page that is hard to use with a screen reader. No data is
> sent to our servers; QUILL has none.

### The demo video

Upload it to YouTube as **Unlisted**. Keep it short, three to five minutes, and
plain. A screen recording with narration is ideal. Show:

1. QUILL running, with the app's name visible.
2. Station > Connect YouTube Account..., then the Google consent screen. **Slow
   down here:** the reviewer must see the app name and, in the browser's address
   bar, the `client_id` that matches the project you are submitting.
3. Coming back to Quill Radio, and the subscriptions and playlists appearing
   (that's the read-only scope in use).
4. The first posting action, for example Reply in the Comments window. Show
   QUILL's own explanation, then Google's second consent screen for posting.
5. Each posting feature once: a reply posted, a comment deleted, a live chat
   message sent, Subscribe, Like, Add to Playlist.
6. Station > Disconnect YouTube Account..., and then the QUILL entry gone from
   `https://myaccount.google.com/permissions`, which shows that revoking works.

Narration tip: say what each step does in a sentence, the same way the user
guide does. Reviewers are people too.

### The privacy policy text

This is now in `docs/legal/PRIVACY.md`, as "YouTube in Quill Radio", in a
slightly longer form that also covers the browser sign-in and SponsorBlock.
The core of it, for the Google form:

> **YouTube.** Quill Radio uses YouTube API Services. By using its YouTube
> features you agree to the YouTube Terms of Service
> (https://www.youtube.com/t/terms), and the Google Privacy Policy
> (https://policies.google.com/privacy) applies to what Google does with your
> data.
>
> If you choose Connect YouTube Account, QUILL asks Google for permission to
> read the channels and playlists you follow, and, only if you then use a
> feature that needs it, to post comments, replies and live chat messages you
> write, subscribe or unsubscribe, rate videos, and add videos to your
> playlists. QUILL does these things only when you ask. Your sign-in is stored
> in your computer's own secure credential store, never in our files and never
> on any server; QUILL has no servers that receive your data. Lists QUILL reads
> from YouTube stay on your computer. You can disconnect at any time with
> Station > Disconnect YouTube Account..., which also removes QUILL's access
> at Google, or remove QUILL's access from your Google account at
> https://myaccount.google.com/permissions.
>
> QUILL's use of information received from Google APIs adheres to the Google
> API Services User Data Policy, including the Limited Use requirements.

---

## The daily limit, and asking for more

Every app using the YouTube Data API starts with **10,000 quota units a day**,
shared by everyone who uses that app. Reading is cheap; posting is not:

| Action | Approximate cost |
| --- | --- |
| Listing subscriptions or playlists, a page | 1 |
| Posting a comment or reply | 50 |
| Sending a live chat message | about 50 |
| Subscribing, rating, adding to a playlist | 50 |

So posting tops out at roughly **200 actions a day for all QUILL users
together**. When the limit is reached, Quill Radio says "YouTube's daily limit
for QUILL has been reached; try again tomorrow." once, and does not retry.

To raise it:

1. Get the app verified first. It's the same project, and reviewers like to see it.
2. Fill in **YouTube API Services: Audit and Quota Extension Form**.
3. Describe QUILL, its users, how many people you expect, and what each action
   is for. The permission justifications above work here too.
4. YouTube checks QUILL against the YouTube API Services Terms and Developer
   Policies. The usual points are attribution, not storing YouTube data longer
   than needed, honouring deletion and revocation, and not changing how YouTube
   content is shown in misleading ways. Have the privacy policy and the demo
   video ready; they may ask for a walkthrough.
5. Expect a few weeks. Ask for a modest number with a clear reason, for example
   "accessibility users posting comments and live chat; expected N daily active
   users". That goes better than asking for a large round number.

---

## After approval: switching it on

1. **Build with the client.** Release builds bake the Google client in from the
   environment: set `QUILL_YOUTUBE_OAUTH_CLIENT_ID` and
   `QUILL_YOUTUBE_OAUTH_CLIENT_SECRET` (or the `_FILE` variants) before the
   runtime build runs `tools/generate_youtube_oauth_client.py`. A desktop
   client's secret is not truly secret, and Google knows that; it identifies
   the app, not a person.
2. **Turn the feature on for everyone.** Mark the `future.youtube_oauth` feature
   as released in `quill/core/feature_catalog.py` / `quill/core/features.py`,
   so Connect YouTube Account shows in public builds.
3. **Tell people.** A release-notes paragraph, the Radio guide's YouTube chapter
   (restored in step 4, without its "Google has to review an app" paragraph),
   and the site.
4. **Restore the passages in "Ready to restore after approval"**, below:
   the user guide, release notes, both Radio changelogs, the root changelog
   and the reworded code strings, verbatim, then render and sync the docs.
5. **Watch the quota** for the first weeks in the Google Cloud console's API
   dashboard, and apply for an extension early if posting is popular.

---

## Where to read Google's own rules

Check these before you submit; Google updates them.

- OAuth app verification help:
  https://support.google.com/cloud/answer/13463073
- Sensitive and restricted scopes:
  https://developers.google.com/identity/protocols/oauth2/production-readiness/sensitive-scope-verification
- Google API Services User Data Policy:
  https://developers.google.com/terms/api-services-user-data-policy
- YouTube API Services Terms of Service:
  https://developers.google.com/youtube/terms/api-services-terms-of-service
- YouTube API Services Developer Policies:
  https://developers.google.com/youtube/terms/developer-policies
- YouTube quota and compliance audits:
  https://developers.google.com/youtube/v3/guides/quota_and_compliance_audits

---

## Other services in the family, for comparison

- **Podcast Index:** no review. A free key from https://api.podcastindex.org/signup,
  baked into builds by `tools/generate_podcast_index_key.py`, and release builds
  now refuse to ship without it.
- **ChatGPT sign-in and your own AI keys** (OpenAI, Google Gemini): each person
  signs in or pastes their own key. QUILL needs no approval of its own.
- **YouTube without Connect YouTube Account:** none needed, as described in
  "What works without Google approval".

---

## Ready to restore after approval

Everything below was taken out of the listener-facing documents on
2026-10-03, so that nobody reads about Connect YouTube Account, the write
actions or the daily-limit message before Google approves them. Each
passage is verbatim. Where a passage was rewritten rather than removed,
"Reads now" is the text to find and "Restore to" is what replaces it.
After restoring, render each changed `.md` (html and epub), run
`python scripts/sync_site_docs.py` and `python scripts/check_docs_artifacts.py`,
and add a release-notes paragraph for the release that turns it on.

### `standalone/radio/docs/userguide.md`

#### Chapter 10 > Channels > Follow a channel, or subscribe on YouTube

Reads now:

````markdown
   YouTube.

Quill Radio never subscribes for you; YouTube always asks you to
confirm.
````

Restore to:

````markdown
   YouTube.

If you have connected your YouTube account (see **Doing things on YouTube
with your account**, below), **Subscribe on YouTube...** subscribes you
straight away instead, and you hear "Subscribed to Rick Steves' Europe." If you
already subscribe, it asks whether to unsubscribe, with **No** already chosen
so a quick Enter changes nothing.

Without a connected account, Quill Radio never subscribes for you; YouTube
always asks you to confirm.
````

#### Chapter 10 > Watching and reading along > The YouTube Video window, step by step

Reads now:

````markdown
7. Press **Escape** to close the window.
````

Restore to:

````markdown
7. The rest of the buttons act on your YouTube account; see **Doing things on
   YouTube with your account**, below.
8. Press **Escape** to close the window.
````

#### Chapter 10 > Live chat > Using Live Chat with a screen reader (Keys in the Live Chat window table)

Reads now:

````markdown
| Move between the list, Full text and the filter | F6 / Shift+F6 |
````

Restore to:

````markdown
| Move between the list, Full text, the filter and the send box | F6 / Shift+F6 |
| Send what you typed | Enter (in the send box) |
````

#### Chapter 10 > Doing things on YouTube with your account (whole section)

Put this whole section back immediately before the heading `### Repair YouTube Support`. Before publishing, drop or reword its second paragraph ("Connect YouTube Account is new, and Google has to review an app..."), which describes the pre-approval state.

````markdown
### Doing things on YouTube with your account

Everything so far only reads from YouTube. Quill Radio can also do things on
YouTube as you: reply to comments, write your own, send messages in a live
chat, subscribe and unsubscribe, like or dislike a video, and add videos to
your playlists. For this it uses Google's own sign-in, **Connect YouTube
Account** on the Station menu, rather than your browser.

Connect YouTube Account is new, and Google has to review an app before
everyone can use it. Until that review is finished, you only see it in copies
of Quill Radio where it has been switched on, and Google may show a warning
that the app is not verified, or not let you sign in at all. Where it is not
available, the buttons below are not shown, and **Subscribe on YouTube...**
keeps opening YouTube's own page in your browser.

#### The permission Quill Radio asks for

Connecting your account first lets Quill Radio read your subscriptions and
playlists, nothing more. The first time you use one of the actions below,
Quill Radio stops and explains, in plain words, that it needs one more
permission: to act on YouTube for you. If you choose **OK**, your browser opens
on Google's page to approve it.

Google describes that permission as "See, edit, and permanently delete your
YouTube videos, ratings, comments and captions", because that is the only
name it has for it. Quill Radio uses it only for the actions listed here, and
only when you press the button for one. It never does anything on its own, and
it never sees your password. If you choose **Cancel**, nothing changes, and you
hear "Nothing was changed on YouTube." You can take the permission back any
time with **Station > Disconnect YouTube Account...**, which also removes
Quill Radio's access at Google. Your sign-in is kept in
Windows' own secure store, never in a settings file.

#### YouTube's daily limit

Google gives each app a fixed number of requests a day, shared by everybody
who uses it. If Quill Radio runs out, you hear "YouTube's daily limit for
QUILL has been reached; try again tomorrow." Nothing is retried behind your
back; just try again the next day. Reading, playing and searching are not
affected.

#### Reply to a comment, or write your own, step by step

1. Open a video's comments (Ctrl+Shift+7, or **Read Comments...** on its row).
2. To answer someone, select their comment and press **Alt+R** for
   **Reply...**. To write a new comment on the video, press **Alt+A** for
   **Add a Comment...**.
3. Type what you want to say and choose **OK**.
4. You hear "Reply posted." or "Comment posted.", and it appears in the list,
   under the comment it answers.

To remove one of your own comments, select it and press **Alt+D** for **Delete
My Comment**. Quill Radio checks with YouTube that it is yours, asks you to
confirm, and you hear "Comment deleted." Anybody else's comment cannot be
deleted, and you are told so.

You can also add a comment from the **YouTube Video** window with **Add a
Comment...** (Alt+C).

#### Send a message in a live chat, step by step

1. Open the live chat (Ctrl+Alt+Shift+7). With your account connected, the
   window has a **Send a message** box (Alt+S).
2. Type your message and press **Enter**. YouTube's chat takes one line of up
   to 200 characters.
3. You hear "Message sent." The box empties and keeps focus, ready for the
   next one. If sending fails, you hear why and what you typed stays in the
   box, so nothing is lost.

You can only send to a chat that is live right now. A replay is read-only.

#### Like a video, or add it to a playlist, step by step

1. Open the **YouTube Video** window (Ctrl+Alt+Shift+8).
2. Choose one of these:
   - **Like** (Alt+L), **Dislike** (Alt+I) or **Remove Rating** (Alt+R). You
     hear "Liked.", "Disliked." or "Rating removed." YouTube counts a dislike
     but no longer shows the number to anyone.
   - **Add to Playlist...** (Alt+P): pick one of your playlists from the list
     and choose **OK**. You hear, for example, "Added to Walks."
   - **New Playlist...** (Alt+N): type a name, choose who can see it (private,
     unlisted or public), and choose **OK**. The video goes into the new
     playlist.

YouTube does not let any app add to **Watch Later**, so that one has to be
done on YouTube itself.

#### Subscribe and unsubscribe

With your account connected, **Subscribe on YouTube...** on a channel's menu
(Shift+F10, then Y) subscribes you straight away. If you already subscribe, it
asks whether to unsubscribe, with **No** already chosen.
````

#### Chapter 10 > What you learned, and where to go next

Reads now:

````markdown
search with YouTube's own filters or YouTube Music, and, if you like, use your
own YouTube sign-in.
````

Restore to:

````markdown
search with YouTube's own filters or YouTube Music, and, if you like, use your
own YouTube sign-in and act on YouTube with your account.
````

### `standalone/radio/docs/release-notes-3.2.md`

#### YouTube (the list of what is new)

Reads now:

````markdown
- **Shorts** and **About This Channel** on every channel.
````

Restore to:

````markdown
- **Shorts** and **About This Channel** on every channel.
- **Doing things on YouTube with your account**: reply and comment, chat,
  subscribe, like, and add to playlists, where Connect YouTube Account is
  available.
````

#### Doing things on YouTube with your account (whole section)

Put this whole section back immediately before the heading `## Keeping up with podcasts`.

````markdown
### Doing things on YouTube with your account

Where **Connect YouTube Account** is available, Quill Radio can now act on
YouTube as you: **Reply...**, **Add a Comment...** and **Delete My Comment**
in the comments window; a **Send a message** box in Live Chat; **Subscribe on
YouTube...** that subscribes and unsubscribes for real; and **Like**,
**Dislike**, **Remove Rating**, **Add to Playlist...** and **New Playlist...**
in the YouTube Video window. Each says what happened once, such as "Reply
posted." or "Subscribed to Rick Steves' Europe."

The first time you use one, Quill Radio explains in plain words that it needs
one more permission from Google, to act on YouTube for you, and only then opens
your browser to ask. Google names that permission broadly; Quill Radio uses it
only for these buttons, and only when you press one.

Two honest caveats. Google has to review an app before everyone can sign in to
it, so until that is done Connect YouTube Account only appears in some copies
of Quill Radio, and Google may warn that the app is not verified. And Google
allows each app a fixed number of requests a day, shared by everyone; if that
runs out you hear "YouTube's daily limit for QUILL has been reached; try again
tomorrow." YouTube does not let any app add to Watch Later.
````

### `standalone/radio/docs/CHANGELOG.md`

#### Quill Radio 3.2.0 entry: YouTube: Live Chat, ... (bullet title)

Reads now:

````markdown
sponsor skipping and filtered search.**
````

Restore to:

````markdown
sponsor skipping, filtered search and account actions.**
````

#### Quill Radio 3.2.0 entry: YouTube: Live Chat, ... (end of bullet)

Reads now:

````markdown
 Channels gain Shorts and About This Channel...; My YouTube gains History.
````

Restore to:

````markdown
 Channels gain Shorts and About This Channel...; My YouTube gains History. Where Connect YouTube Account is available, Reply, Add a Comment, Delete My Comment, sending in Live Chat, real Subscribe/Unsubscribe, Like/Dislike/Remove Rating, Add to Playlist and New Playlist act as your account, asking Google for the extra permission (youtube.force-ssl) in plain words the first time; a spent daily quota is one sentence and is never retried.
````

### `standalone/radio/CHANGELOG.md`

The same two edits as `standalone/radio/docs/CHANGELOG.md`; keep the
two changelogs' entries identical.

#### Quill Radio 3.2.0 entry: YouTube: Live Chat, ... (bullet title)

Reads now:

````markdown
sponsor skipping and filtered search.**
````

Restore to:

````markdown
sponsor skipping, filtered search and account actions.**
````

#### Quill Radio 3.2.0 entry: YouTube: Live Chat, ... (end of bullet)

Reads now:

````markdown
 Channels gain Shorts and About This Channel...; My YouTube gains History.
````

Restore to:

````markdown
 Channels gain Shorts and About This Channel...; My YouTube gains History. Where Connect YouTube Account is available, Reply, Add a Comment, Delete My Comment, sending in Live Chat, real Subscribe/Unsubscribe, Like/Dislike/Remove Rating, Add to Playlist and New Playlist act as your account, asking Google for the extra permission (youtube.force-ssl) in plain words the first time; a spent daily quota is one sentence and is never retried.
````

### `CHANGELOG.md`

#### 1.0.0 > Quill Radio: YouTube live chat, ... (heading)

Reads now:

````markdown
### Quill Radio: YouTube live chat, sponsor skipping and filtered search (2026-10-03)
````

Restore to:

````markdown
### Quill Radio: YouTube live chat, account actions, sponsor skipping and filtered search (2026-10-03)
````

#### 1.0.0 > Quill Radio: YouTube live chat, ... (account actions bullet)

Put this bullet back between the **Live Chat** bullet and the **YouTube Video window** bullet.

````markdown
- **Account actions through the official sign-in**, incremental:
  `youtube_write_scope.py` asks for `youtube.force-ssl` (with
  `include_granted_scopes`) only on the first write, after a plain-language
  consent; `youtube_account_api.py` is the single Data API write site
  (comments, live chat send, subscriptions, ratings, playlists), turning a 403
  quotaExceeded into one sentence and never retrying. Wired into the Comments
  window (Reply / Add a Comment / Delete My Comment), the Live Chat send box,
  Subscribe on YouTube (real subscribe/unsubscribe, the confirm page as the
  fallback) and the new YouTube Video window.
````

### Code strings that were reworded

These are not documents, but they are what a listener hears or reads, so
they were reworded at the same time. Restore them in the same change.

#### `quill/core/radio/surface_help.py` (F1 window purposes)

`"YouTube Comments"`, restore the last sentence:

````markdown
"you back where you were. With a YouTube account connected, Alt+R "
"Reply, Alt+A Add a Comment and Alt+D Delete My Comment post as you."
````

`"YouTube Live Chat"`, restore the send box to the F6 list:

````markdown
"pause, Ctrl+S speak new messages on or off, F6 between the list, Full "
"text, the filter and the send box. Escape closes it."
````

`"YouTube Video"`, restore the account actions:

````markdown
"description lists (Enter jumps there while it plays), and Like, Add "
"to Playlist, Add a Comment and the rest, which act as your connected "
"YouTube account. Escape closes it."
````

#### `quill/ui/radio/palette_commands.py` (Command Palette title)

`radio.youtube_video` reads `Internet Radio: YouTube Video Details...`;
restore `Internet Radio: YouTube Video Details and Account Actions...`.

#### `quill/tools/build_help_reference.py` (published F1 reference)

Empty `HELD_BACK`, so the Comments window's Reply / Add a Comment / Delete
My Comment help and the Live Chat send box help are published again, then
run `python -m quill.tools.build_help_reference --write` and
`python -m quill.tools.build_keymap_reference --write`.

#### Tests that pin the hiding

`tests/unit/ui/radio/test_radio_youtube_held_back.py` asserts every surface
is absent while `future.youtube_oauth` is locked. Once the flag is released
it is no longer locked in a public build: rewrite that file's
`locked_app` fixture (or retire the file) in the same change.
