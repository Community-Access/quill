#!/usr/bin/env bash
# Smoke-check the QUILL WordPress test site the way QUILL talks to it.
# Prints facts only; never prints a password.
set -uo pipefail
cd "$(dirname "$0")"
B=https://lp.csedesigns.com/wordpress/wp-json
pw() { grep "^$1 application password" test-accounts.txt | sed 's/.*: //'; }
j() { python3 -c "import sys,json; d=json.load(sys.stdin); print($1)"; }

echo "REST index:"
curl -s "$B/" | j '"  name:", d["name"], "| app passwords:", bool(d.get("authentication",{}).get("application-passwords")), "| batch/v1:", "batch/v1" in d["namespaces"]'
for user in quilladmin quill-editor quill-author quill-contributor; do
  printf '%-18s' "$user:"
  curl -s -u "$user:$(pw $user)" "$B/wp/v2/users/me?context=edit" \
    | j '",".join(d.get("roles",[])), "| publish posts:", d.get("capabilities",{}).get("publish_posts",False), "| publish pages:", d.get("capabilities",{}).get("publish_pages",False), "| upload:", d.get("capabilities",{}).get("upload_files",False)'
done
A="quilladmin:$(pw quilladmin)"
echo "Posts by status:"
curl -s -u "$A" "$B/wp/v2/posts?status=any&context=edit&per_page=100&_fields=slug,status" \
  | j '"  " + ", ".join(sorted(p["status"]+":"+p["slug"] for p in d))'
echo "Trash:"
curl -s -u "$A" "$B/wp/v2/posts?status=trash&context=edit&_fields=slug" | j '"  " + ", ".join(p["slug"] for p in d)'
echo "Pages:"
curl -s -u "$A" "$B/wp/v2/pages?status=any&context=edit&_fields=slug,parent,status" | j '"  " + ", ".join(p["slug"]+("(child)" if p["parent"] else "") for p in d)'
echo "Media:"
curl -s -u "$A" "$B/wp/v2/media?context=edit&_fields=slug,alt_text" | j '"  " + ", ".join(p["slug"]+("" if p["alt_text"] else "(no alt)") for p in d)'
echo "Terms:"
curl -s "$B/wp/v2/categories?per_page=100&hide_empty=false&_fields=name,count" | j '"  categories: " + ", ".join("%s(%s)" % (t["name"], t["count"]) for t in d)'
curl -s "$B/wp/v2/tags?per_page=100&hide_empty=false&_fields=name,count" | j '"  tags: " + ", ".join("%s(%s)" % (t["name"], t["count"]) for t in d)'
printf 'Batch route: '; curl -s "$B/" | j '"/batch/v1" in d.get("routes", {})'
echo "Comments:"
for s in hold approve spam; do
  printf '  %s: ' "$s"; curl -s -u "$A" "$B/wp/v2/comments?status=$s&context=edit&_fields=id" | j 'len(d)'
done
welcome=$(curl -s -u "$A" "$B/wp/v2/posts?slug=welcome&_fields=id" | j 'd[0]["id"]')
printf 'Revisions of welcome: '; curl -s -u "$A" "$B/wp/v2/posts/$welcome/revisions?context=edit&_fields=id" | j 'len(d)'
printf 'Synced patterns: '; curl -s -u "$A" "$B/wp/v2/blocks?context=edit&_fields=slug" | j '", ".join(p["slug"] for p in d)'
printf 'Site logo set: '; curl -s -u "$A" "$B/wp/v2/settings" | j 'bool(d.get("site_logo"))'
for path in "" about/ every-block/ welcome/ wp-admin/; do
  printf 'GET /wordpress/%-14s %s\n' "$path" "$(curl -s -o /dev/null -w '%{http_code}' "https://lp.csedesigns.com/wordpress/$path")"
done
