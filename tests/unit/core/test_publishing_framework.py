from __future__ import annotations

from quill.core.features import feature_for_command


def test_publishing_commands_map_to_publishing_feature() -> None:
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
    ]

    for command_id in publishing_commands:
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
    ]

    assert all(command_id.startswith("publishing.") for command_id in publishing_commands)
    assert all("wordpress" not in command_id for command_id in publishing_commands)
