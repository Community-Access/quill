#!/usr/bin/env bash
# Install and seed the QUILL WordPress regression-test site.
# Safe to re-run: every step checks before it creates.
set -euo pipefail
cd "$(dirname "$0")"
set -a; . ./.env; set +a

URL="https://lp.csedesigns.com/wordpress"
wp() {
  docker run --rm -i --user 33:33 \
    --volumes-from wordpress-test --network wordpress-test_internal \
    -w /var/www/html/wordpress \
    -e WORDPRESS_DB_HOST=db -e WORDPRESS_DB_NAME=wordpress \
    -e WORDPRESS_DB_USER=wordpress -e "WORDPRESS_DB_PASSWORD=$DB_PASSWORD" \
    -e HTTP_X_FORWARDED_PROTO=https \
    wordpress:cli wp "$@"
}

# --- core -----------------------------------------------------------------
if ! wp core is-installed 2>/dev/null; then
  wp core install --url="$URL" --title="QUILL WordPress Test Site" \
    --admin_user=quilladmin --admin_password="$ADMIN_PASSWORD" \
    --admin_email=wordpress-test@csedesigns.com --skip-email
fi
wp option update blogdescription "Regression testing for QUILL and QUILL Lite"
wp option update timezone_string "America/Los_Angeles"
wp option update default_comment_status open
wp option update comment_moderation 1
wp option update blog_public 0   # discourage search engines: a test site

# Pretty links, with the rewrite base for /wordpress/.
wp rewrite structure '/%postname%/'
docker exec -i -u 33 wordpress-test sh -c 'cat > /var/www/html/wordpress/.htaccess' <<'HT'
# BEGIN WordPress
<IfModule mod_rewrite.c>
RewriteEngine On
RewriteRule .* - [E=HTTP_AUTHORIZATION:%{HTTP:Authorization}]
RewriteBase /wordpress/
RewriteRule ^index\.php$ - [L]
RewriteCond %{REQUEST_FILENAME} !-f
RewriteCond %{REQUEST_FILENAME} !-d
RewriteRule . /wordpress/index.php [L]
</IfModule>
# END WordPress
HT

# --- people: one account per role ------------------------------------------
ACCOUNTS=test-accounts.txt
umask 077
touch "$ACCOUNTS"
for role in editor author contributor subscriber; do
  user="quill-$role"
  if ! wp user get "$user" --field=ID >/dev/null 2>&1; then
    pw=$(openssl rand -base64 30 | tr -d '/+=' | cut -c1-24)
    wp user create "$user" "$user@csedesigns.com" --role="$role" --user_pass="$pw" \
      --display_name="QUILL $(echo "$role" | sed 's/./\U&/')" >/dev/null
    printf '%s sign-in password: %s\n' "$user" "$pw" >> "$ACCOUNTS"
  fi
done
for user in quilladmin quill-editor quill-author quill-contributor; do
  if ! grep -q "^$user application password" "$ACCOUNTS"; then
    ap=$(wp user application-password create "$user" "QUILL regression tests" --porcelain)
    printf '%s application password: %s\n' "$user" "$ap" >> "$ACCOUNTS"
  fi
done
chmod 600 "$ACCOUNTS"

# --- terms -----------------------------------------------------------------
for c in News Training "Product Updates" "Empty Category"; do
  wp term get category "$(echo "$c" | tr 'A-Z ' 'a-z-')" --by=slug >/dev/null 2>&1 || wp term create category "$c" >/dev/null
done
wp term get category training --by=slug >/dev/null 2>&1 && \
  { wp term get category "jaws-training" --by=slug >/dev/null 2>&1 || \
    wp term create category "JAWS Training" --parent="$(wp term get category training --by=slug --field=term_id)" >/dev/null; }
for t in JAWS Braille WordPress Accessibility "Unused Tag"; do
  wp term get post_tag "$(echo "$t" | tr 'A-Z ' 'a-z-')" --by=slug >/dev/null 2>&1 || wp term create post_tag "$t" >/dev/null
done

