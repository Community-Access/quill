#!/usr/bin/env bash
# Put the QUILL WordPress test site's content back to its known starting state.
# Keeps the accounts, application passwords, settings and media; deletes every
# page, post and synced pattern a test may have changed, then reseeds.
set -euo pipefail
cd "$(dirname "$0")"
set -a; . ./.env; set +a
wp() {
  docker run --rm -i --user 33:33 --volumes-from wordpress-test --network wordpress-test_internal \
    -w /var/www/html/wordpress -e WORDPRESS_DB_HOST=db -e WORDPRESS_DB_NAME=wordpress \
    -e WORDPRESS_DB_USER=wordpress -e "WORDPRESS_DB_PASSWORD=$DB_PASSWORD" wordpress:cli wp "$@"
}
ids=$(wp post list --post_type=post,page,wp_block --post_status=publish,draft,pending,future,private,trash --field=ID </dev/null)
keep="1 2"   # Hello world! and Sample Page, from the WordPress install
del=""
for id in $ids; do
  case " $keep " in *" $id "*) ;; *) del="$del $id";; esac
done
[ -n "$del" ] && wp post delete $del --force </dev/null >/dev/null
rm -f seed-ids.txt
./setup.sh
