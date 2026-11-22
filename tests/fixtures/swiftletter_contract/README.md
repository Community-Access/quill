# SwiftLetter Phase 1 contract fixtures

Copied unchanged from SwiftLetter's shared REST contract: payown/SwiftLetter pull
request #11, branch `ci/rest-contract-tests`, commit
`aa076f266e416f0a6f5185a2677eb88c5ec3f1d9` (2026-11-22), folder
`app/public/wp-content/plugins/SwiftLetter/tests/contract/fixtures/`.

Every file is `"contract_version": 1`. SwiftLetter's CI runs the same files
against a disposable WordPress site; QUILL's
`tests/unit/core/wordpress/test_wp_swiftletter_contract.py` replays their
`example` responses and error bodies through QUILL's client, so a change on
either side that breaks the other fails a test. All content is fictional.

To update: copy the folder's JSON files again from SwiftLetter, change the commit
above, and run the contract test. Do not edit the JSON here by hand.