# --- media: pictures made on the server, no downloads -----------------------
mkdir -p seed
docker exec -u 33 wordpress-test php -r '
foreach ([["wide-banner",2400,800,[30,90,160]],["square-logo",512,512,[200,120,20]],["photo-volunteers",1600,1067,[40,140,90]],["decorative-divider",1200,40,[180,180,180]]] as [$n,$w,$h,$c]) {
  $im = imagecreatetruecolor($w,$h); imagefill($im,0,0,imagecolorallocate($im,...$c));
  imagestring($im,5,20,($h>60?20:10),"QUILL test: $n",imagecolorallocate($im,255,255,255));
  imagepng($im,"/tmp/$n.png");
}
$g = imagecreatetruecolor(400,200); imagefill($g,0,0,imagecolorallocate($g,250,250,250));
imagestring($g,5,40,90,"Text in a picture: Book now",imagecolorallocate($g,0,0,0)); imagegif($g,"/tmp/animated-ish.gif");'
for f in wide-banner.png square-logo.png photo-volunteers.png decorative-divider.png animated-ish.gif; do
  name="${f%.*}"
  if [ -z "$(wp post list --post_type=attachment --name="$name" --field=ID)" ]; then
    docker cp "wordpress-test:/tmp/$f" "seed/$f"
    docker cp "seed/$f" "wordpress-test:/var/www/html/wordpress/$f"
    alt=""
    case "$name" in
      photo-volunteers) alt="Volunteers sorting donations at the spring fair";;
      square-logo) alt="QUILL test site logo";;
    esac
    wp media import "/var/www/html/wordpress/$f" --title="$name" --alt="$alt" >/dev/null
    docker exec -u 33 wordpress-test rm -f "/var/www/html/wordpress/$f"
  fi
done
# --- media for listening (wordpress.md 6.1a): made on the server, no downloads
# A three-second 440 Hz tone (WAV, written by PHP in the WordPress container),
# a five-second silent test-pattern video (MP4, made by ffmpeg in a throwaway
# container, with a silent sound track so players treat it as playable), and
# English captions named the way Add Captions names them (clip.en.vtt).
docker exec -u 33 wordpress-test php -r '
$rate = 8000; $n = $rate * 3; $data = "";
for ($i = 0; $i < $n; $i++) { $data .= pack("v", (int) (8000 * sin(2 * M_PI * 440 * $i / $rate))); }
$head = "RIFF" . pack("V", 36 + strlen($data)) . "WAVEfmt " . pack("VvvVVvv", 16, 1, 1, $rate, $rate * 2, 2, 16) . "data" . pack("V", strlen($data));
file_put_contents("/tmp/quill-test-tone.wav", $head . $data);'
if [ -z "$(wp post list --post_type=attachment --name=quill-test-clip --field=ID)" ]; then
  docker run --rm -v "$(pwd)/seed:/out" jrottenberg/ffmpeg:6.1-alpine -loglevel error -y \
    -f lavfi -i "testsrc=size=640x360:rate=25:duration=5" \
    -f lavfi -i "anullsrc=channel_layout=mono:sample_rate=44100" \
    -shortest -c:v libx264 -pix_fmt yuv420p -c:a aac -b:a 32k /out/quill-test-clip.mp4
  printf 'WEBVTT\n\n00:00:00.500 --> 00:00:02.500\nThis is the QUILL test clip.\n\n00:00:02.500 --> 00:00:04.800\nCaptions read on request.\n' > seed/quill-test-clip.en.vtt
fi
for f in quill-test-tone.wav quill-test-clip.mp4 quill-test-clip.en.vtt; do
  name="${f%.*}"; name="${name//./-}"
  if [ -z "$(wp post list --post_type=attachment --name="$name" --field=ID)" ]; then
    [ -f "seed/$f" ] || docker cp "wordpress-test:/tmp/$f" "seed/$f"
    docker cp "seed/$f" "wordpress-test:/var/www/html/wordpress/$f"
    # The title is the name, so the slug checked above is the one WordPress makes.
    # A site that refuses .vtt uploads still gets the tone and the clip.
    wp media import "/var/www/html/wordpress/$f" --title="${f%.*}" >/dev/null || \
      echo "WordPress would not take $f; the captions test will say there are no captions."
    docker exec -u 33 wordpress-test rm -f "/var/www/html/wordpress/$f"
  fi
