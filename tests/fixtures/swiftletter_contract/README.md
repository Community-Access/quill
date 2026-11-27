# SwiftLetter Phase 1 contract fixtures

Copied unchanged from SwiftLetter's shared REST contract: payown/SwiftLetter pull
request #11, branch `ci/rest-contract-tests`, commit
`8a646e47d56c7d7daee3abf908f983df97550559` (2026-11-27, after SwiftLetter #13
and #17), folder
`app/public/wp-content/plugins/SwiftLetter/tests/contract/fixtures/`, including
its `compat/` folder. `compat/article-save-1.1.0-rc.1.json` is how SwiftLetter
1.1.0-rc.1 answered a save (id and edit_version only), kept so QUILL still
copes with rc.1 sites.

Every file is `"contract_version": 1`. SwiftLetter's CI runs the same files
against a disposable WordPress site; QUILL's
`tests/unit/core/wordpress/test_wp_swiftletter_contract.py` replays their
`example` responses and error bodies through QUILL's client, so a change on
either side that breaks the other fails a test. All content is fictional.

To update: copy the folder's JSON files (and `compat/`) again from SwiftLetter, change the commit
above, and run the contract test. Do not edit the JSON here by hand.
