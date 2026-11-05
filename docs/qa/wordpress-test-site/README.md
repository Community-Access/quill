# The WordPress test site

These are the scripts that build and look after QUILL's WordPress test site,
https://lp.csedesigns.com/wordpress/. The tests themselves, the accounts and
what is seeded on the site are in the regression plan,
`docs/qa/wordpress-regression-testing.md`.

- `docker-compose.yml`: the two containers, WordPress and MariaDB.
- `setup.sh`: installs WordPress, makes the accounts and their application
  passwords, and seeds the pages, posts, media and patterns.
- `reset.sh`: puts the content back to its starting state, keeping the
  accounts, passwords, settings and media.
- `verify.sh`: signs in as each role and prints what each can do, never a
  password.
- `store-passwords.py`: copies the passwords from the server into Windows
  Credential Manager on this computer (below).

The shell scripts live on the server in `~/app/wordpress-test/`; these copies
are kept here so the site can be rebuilt.

## Where the test passwords live

No password is ever in this repository. There are two copies, both private.

**On this computer, in Windows Credential Manager.** Each password is a
generic credential under the service
`QUILL WordPress test site (lp.csedesigns.com)`, with the user name
`<login> <kind>`, where kind is `sign-in` or `application`. There are nine:

- `quilladmin sign-in` and `quilladmin application`;
- `quill-editor sign-in` and `quill-editor application`;
- `quill-author sign-in` and `quill-author application`;
- `quill-contributor sign-in` and `quill-contributor application`;
- `quill-subscriber sign-in` (the subscriber has no application password).

**On the server.** `~/app/wordpress-test/test-accounts.txt` (mode 600) holds
the sign-in passwords of the four test accounts and the application
passwords of the first four logins. The administrator's sign-in password is
`ADMIN_PASSWORD` in `~/app/wordpress-test/.env`.

**Refreshing the local copy.** Whenever the server's copy changes, after
`setup.sh` builds a fresh site or a reset makes new passwords, run this from
the repository root:

```powershell
python docs/qa/wordpress-test-site/store-passwords.py --admin-sign-in
```

It reads the server's file over ssh, stores each entry with `keyring`, and
prints only the names it stored. Without `--admin-sign-in` it leaves the
administrator's sign-in password alone. To store from a copy you already
have instead of using ssh, pass `--file <path>`. `reset.sh` as it is written
keeps the accounts and their passwords, so an ordinary reset needs no
refresh.

The live run, `docs/qa/wordpress-live-run.py`, reads the application
passwords from Credential Manager.