done
tone_url=$(wp post list --post_type=attachment --name=quill-test-tone --field=guid)
tone_id=$(wp post list --post_type=attachment --name=quill-test-tone --field=ID)
clip_url=$(wp post list --post_type=attachment --name=quill-test-clip --field=guid)
clip_id=$(wp post list --post_type=attachment --name=quill-test-clip --field=ID)

logo=$(wp post list --post_type=attachment --name=square-logo --field=ID)
wp option update site_logo "$logo"
wp option update site_icon "$logo"
photo_url=$(wp post list --post_type=attachment --name=photo-volunteers --field=guid)
photo_id=$(wp post list --post_type=attachment --name=photo-volunteers --field=ID)

# --- content ---------------------------------------------------------------
post() {  # slug type status title content [extra args...]
  local slug=$1 type=$2 status=$3 title=$4 content=$5; shift 5
  local id
  # Remembered in seed-ids.txt, not looked up by slug: WordPress gives drafts
  # and pending posts no slug, so a slug lookup would create them again.
  touch seed-ids.txt
  id=$(grep "^$slug=" seed-ids.txt | cut -d= -f2 || true)
  if [ -n "$id" ] && ! wp post get "$id" --field=ID </dev/null >/dev/null 2>&1; then
    id=""
  fi
  if [ -z "$id" ]; then
    id=$(printf '%s' "$content" | wp post create - --post_type="$type" --post_name="$slug" \
      --post_status="$status" --post_title="$title" --porcelain "$@")
    grep -v "^$slug=" seed-ids.txt > seed-ids.tmp || true
    echo "$slug=$id" >> seed-ids.tmp
    mv seed-ids.tmp seed-ids.txt
  fi
  echo "$id"
}

blocks=$(cat <<BLOCKS
<!-- wp:paragraph -->
<p>This page has one of every block QUILL needs to round-trip exactly.</p>
<!-- /wp:paragraph -->

<!-- wp:heading -->
<h2 class="wp-block-heading">Buttons and columns</h2>
<!-- /wp:heading -->

<!-- wp:buttons -->
<div class="wp-block-buttons"><!-- wp:button -->
<div class="wp-block-button"><a class="wp-block-button__link wp-element-button" href="https://example.org/book">Book a session</a></div>
<!-- /wp:button --></div>
<!-- /wp:buttons -->

<!-- wp:columns -->
<div class="wp-block-columns"><!-- wp:column -->
<div class="wp-block-column"><!-- wp:paragraph -->
<p>Morning sessions run from nine.</p>
<!-- /wp:paragraph --></div>
<!-- /wp:column -->

<!-- wp:column -->
<div class="wp-block-column"><!-- wp:paragraph -->
<p>Evening sessions run from six.</p>
<!-- /wp:paragraph --></div>
<!-- /wp:column --></div>
<!-- /wp:columns -->

<!-- wp:details -->
<details class="wp-block-details"><summary>What does it cost?</summary><!-- wp:paragraph {"placeholder":"Type / to add a hidden block"} -->
<p>The first session is free.</p>
<!-- /wp:paragraph --></details>
<!-- /wp:details -->

<!-- wp:image {"id":$photo_id,"sizeSlug":"large","linkDestination":"none"} -->
<figure class="wp-block-image size-large"><img src="$photo_url" alt="Volunteers sorting donations at the spring fair" class="wp-image-$photo_id"/><figcaption class="wp-element-caption">Photo: the spring fair</figcaption></figure>
<!-- /wp:image -->

<!-- wp:table -->
<figure class="wp-block-table"><table class="has-fixed-layout"><thead><tr><th>Session</th><th>Time</th></tr></thead><tbody><tr><td>Morning</td><td>9:00</td></tr><tr><td>Evening</td><td>18:00</td></tr></tbody></table></figure>
<!-- /wp:table -->

<!-- wp:quote -->
<blockquote class="wp-block-quote"><!-- wp:paragraph -->
<p>It made the site mine again.</p>
<!-- /wp:paragraph --><cite>A tester</cite></blockquote>
<!-- /wp:quote -->

<!-- wp:code -->
<pre class="wp-block-code"><code>print("hello")</code></pre>
<!-- /wp:code -->

<!-- wp:separator -->
<hr class="wp-block-separator has-alpha-channel-opacity"/>
<!-- /wp:separator -->

<!-- wp:embed {"url":"https://www.youtube.com/watch?v=dQw4w9WgXcQ","type":"video","providerNameSlug":"youtube","responsive":true} -->
<figure class="wp-block-embed is-type-video is-provider-youtube wp-block-embed-youtube"><div class="wp-block-embed__wrapper">
https://www.youtube.com/watch?v=dQw4w9WgXcQ
</div></figure>
<!-- /wp:embed -->

<!-- wp:latest-posts {"postsToShow":3} /-->

<!-- wp:shortcode -->
[gallery size="thumbnail"]
<!-- /wp:shortcode -->
BLOCKS
)
problems=$(cat <<PROB
<!-- wp:paragraph -->
<p>Check Before Publishing should find something in every paragraph below.</p>
<!-- /wp:paragraph -->

<!-- wp:heading {"level":1} -->
<h1 class="wp-block-heading">A heading 1 in the body</h1>
<!-- /wp:heading -->

<!-- wp:heading {"level":4} -->
<h4 class="wp-block-heading">A heading that skips from 1 to 4</h4>
<!-- /wp:heading -->

<!-- wp:paragraph -->
<p>To book, <a href="https://example.org/book">click here</a>. Or see <a href="https://example.org/">https://example.org/</a>, or <a href="https://example.org/new" target="_blank">our new page</a>.</p>
<!-- /wp:paragraph -->

<!-- wp:image -->
<figure class="wp-block-image"><img src="$photo_url"/></figure>
<!-- /wp:image -->

<!-- wp:paragraph -->
<p>Status: <span style="color:#cc0000">cancelled</span>.</p>
<!-- /wp:paragraph -->

<!-- wp:table -->
<figure class="wp-block-table"><table><tbody><tr><td>No</td><td>header row</td></tr></tbody></table></figure>
<!-- /wp:table -->
PROB
)

