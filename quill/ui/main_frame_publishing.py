"""Publishing (WordPress) commands for MainFrame (CQ-1 decomposition).

``PublishingCommandsMixin`` owns the publishing surface: the connections
dialog, connection verification, remote content browsing, remote-item compare
/ open / update / publish, draft and page-draft creation, the scheduled
publish flow, and the linkage helpers that keep a local document tied to its
remote item. Extracted verbatim from ``main_frame.py``; runs on ``MainFrame``
(``self``). Publishing *send* stays feature-locked (future.publishing_read is
the lit read-only flag); all outbound calls route through the audited
publishing core.
"""

from __future__ import annotations

from quill.core.document import Document
from quill.core.locations import LocationRing


class PublishingCommandsMixin:
    def _open_publishing_connections(self) -> None:
        from quill.ui.publishing_tools import PublishingConnectionsDialog

        dialog = PublishingConnectionsDialog(self.frame, announce_cb=self._announce)
        if dialog.show_modal():
            self._set_status("Updated publishing connections")
        else:
            self._set_status("Publishing connections cancelled")

    def _verify_current_publishing_connection(self) -> None:
        from quill.core.publishing import (
            current_publishing_connection,
            load_publishing_secret,
            verify_publishing_connection,
        )

        profile = current_publishing_connection()
        if profile is None:
            message = "No current publishing connection is selected."
            self._show_message_box(
                message,
                "Publishing Connection Check",
                self._wx.ICON_WARNING | self._wx.OK,
            )
            self._set_status(message)
            return
        ok, message = verify_publishing_connection(profile, load_publishing_secret(profile.id))
        icon = self._wx.ICON_INFORMATION if ok else self._wx.ICON_WARNING
        self._show_message_box(message, "Publishing Connection Check", icon | self._wx.OK)
        self._set_status(message)

    def _browse_publishing_content(self) -> None:
        from quill.core.publishing import prepare_publishing_remote_content
        from quill.ui.publishing_tools import BrowsePublishingContentDialog

        dialog = BrowsePublishingContentDialog(
            self.frame, self._task_manager, announce_cb=self._announce
        )
        remote_document = dialog.show_modal()
        if remote_document is None:
            self._set_status("Browse publishing content cancelled")
            return
        prepared_content = prepare_publishing_remote_content(
            remote_document.body,
            requested_open_representation=dialog.selected_open_representation,
        )
        metadata = {
            "source_kind": "publishing_remote",
            "display_name": remote_document.title,
            "source_label": "from publishing",
            "publishing_authoring_surface": prepared_content.authoring_surface,
            "publishing_open_representation": prepared_content.open_representation,
            "publishing_provider_id": remote_document.provider_id,
            "publishing_site_url": remote_document.site_url,
            "publishing_remote_id": remote_document.remote_id,
            "publishing_remote_url": remote_document.remote_url,
            "publishing_remote_title": remote_document.title,
            "publishing_content_kind": remote_document.content_kind,
            "publishing_status": remote_document.status,
            "publishing_updated_at": remote_document.updated_at,
        }
        document = Document(
            text=prepared_content.text,
            path=None,
            modified=False,
            source_metadata=metadata,
        )
        self._clear_empty_workspace_state()
        self._create_document_tab(document, select=True)
        self._location_ring = LocationRing()
        self._location_ring.record(0)
        self._refresh_title()
        content_kind = "page" if remote_document.content_kind == "page" else "post"
        self._set_status(f"Opened {content_kind} from publishing.")

    def _compare_publishing_remote_item(self) -> None:
        from quill.core.publishing import (
            compare_publishing_remote_item,
            current_publishing_connection,
            load_publishing_secret,
            publishing_comparison_message,
        )

        dialog_title = "Compare With Remote"
        metadata = self.document.source_metadata
        if metadata.get("source_kind") != "publishing_remote":
            message = "Open remote publishing content before comparing it with the remote site."
            self._show_message_box(message, dialog_title, self._wx.ICON_INFORMATION | self._wx.OK)
            self._set_status(message)
            return
        profile = current_publishing_connection()
        if profile is None:
            message = "No current publishing connection is selected."
            self._show_message_box(message, dialog_title, self._wx.ICON_WARNING | self._wx.OK)
            self._set_status(message)
            return
        provider_id = str(metadata.get("publishing_provider_id", "")).strip()
        site_url = str(metadata.get("publishing_site_url", "")).strip()
        remote_id = str(metadata.get("publishing_remote_id", "")).strip()
        content_kind = str(metadata.get("publishing_content_kind", "")).strip().lower()
        authoring_surface = str(metadata.get("publishing_authoring_surface", "")).strip().lower()
        if provider_id and profile.provider_id != provider_id:
            message = "The current publishing connection does not match this remote item."
            self._show_message_box(message, dialog_title, self._wx.ICON_WARNING | self._wx.OK)
            self._set_status(message)
            return
        if site_url and profile.site_url.rstrip("/") != site_url.rstrip("/"):
            message = "The current publishing connection does not match this remote site."
            self._show_message_box(message, dialog_title, self._wx.ICON_WARNING | self._wx.OK)
            self._set_status(message)
            return
        ok, message, comparison = compare_publishing_remote_item(
            profile,
            load_publishing_secret(profile.id),
            content_kind=content_kind,
            remote_id=remote_id,
            local_title=self._current_document_title(),
            local_document_text=self.editor.GetValue(),
            local_authoring_surface=authoring_surface or "markdown",
            local_status=str(metadata.get("publishing_status", "")).strip(),
            last_known_updated_at=str(metadata.get("publishing_updated_at", "")).strip(),
        )
        icon = self._wx.ICON_INFORMATION if ok else self._wx.ICON_WARNING
        report = (
            publishing_comparison_message(comparison) if ok and comparison is not None else message
        )
        self._show_message_box(report, dialog_title, icon | self._wx.OK)
        self._set_status(report.splitlines()[0] if ok else message)

    def _update_publishing_remote_item(self) -> None:
        self._send_publishing_remote_item(status=None)

    def _publish_open_remote_item(self) -> None:
        self._send_publishing_remote_item(status="publish")

    def _send_publishing_remote_item(self, *, status: str | None) -> None:
        from quill.core.publishing import (
            current_publishing_connection,
            load_publishing_secret,
            publishing_result_message,
            update_publishing_remote_item,
        )

        metadata = self.document.source_metadata
        if metadata.get("source_kind") != "publishing_remote":
            message = (
                "Open remote publishing content before publishing remote content."
                if status == "publish"
                else "Open remote publishing content before updating remote content."
            )
            self._show_message_box(
                message,
                "Publish Open Remote Content" if status == "publish" else "Update Remote Content",
                self._wx.ICON_INFORMATION | self._wx.OK,
            )
            self._set_status(message)
            return
        profile = current_publishing_connection()
        if profile is None:
            message = "No current publishing connection is selected."
            self._show_message_box(
                message,
                "Publish Open Remote Content" if status == "publish" else "Update Remote Content",
                self._wx.ICON_WARNING | self._wx.OK,
            )
            self._set_status(message)
            return
        provider_id = str(metadata.get("publishing_provider_id", "")).strip()
        site_url = str(metadata.get("publishing_site_url", "")).strip()
        remote_id = str(metadata.get("publishing_remote_id", "")).strip()
        content_kind = str(metadata.get("publishing_content_kind", "")).strip().lower()
        authoring_surface = str(metadata.get("publishing_authoring_surface", "")).strip().lower()
        if provider_id and profile.provider_id != provider_id:
            message = "The current publishing connection does not match this remote item."
            self._show_message_box(
                message,
                "Publish Open Remote Content" if status == "publish" else "Update Remote Content",
                self._wx.ICON_WARNING | self._wx.OK,
            )
            self._set_status(message)
            return
        if site_url and profile.site_url.rstrip("/") != site_url.rstrip("/"):
            message = "The current publishing connection does not match this remote site."
            self._show_message_box(
                message,
                "Publish Open Remote Content" if status == "publish" else "Update Remote Content",
                self._wx.ICON_WARNING | self._wx.OK,
            )
            self._set_status(message)
            return
        label_kind = "page" if content_kind == "page" else "post"
        remote_url = str(metadata.get("publishing_remote_url", "")).strip() or "(no public URL)"
        title = self._current_document_title()
        is_publish = status == "publish"
        dialog_title = "Publish Open Remote Content" if is_publish else "Update Remote Content"
        action_label = "Publish" if is_publish else "Update"
        action_detail = (
            "publish it" if is_publish else "send the current document text to the remote item"
        )
        review_message = (
            f"{action_label} this remote {label_kind} on {profile.site_url}?\n\n"
            f"Title: {title}\n"
            f"Authoring surface: {authoring_surface or 'markdown'}\n"
            f"Remote URL: {remote_url}\n\n"
            f"Choose Yes to {action_detail}."
        )
        proceed = self._show_message_box(
            review_message,
            dialog_title,
            self._wx.ICON_INFORMATION | self._wx.YES_NO | self._wx.CANCEL,
        )
        if proceed != self._wx.ID_YES:
            self._set_status(
                "Publish open remote content cancelled"
                if is_publish
                else "Update remote content cancelled"
            )
            return
        ok, message, remote_document = update_publishing_remote_item(
            profile,
            load_publishing_secret(profile.id),
            content_kind=content_kind,
            remote_id=remote_id,
            title=title,
            document_text=self.editor.GetValue(),
            authoring_surface=authoring_surface or "markdown",
            status=status,
        )
        icon = self._wx.ICON_INFORMATION if ok else self._wx.ICON_WARNING
        result_message = (
            publishing_result_message("updated", remote_document)
            if ok and remote_document is not None
            else message
        )
        self._show_message_box(result_message, dialog_title, icon | self._wx.OK)
        if not ok or remote_document is None:
            self._set_status(message)
            return
        metadata["publishing_status"] = remote_document.status
        metadata["publishing_updated_at"] = remote_document.updated_at
        metadata["publishing_remote_url"] = remote_document.remote_url
        metadata["publishing_remote_title"] = remote_document.title
        metadata["display_name"] = remote_document.title
        self.document.mark_saved()
        self._sync_publishing_linkage_for_document(self.document)
        self._refresh_title()
        self._set_status(result_message.splitlines()[0])

    def _create_publishing_draft(self) -> None:
        self._create_publishing_item("post", status="draft")

    def _publish_current_document(self) -> None:
        self._create_publishing_item("post", status="publish")

    def _create_publishing_page_draft(self) -> None:
        self._create_publishing_item("page", status="draft")

    def _publish_current_page(self) -> None:
        self._create_publishing_item("page", status="publish")

    def _create_publishing_item(self, content_kind: str, *, status: str) -> None:
        from quill.core.publishing import (
            create_publishing_remote_item,
            current_publishing_connection,
            load_publishing_secret,
            publishing_result_message,
        )

        profile = current_publishing_connection()
        if profile is None:
            message = "No current publishing connection is selected."
            self._show_message_box(
                message,
                "Create Publishing Draft",
                self._wx.ICON_WARNING | self._wx.OK,
            )
            self._set_status(message)
            return
        title = self._publishing_document_title()
        authoring_surface = self._publishing_document_authoring_surface()
        label_kind = "page" if content_kind == "page" else "post"
        publishing_status = "publish" if status.strip().lower() == "publish" else "draft"
        action_label = "Publish" if publishing_status == "publish" else "Create"
        state_label = "published" if publishing_status == "publish" else "draft"
        dialog_title = (
            "Publish Current Document"
            if publishing_status == "publish"
            else "Create Publishing Draft"
        )
        review_message = (
            f"{action_label} this remote {label_kind} as {state_label} on {profile.site_url}?\n\n"
            f"Title: {title}\n"
            f"Authoring surface: {authoring_surface}\n\n"
            f"Choose Yes to send the current document text and {action_label.lower()} it."
        )
        proceed = self._show_message_box(
            review_message,
            dialog_title,
            self._wx.ICON_INFORMATION | self._wx.YES_NO | self._wx.CANCEL,
        )
        if proceed != self._wx.ID_YES:
            self._set_status(
                "Publish current document cancelled"
                if publishing_status == "publish"
                else "Create publishing draft cancelled"
            )
            return
        ok, message, remote_document = create_publishing_remote_item(
            profile,
            load_publishing_secret(profile.id),
            content_kind=content_kind,
            title=title,
            document_text=self.editor.GetValue(),
            authoring_surface=authoring_surface,
            status=publishing_status,
        )
        icon = self._wx.ICON_INFORMATION if ok else self._wx.ICON_WARNING
        result_message = (
            publishing_result_message("created", remote_document)
            if ok and remote_document is not None
            else message
        )
        self._show_message_box(result_message, dialog_title, icon | self._wx.OK)
        if not ok or remote_document is None:
            self._set_status(message)
            return
        self.document.source_metadata.update({
            "source_kind": "publishing_remote",
            "display_name": remote_document.title,
            "source_label": "from publishing",
            "publishing_authoring_surface": authoring_surface,
            "publishing_open_representation": (
                "raw_html" if authoring_surface == "html" else "readable_markdown"
            ),
            "publishing_provider_id": remote_document.provider_id,
            "publishing_site_url": remote_document.site_url,
            "publishing_remote_id": remote_document.remote_id,
            "publishing_remote_url": remote_document.remote_url,
            "publishing_remote_title": remote_document.title,
            "publishing_content_kind": remote_document.content_kind,
            "publishing_status": remote_document.status,
            "publishing_updated_at": remote_document.updated_at,
        })
        self.document.mark_saved()
        self._sync_publishing_linkage_for_document(self.document)
        self._refresh_title()
        self._set_status(result_message.splitlines()[0])

    def _publishing_document_title(self) -> str:
        title = self._current_document_title().strip()
        if title:
            return title
        first_line = (
            self.editor.GetValue().splitlines()[0].strip() if self.editor.GetValue() else ""
        )
        if first_line:
            return first_line.lstrip("#").strip() or "(untitled)"
        return "(untitled)"

    def _publishing_document_authoring_surface(self) -> str:
        metadata = self.document.source_metadata
        saved_surface = str(metadata.get("publishing_authoring_surface", "")).strip().lower()
        if saved_surface in {"markdown", "html"}:
            return saved_surface
        path = getattr(self.document, "path", None)
        if path is not None and path.suffix.lower() in {".html", ".htm", ".xhtml"}:
            return "html"
        return "markdown"

    def _schedule_publishing_publish(self) -> None:
        from quill.core.publishing import (
            create_publishing_remote_item,
            current_publishing_connection,
            load_publishing_secret,
            publishing_result_message,
            update_publishing_remote_item,
        )
        from quill.ui.publishing_tools import SchedulePublishDialog

        profile = current_publishing_connection()
        if profile is None:
            message = "No current publishing connection is selected."
            self._show_message_box(message, "Schedule Publish", self._wx.ICON_WARNING | self._wx.OK)
            self._set_status(message)
            return

        metadata = self.document.source_metadata
        is_remote_item = metadata.get("source_kind") == "publishing_remote"
        remote_id = ""
        fixed_content_kind: str | None = None
        if is_remote_item:
            provider_id = str(metadata.get("publishing_provider_id", "")).strip()
            site_url = str(metadata.get("publishing_site_url", "")).strip()
            if provider_id and profile.provider_id != provider_id:
                message = "The current publishing connection does not match this remote item."
                self._show_message_box(
                    message, "Schedule Publish", self._wx.ICON_WARNING | self._wx.OK
                )
                self._set_status(message)
                return
            if site_url and profile.site_url.rstrip("/") != site_url.rstrip("/"):
                message = "The current publishing connection does not match this remote site."
                self._show_message_box(
                    message, "Schedule Publish", self._wx.ICON_WARNING | self._wx.OK
                )
                self._set_status(message)
                return
            remote_id = str(metadata.get("publishing_remote_id", "")).strip()
            fixed_content_kind = (
                str(metadata.get("publishing_content_kind", "")).strip().lower() or "post"
            )

        dialog = SchedulePublishDialog(
            self.frame,
            provider_id=profile.provider_id,
            fixed_content_kind=fixed_content_kind,
            announce_cb=self._announce,
        )
        choice = dialog.show_modal()
        if choice is None:
            self._set_status("Schedule publish cancelled")
            return

        content_kind = fixed_content_kind or choice.content_kind
        label_kind = "page" if content_kind == "page" else "post"
        title = (
            self._current_document_title() if is_remote_item else self._publishing_document_title()
        )
        authoring_surface = (
            str(metadata.get("publishing_authoring_surface", "")).strip().lower() or "markdown"
            if is_remote_item
            else self._publishing_document_authoring_surface()
        )
        when_local = choice.scheduled_at.strftime("%Y-%m-%d %H:%M %Z")
        review_message = (
            f"Schedule this remote {label_kind} to publish on {profile.site_url}?\n\n"
            f"Title: {title}\n"
            f"Scheduled for: {when_local}\n"
            f"Authoring surface: {authoring_surface}\n\n"
            "Choose Yes to send the current document text and schedule it."
        )
        proceed = self._show_message_box(
            review_message,
            "Schedule Publish",
            self._wx.ICON_INFORMATION | self._wx.YES_NO | self._wx.CANCEL,
        )
        if proceed != self._wx.ID_YES:
            self._set_status("Schedule publish cancelled")
            return

        secret = load_publishing_secret(profile.id)
        if remote_id:
            ok, message, remote_document = update_publishing_remote_item(
                profile,
                secret,
                content_kind=content_kind,
                remote_id=remote_id,
                title=title,
                document_text=self.editor.GetValue(),
                authoring_surface=authoring_surface,
                scheduled_at=choice.scheduled_at,
            )
        else:
            ok, message, remote_document = create_publishing_remote_item(
                profile,
                secret,
                content_kind=content_kind,
                title=title,
                document_text=self.editor.GetValue(),
                authoring_surface=authoring_surface,
                scheduled_at=choice.scheduled_at,
            )
        icon = self._wx.ICON_INFORMATION if ok else self._wx.ICON_WARNING
        result_message = (
            publishing_result_message("scheduled", remote_document)
            if ok and remote_document is not None
            else message
        )
        self._show_message_box(result_message, "Schedule Publish", icon | self._wx.OK)
        if not ok or remote_document is None:
            self._set_status(message)
            return
        self.document.source_metadata.update({
            "source_kind": "publishing_remote",
            "display_name": remote_document.title,
            "source_label": "from publishing",
            "publishing_authoring_surface": authoring_surface,
            "publishing_open_representation": (
                "raw_html" if authoring_surface == "html" else "readable_markdown"
            ),
            "publishing_provider_id": remote_document.provider_id,
            "publishing_site_url": remote_document.site_url,
            "publishing_remote_id": remote_document.remote_id,
            "publishing_remote_url": remote_document.remote_url,
            "publishing_remote_title": remote_document.title,
            "publishing_content_kind": remote_document.content_kind,
            "publishing_status": remote_document.status,
            "publishing_updated_at": remote_document.updated_at,
            "publishing_scheduled_for": remote_document.scheduled_for,
        })
        self.document.mark_saved()
        self._sync_publishing_linkage_for_document(self.document)
        self._refresh_title()
        self._set_status(result_message.splitlines()[0])
