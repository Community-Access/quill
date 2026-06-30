from __future__ import annotations

from quill.core.features import (
    FEATURE_DEFINITIONS,
    FEATURE_STATE_OFF,
    FEATURE_STATE_ON,
    PROFILE_ACCESSIBILITY_PROFESSIONAL,
    PROFILE_AUTHOR_STUDENT,
    PROFILE_DEFINITIONS,
    PROFILE_DEVELOPER_POWER_TEXT,
    PROFILE_ESSENTIAL,
    PROFILE_FULL_QUILL,
    PROFILE_WRITER,
    FeatureManager,
    feature_for_command,
)


def test_inbound_publishing_commands_map_to_read_feature() -> None:
    # Read-only inbound commands are gated by future.publishing_read so they
    # can ship without lighting up any content-send path.
    read_commands = [
        "publishing.connections",
        "publishing.verify_connection",
        "publishing.browse_content",
        "publishing.open_remote_item",
    ]

    for command_id in read_commands:
        assert feature_for_command(command_id) == "future.publishing_read"


def test_send_publishing_commands_map_to_locked_publishing_feature() -> None:
    # Every content-send command stays under the locked-off future.publishing
    # feature so it never reaches a public release until approved.
    send_commands = [
        "publishing.create_draft",
        "publishing.publish_current",
        "publishing.create_page_draft",
        "publishing.publish_current_page",
        "publishing.update_remote_item",
        "publishing.publish_remote_item",
        "publishing.schedule_publish",
        "publishing.compare_remote_item",
    ]

    for command_id in send_commands:
        assert feature_for_command(command_id) == "future.publishing"


def test_publishing_command_ids_stay_provider_neutral() -> None:
    publishing_commands = [
        "publishing.connections",
        "publishing.verify_connection",
        "publishing.create_draft",
        "publishing.publish_current",
        "publishing.create_page_draft",
        "publishing.publish_current_page",
        "publishing.browse_content",
        "publishing.open_remote_item",
        "publishing.update_remote_item",
        "publishing.publish_remote_item",
        "publishing.schedule_publish",
        "publishing.compare_remote_item",
    ]

    assert all(command_id.startswith("publishing.") for command_id in publishing_commands)
    assert all("wordpress" not in command_id for command_id in publishing_commands)


def test_publishing_feature_is_locked_off_pending_review() -> None:
    # The publishing-providers-framework branch is locked off so it never
    # ships in a public release until this gate is deliberately lifted.
    definition = FEATURE_DEFINITIONS["future.publishing"]
    assert definition.locked_off is True


def test_publishing_disabled_in_default_build() -> None:
    manager = FeatureManager.load(persistent=False)
    assert manager.is_enabled("future.publishing") is False
    assert manager.is_visible("future.publishing") is False


def test_publishing_profile_states_match_writer_tier_and_above() -> None:
    # Publishing is restricted to "writer and above": Casual Writer, Author
    # or Student, Developer and Power Text, and Full Quill get it by
    # default; every other profile defaults it off. This is the *configured*
    # value in PROFILE_DEFINITIONS, independent of the live locked_off
    # short-circuit asserted by test_publishing_disabled_in_default_build
    # above -- see test_publishing_profile_states_are_overridden_by_the_lock
    # for how the two interact.
    included = {
        PROFILE_WRITER,
        PROFILE_AUTHOR_STUDENT,
        PROFILE_DEVELOPER_POWER_TEXT,
        PROFILE_FULL_QUILL,
    }
    excluded = {
        PROFILE_ESSENTIAL,
        "reader_and_student",
        "office_and_admin",
        "low_vision",
        "braille_screen_reader_power_user",
        PROFILE_ACCESSIBILITY_PROFESSIONAL,
    }
    assert included | excluded == set(PROFILE_DEFINITIONS)
    for profile_id in included:
        states = PROFILE_DEFINITIONS[profile_id].states
        assert states.get("future.publishing") == FEATURE_STATE_ON, profile_id
    for profile_id in excluded:
        states = PROFILE_DEFINITIONS[profile_id].states
        assert states.get("future.publishing") == FEATURE_STATE_OFF, profile_id


def test_publishing_profile_states_are_overridden_by_the_lock() -> None:
    # Even though the 4 writer-tier-and-above profiles configure
    # future.publishing ON, the feature stays unreachable everywhere while
    # it remains locked_off -- locked_off is checked before any profile is
    # ever consulted. This guards against a future session mistaking "the
    # profile data says ON" for "the feature is actually enabled."
    for profile_id in PROFILE_DEFINITIONS:
        manager = FeatureManager(active_profile_id=profile_id)
        assert manager.state_for("future.publishing") == FEATURE_STATE_OFF, profile_id


def test_publishing_read_feature_is_not_locked_off() -> None:
    # Unlike future.publishing (send), the read-only inbound feature ships:
    # it is not locked, so writer-tier profiles can actually reach it.
    definition = FEATURE_DEFINITIONS["future.publishing_read"]
    assert definition.locked_off is False
    assert definition.locked_on is False


def test_publishing_read_is_reachable_only_in_full_quill() -> None:
    # Read-only inbound is enabled by default only in the all-features (Full
    # Quill) profile; every other profile leaves it off (any user can still
    # enable it individually). It is not locked, so Full Quill genuinely
    # reaches it.
    for profile_id in PROFILE_DEFINITIONS:
        manager = FeatureManager(active_profile_id=profile_id)
        if profile_id == PROFILE_FULL_QUILL:
            assert manager.is_enabled("future.publishing_read") is True, profile_id
        else:
            assert manager.is_enabled("future.publishing_read") is False, profile_id