about=$(post about page publish "About Us" "<!-- wp:paragraph --><p>A lasting page.</p><!-- /wp:paragraph -->")
post contact page publish "Contact" "<!-- wp:paragraph --><p>Write to us.</p><!-- /wp:paragraph -->" >/dev/null
post team page publish "Meet the Team" "<!-- wp:paragraph --><p>Our presenters.</p><!-- /wp:paragraph -->" --post_parent="$about" >/dev/null
post every-block page publish "Every Block" "$blocks" >/dev/null
post listen-and-watch page publish "Listen and Watch" "<!-- wp:paragraph --><p>Play Media Here on each block below.</p><!-- /wp:paragraph -->

<!-- wp:audio {\"id\":$tone_id} -->
<figure class=\"wp-block-audio\"><audio controls src=\"$tone_url\"></audio><figcaption class=\"wp-element-caption\">A three-second test tone</figcaption></figure>
<!-- /wp:audio -->

<!-- wp:video {\"id\":$clip_id} -->
<figure class=\"wp-block-video\"><video controls src=\"$clip_url\"></video></figure>
<!-- /wp:video -->" >/dev/null
post page-draft page draft "A Draft Page" "<!-- wp:paragraph --><p>Not public yet.</p><!-- /wp:paragraph -->" >/dev/null

news=$(wp term get category news --by=slug --field=term_id)
training=$(wp term get category training --by=slug --field=term_id)
welcome=$(post welcome post publish "Welcome to the test site" "<!-- wp:paragraph --><p>The first published post. Open me by web address.</p><!-- /wp:paragraph -->" --post_category="$news" --tags_input="WordPress,Accessibility")
sticky=$(post sticky-news post publish "Pinned news" "<!-- wp:paragraph --><p>Sticky, at the top of the blog.</p><!-- /wp:paragraph -->" --post_category="$news")
wp option update sticky_posts "[$sticky]" --format=json >/dev/null
post check-me post draft "Things to check before publishing" "$problems" --post_category="$training" >/dev/null
post pending-review post pending "Waiting for review" "<!-- wp:paragraph --><p>Submitted by a contributor.</p><!-- /wp:paragraph -->" --post_author="$(wp user get quill-contributor --field=ID)" >/dev/null
post scheduled post future "Scheduled for next month" "<!-- wp:paragraph --><p>Goes live later.</p><!-- /wp:paragraph -->" --post_date="$(date -d '+30 days' '+%Y-%m-%d 09:00:00')" >/dev/null
post private-note post private "A private post" "<!-- wp:paragraph --><p>Editors only.</p><!-- /wp:paragraph -->" >/dev/null
post locked post publish "Password protected" "<!-- wp:paragraph --><p>Behind a password.</p><!-- /wp:paragraph -->" --post_password=quill >/dev/null
post classic post publish "Classic content" "<p>Written in the classic editor, with no block comments at all.</p><p>Second paragraph.</p>" >/dev/null
post by-author post publish "Written by the author" "<!-- wp:paragraph --><p>Owned by quill-author.</p><!-- /wp:paragraph -->" --post_author="$(wp user get quill-author --field=ID)" >/dev/null
trashed=$(post in-the-trash post publish "In the Trash" "<!-- wp:paragraph --><p>Restore me.</p><!-- /wp:paragraph -->")
[ "$(wp post get "$trashed" --field=post_status)" = trash ] || wp post delete "$trashed" >/dev/null

# Revisions: change the welcome post a few times.
if [ "$(wp post list --post_type=revision --post_parent="$welcome" --format=count)" -lt 3 ]; then
  for n in 1 2 3; do
    wp post update "$welcome" --post_content="<!-- wp:paragraph --><p>The first published post, version $n. Open me by web address.</p><!-- /wp:paragraph -->" >/dev/null
  done
fi

# A synced pattern.
[ -n "$(wp post list --post_type=wp_block --name=event-announcement --field=ID)" ] || \
  printf '%s' '<!-- wp:heading --><h2 class="wp-block-heading">Event name</h2><!-- /wp:heading --><!-- wp:paragraph --><p>Date, time and place.</p><!-- /wp:paragraph -->' | \
  wp post create - --post_type=wp_block --post_status=publish --post_title="Event announcement" --post_name=event-announcement >/dev/null

# --- a custom post type ------------------------------------------------------
# Events, registered by a must-use plugin, so Open's list of kinds and a custom
# type's save, publish and Trash can be tested (wordpress.md 5.2). Shown in REST.
wp eval '$d = WP_CONTENT_DIR . "/mu-plugins"; if (!is_dir($d)) { mkdir($d, 0755, true); }
file_put_contents($d . "/quill-test-events.php", "<?php
add_action(\"init\", function () {
  register_post_type(\"event\", array(\"label\" => \"Events\", \"public\" => true, \"show_in_rest\" => true, \"rest_base\" => \"events\", \"supports\" => array(\"title\", \"editor\", \"revisions\", \"author\")));
});
");'
post open-day event publish "Open Day" "<!-- wp:paragraph --><p>Come and see the studio.</p><!-- /wp:paragraph -->" >/dev/null

# --- comments --------------------------------------------------------------
if [ "$(wp comment list --post_id="$welcome" --status=all --format=count)" -lt 3 ] && \
   [ "$(wp comment list --post_id="$welcome" --status=spam --format=count)" -lt 1 ]; then
  wp comment create --comment_post_ID="$welcome" --comment_author="Sam" --comment_content="Great news, thank you!" --comment_approved=1 >/dev/null
  wp comment create --comment_post_ID="$welcome" --comment_author="Alex" --comment_content="When does the next session start?" --comment_approved=0 >/dev/null
  wp comment create --comment_post_ID="$welcome" --comment_author="Spammy" --comment_content="Buy cheap things" --comment_approved=spam >/dev/null
fi

# --- menus -----------------------------------------------------------------
echo "Done. Site: $URL  Admin: $URL/wp-admin  Accounts: $(pwd)/$ACCOUNTS"
