"""Host-agnostic Quillin runtime for the standalone companion apps.

:class:`QuillinAppHost` is the wx-free counterpart of the editor's
``QuillinsMenuMixin``: it owns Quillin *discovery*, *contribution collection*,
per-Quillin *ExtensionHost lifecycle*, *event firing*, *schedule timers*, and
*provider registration* (e.g. podcast feed-auth) for any app that is not the
full editor -- Quill Radio, Quill Cast, and their siblings.

It stays wx-free by delegating the few UI-touching effects to two injected
collaborators:

* a :class:`~quill.core.quillins.host.HostServices` implementation (the
  app-neutral surface: ``ui.*``, storage, clipboard, contained fs) plus a
  :data:`~quill.core.quillins.host.ConsentCallback`, exactly like the editor;
* a thin :class:`AppFrameAdapter` for the wx bits the host cannot do itself --
  registering a command in the app's :class:`~quill.core.commands.CommandRegistry`,
  adding a contributed item to the app's Quillins menu, and announcing.

Everything else -- disk scan, manifest parse, registry build, ``targets``
filtering (via the loader), the SEC-8 third-party lock, the bundled flag, Safe
Mode, and the out-of-process worker lifecycle -- lives here, unchanged in spirit
from the editor mixin but with no editor/document assumptions.

Migrating the *editor* onto this host is deliberately out of scope: the editor's
mixin keeps working as-is (it hosts an editor document the app-neutral surface
does not model). See the design note in the accompanying report.
"""

from __future__ import annotations

import threading
from pathlib import Path
from typing import Any, Protocol

from quill.core.quillins.host import ConsentCallback, ExtensionHost, HostServices
from quill.core.quillins.loader import (
    InstalledExtension,
    discover_bundled_extensions,
    discover_extensions,
    load_enabled_bundled_manifests,
    load_enabled_manifests,
)
from quill.core.quillins.model import (
    CAP_BEACON_RESOLVER,
    CAP_PODCAST_FEED_AUTH,
    CAP_RADIO_DIRECTORY,
    CAP_STUDIO_PIPELINE,
    CAP_WEATHER_ALERTS,
    ExtensionManifest,
)
from quill.core.quillins.registry import ContributionRegistry, build_registry
from quill.core.quillins.snippets import SnippetContext, expand_snippet

#: Storage key a ``podcast.feed.auth`` handler writes its resulting header to.
#: The out-of-process worker discards a handler's *return* value, so a feed-auth
#: handler communicates its result by calling ``api.set_storage(FEED_AUTH_RESULT_KEY,
#: header)``; the host reads it back from the shared storage dict after the call.
FEED_AUTH_RESULT_KEY = "__quill_feed_auth_header__"
#: Result keys for the other host-mediated provider handlers, mirroring
#: FEED_AUTH_RESULT_KEY. Each handler writes its result (JSON for structured
#: payloads, a plain string for scalars) to its key; the host reads it back.
DIRECTORY_RESULT_KEY = "__quill_radio_directory_result__"
ALERTS_RESULT_KEY = "__quill_weather_alerts_result__"
PIPELINE_RESULT_KEY = "__quill_studio_pipeline_result__"
RESOLVER_RESULT_KEY = "__quill_beacon_resolver_result__"


def _decode_rows(raw: str) -> list[dict[str, str]]:
    """Decode a handler's JSON-array result into a list of string-keyed dict rows.

    A handler returning structured data (station rows, alert rows) JSON-encodes a
    list of objects into its result-key storage string; this decodes it back,
    tolerantly (a malformed or non-list payload yields no rows).
    """

    import json

    if not raw:
        return []
    try:
        parsed = json.loads(raw)
    except (ValueError, TypeError):
        return []
    if not isinstance(parsed, list):
        return []
    rows: list[dict[str, str]] = []
    for item in parsed:
        if isinstance(item, dict):
            rows.append({str(k): str(v) for k, v in item.items()})
    return rows


def _decode_object(raw: str) -> dict[str, Any] | None:
    """Decode a handler's JSON-object result, or None for an absent/bad payload."""

    import json

    if not raw:
        return None
    try:
        parsed = json.loads(raw)
    except (ValueError, TypeError):
        return None
    return parsed if isinstance(parsed, dict) else None


class AppFrameAdapter(Protocol):
    """The wx-touching surface :class:`QuillinAppHost` drives on its host frame.

    A companion-app frame (via ``QuillinsAppMixin``) supplies this so the host
    can register commands and place contributed menu items without importing
    ``wx`` itself. ``announce`` and command execution that a background thread
    may reach should be marshalled onto the UI thread by the implementation.
    """

    def register_command(
        self,
        command_id: str,
        title: str,
        handler: Any,
        binding: str | None,
    ) -> None: ...

    def add_menu_command(self, command_id: str, title: str) -> None: ...

    def announce(self, message: str, severity: str = "info") -> None: ...


class _RepeatingTimer:
    """A daemon, re-arming timer (wx-free) for a Quillin ``schedule`` entry."""

    def __init__(self, interval_seconds: int, callback: Any) -> None:
        self._interval = float(interval_seconds)
        self._callback = callback
        self._timer: threading.Timer | None = None
        self._stopped = False

    def start(self) -> None:
        self._arm()

    def _arm(self) -> None:
        if self._stopped:
            return
        timer = threading.Timer(self._interval, self._tick)
        timer.daemon = True
        self._timer = timer
        timer.start()

    def _tick(self) -> None:
        if self._stopped:
            return
        try:
            self._callback()
        finally:
            self._arm()

    def stop(self) -> None:
        self._stopped = True
        if self._timer is not None:
            self._timer.cancel()


class QuillinAppHost:
    """Own the full Quillin lifecycle for one standalone app (wx-free)."""

    def __init__(
        self,
        *,
        app_id: str,
        services: HostServices,
        consent: ConsentCallback,
        frame_adapter: AppFrameAdapter,
        features: object,
        keymap: dict[str, str] | None = None,
        safe_mode: bool = False,
        root: Path | None = None,
    ) -> None:
        self._app_id = app_id
        self._services = services
        self._consent = consent
        self._frame = frame_adapter
        self._features = features
        self._keymap = keymap or {}
        self._safe_mode = safe_mode
        self._root = root

        self._registry: ContributionRegistry | None = None
        # command id -> (manifest, extension directory)
        self._command_index: dict[str, tuple[ExtensionManifest, Path]] = {}
        # bundled command ids run without the SEC-8 third-party unlock.
        self._bundled_command_ids: set[str] = set()
        # quillin id -> {key: value} persistent-per-run storage (as in the editor)
        self._storage_data: dict[str, dict[str, str]] = {}
        # quillin id -> (manifest, directory) for document/app event subscriptions
        self._event_index: dict[str, tuple[ExtensionManifest, Path]] = {}
        self._timers: list[_RepeatingTimer] = []
        # provider ids this host registered into each per-app registry, cleared on
        # reload/shutdown so a reload never leaves stale providers behind.
        self._feed_auth_provider_ids: set[str] = set()
        self._directory_provider_ids: set[str] = set()
        self._alert_source_ids: set[str] = set()
        self._pipeline_step_ids: set[str] = set()
        self._resolver_ids: set[str] = set()

    # -- discovery -----------------------------------------------------------
    @property
    def app_id(self) -> str:
        return self._app_id

    @property
    def registry(self) -> ContributionRegistry | None:
        return self._registry

    def installed(self) -> list[InstalledExtension]:
        """Every Quillin targeting this app: bundled (Tier C) first, then third-party."""

        found = list(
            discover_bundled_extensions(self._features, root=self._root, app_id=self._app_id)
        )
        found.extend(discover_extensions(self._features, root=self._root, app_id=self._app_id))
        return found

    # -- load / reload -------------------------------------------------------
    def load(self) -> None:
        """Discover enabled Quillins, collect contributions, and wire them up.

        Safe Mode is the load-bearing choke point (P1-7): no contribution is
        collected, no command registered, no provider populated, and no timer
        started. The menu still builds around this (Manage Quillins stays), but
        nothing runnable is loaded.
        """

        self._teardown_runtime()
        self._registry = None
        self._command_index = {}
        self._bundled_command_ids = set()
        self._event_index = {}

        if self._safe_mode:
            self._frame.announce("Quillins are disabled in Safe Mode.")
            return

        installed = {item.id: item for item in self.installed()}
        bundled_manifests = load_enabled_bundled_manifests(
            self._features, root=self._root, app_id=self._app_id
        )
        third_party_manifests = load_enabled_manifests(
            self._features, root=self._root, app_id=self._app_id
        )
        manifests = [*bundled_manifests, *third_party_manifests]
        if not manifests:
            return

        registry = build_registry(manifests, host_keymap=self._keymap)
        self._registry = registry

        bundled_ids = {manifest.id for manifest in bundled_manifests}
        for manifest in manifests:
            entry = installed.get(manifest.id)
            if entry is None:
                continue
            directory = entry.directory
            for command in manifest.contributes.commands:
                self._command_index[command.id] = (manifest, directory)
                if manifest.id in bundled_ids:
                    self._bundled_command_ids.add(command.id)
            if manifest.contributes.document_events:
                self._event_index[manifest.id] = (manifest, directory)
            self._register_feed_auth_providers(manifest, directory)
            self._register_directory_providers(manifest, directory)
            self._register_alert_sources(manifest, directory)
            self._register_pipeline_steps(manifest, directory)
            self._register_location_resolvers(manifest, directory)
            if manifest.contributes.schedule:
                self._start_timers(manifest, directory)

        # Register every contributed command with the app and list it in the
        # Quillins menu (the app's flat backstop, mirroring the editor's).
        for command_id, resolved in registry.commands.items():
            binding = next(
                (h.binding for h in registry.hotkeys if h.command_id == command_id), None
            )
            self._frame.register_command(
                command_id,
                resolved.command.title,
                lambda cid=command_id: self.run_command(cid),
                binding,
            )
            self._frame.add_menu_command(command_id, resolved.command.title)

        # Fire quillin.enabled for any subscriber, matching the editor contract.
        for quillin_id, (manifest, directory) in list(self._event_index.items()):
            self._fire_lifecycle_event("quillin.enabled", quillin_id, manifest, directory)

    def shutdown(self) -> None:
        """Stop timers and forget contributed providers (app teardown)."""

        self._teardown_runtime()

    def _teardown_runtime(self) -> None:
        for timer in self._timers:
            timer.stop()
        self._timers = []
        if self._feed_auth_provider_ids:
            from quill.core.podcasts import feed_auth_registry

            for provider_id in self._feed_auth_provider_ids:
                feed_auth_registry.clear_provider(provider_id)
            self._feed_auth_provider_ids = set()
        if self._directory_provider_ids:
            from quill.core.radio import directory_registry

            for provider_id in self._directory_provider_ids:
                directory_registry.clear_provider(provider_id)
            self._directory_provider_ids = set()
        if self._alert_source_ids:
            from quill.core.weather import alert_source_registry

            for source_id in self._alert_source_ids:
                alert_source_registry.clear_source(source_id)
            self._alert_source_ids = set()
        if self._pipeline_step_ids:
            from quill.core.audio_studio import pipeline_registry

            for step_id in self._pipeline_step_ids:
                pipeline_registry.clear_step(step_id)
            self._pipeline_step_ids = set()
        if self._resolver_ids:
            from quill.apps.beacon import resolver_registry

            for resolver_id in self._resolver_ids:
                resolver_registry.clear_resolver(resolver_id)
            self._resolver_ids = set()

    # -- command execution ---------------------------------------------------
    def run_command(self, command_id: str, context: dict[str, Any] | None = None) -> None:
        """Run a contributed command: snippet inline, handler out-of-process."""

        entry = self._command_index.get(command_id)
        if entry is None:
            self._frame.announce("Quillin command is unavailable.")
            return
        if command_id not in self._bundled_command_ids and not self._third_party_enabled():
            self._frame.announce("Third-party Quillins are disabled in this build.")
            return
        manifest, directory = entry
        command = next((c for c in manifest.contributes.commands if c.id == command_id), None)
        if command is None:
            return
        if command.is_snippet and command.snippet is not None:
            self._run_snippet(command.snippet)
            return
        self._run_handler(manifest, directory, command_id, context)

    def _run_snippet(self, body: str) -> None:
        """Expand a snippet and hand the result to the clipboard (no editor here)."""

        expansion = expand_snippet(body, SnippetContext())
        try:
            self._services.set_clipboard(expansion.text)
        except Exception:  # noqa: BLE001 - fall back to a plain announcement
            self._frame.announce("Quillin snippet ready.")
            return
        self._frame.announce("Quillin snippet copied to the clipboard.")

    def _run_handler(
        self,
        manifest: ExtensionManifest,
        directory: Path,
        command_id: str,
        context: dict[str, Any] | None,
    ) -> None:
        host = self._make_host(manifest, directory)
        try:
            host.start()
            host.load()
            host.invoke(command_id, context or {})
        except Exception as error:  # noqa: BLE001 - surface, never crash the app
            self._frame.announce(f"Quillin error: {error}")
        finally:
            host.close()

    def _make_host(self, manifest: ExtensionManifest, directory: Path) -> ExtensionHost:
        storage = self._storage_data.setdefault(manifest.id, {})
        return ExtensionHost(
            manifest,
            directory,
            self._services,
            consent=self._consent,
            storage=storage,
        )

    # -- events (document/app lifecycle) -------------------------------------
    def fire_event(self, event_name: str, context: dict[str, Any] | None = None) -> None:
        """Fire ``event_name`` to every subscribed Quillin. Non-blocking."""

        payload = dict(context or {})
        for _quillin_id, (manifest, directory) in list(self._event_index.items()):
            for entry in manifest.contributes.document_events:
                if not isinstance(entry, dict) or entry.get("event") != event_name:
                    continue
                handler = entry.get("handler")
                if isinstance(handler, str) and handler:
                    self._run_event_handler_async(manifest, directory, handler, payload)

    def _fire_lifecycle_event(
        self,
        event_name: str,
        quillin_id: str,
        manifest: ExtensionManifest,
        directory: Path,
    ) -> None:
        for entry in manifest.contributes.document_events:
            if not isinstance(entry, dict) or entry.get("event") != event_name:
                continue
            handler = entry.get("handler")
            if isinstance(handler, str) and handler:
                self._run_event_handler_async(manifest, directory, handler, {})

    def _run_event_handler_async(
        self,
        manifest: ExtensionManifest,
        directory: Path,
        handler_name: str,
        context: dict[str, Any],
    ) -> None:
        def _worker() -> None:
            host = self._make_host(manifest, directory)
            try:
                host.start()
                host.load()
                host.invoke_event(handler_name, dict(context))
            except Exception as error:  # noqa: BLE001 - never crash the app
                self._frame.announce(f"Quillin event error: {error}")
            finally:
                host.close()

        thread = threading.Thread(target=_worker, daemon=True)
        thread.start()

    # -- schedule timers -----------------------------------------------------
    def _start_timers(self, manifest: ExtensionManifest, directory: Path) -> None:
        for sched in manifest.contributes.schedule:

            def _tick(m: ExtensionManifest = manifest, d: Path = directory, s: Any = sched) -> None:
                context = {"timer_id": s.id, "interval_seconds": s.interval_seconds}
                self._run_event_handler_async(m, d, s.handler, context)

            timer = _RepeatingTimer(sched.interval_seconds, _tick)
            timer.start()
            self._timers.append(timer)

    # -- host-mediated provider handler (shared) -----------------------------
    def _invoke_result_handler(
        self,
        manifest: ExtensionManifest,
        directory: Path,
        handler_name: str,
        context: dict[str, Any],
        result_key: str,
    ) -> str:
        """Run a Quillin provider handler and return its stored result string.

        The shared mechanism behind every host-mediated provider (feed-auth,
        directory, alerts, pipeline, resolver). Synchronous by design -- callers
        run it off the UI thread (a fetch/search/export worker). The out-of-process
        worker discards a handler's return value, so the handler writes its result
        (a plain string, or a JSON blob for structured payloads) to ``result_key``
        in its own storage; the host reads it back here. The handler makes no
        network call of its own, so no egress is introduced.
        """

        storage = self._storage_data.setdefault(manifest.id, {})
        storage.pop(result_key, None)
        host = self._make_host(manifest, directory)
        try:
            host.start()
            host.load()
            host.invoke_event(handler_name, dict(context))
        except Exception:  # noqa: BLE001 - a faulty provider yields no result
            return ""
        finally:
            host.close()
        value = storage.get(result_key, "")
        return value if isinstance(value, str) else ""

    # -- feed-auth providers (podcast.feed.auth) -----------------------------
    def _register_feed_auth_providers(self, manifest: ExtensionManifest, directory: Path) -> None:
        providers = manifest.contributes.feed_auth_providers
        if not providers or not manifest.has_capability(CAP_PODCAST_FEED_AUTH):
            return
        from quill.core.podcasts import feed_auth_registry

        for provider in providers:
            handler_name = provider.handler

            def _handler(
                feed_url: str,
                request_url: str,
                m: ExtensionManifest = manifest,
                d: Path = directory,
                hn: str = handler_name,
            ) -> str:
                return self._invoke_result_handler(
                    m, d, hn, {"feed_url": feed_url, "url": request_url}, FEED_AUTH_RESULT_KEY
                )

            feed_auth_registry.register_provider(provider.id, provider.match_hosts, _handler)
            self._feed_auth_provider_ids.add(provider.id)

    # -- station-directory providers (radio.directory) -----------------------
    def _register_directory_providers(self, manifest: ExtensionManifest, directory: Path) -> None:
        providers = manifest.contributes.directory_providers
        if not providers or not manifest.has_capability(CAP_RADIO_DIRECTORY):
            return
        from quill.core.radio import directory_registry

        for provider in providers:
            handler_name = provider.handler

            def _handler(
                query: str,
                m: ExtensionManifest = manifest,
                d: Path = directory,
                hn: str = handler_name,
            ) -> list[dict[str, str]]:
                raw = self._invoke_result_handler(m, d, hn, {"query": query}, DIRECTORY_RESULT_KEY)
                return _decode_rows(raw)

            directory_registry.register_provider(provider.id, provider.display_name, _handler)
            self._directory_provider_ids.add(provider.id)

    # -- weather alert sources (weather.alerts) ------------------------------
    def _register_alert_sources(self, manifest: ExtensionManifest, directory: Path) -> None:
        sources = manifest.contributes.alert_sources
        if not sources or not manifest.has_capability(CAP_WEATHER_ALERTS):
            return
        from quill.core.weather import alert_source_registry

        for source in sources:
            handler_name = source.handler

            def _handler(
                m: ExtensionManifest = manifest,
                d: Path = directory,
                hn: str = handler_name,
            ) -> list[dict[str, str]]:
                raw = self._invoke_result_handler(m, d, hn, {}, ALERTS_RESULT_KEY)
                return _decode_rows(raw)

            alert_source_registry.register_source(source.id, _handler, source.interval_seconds)
            self._alert_source_ids.add(source.id)

    # -- audio-processing steps (studio.pipeline) ----------------------------
    def _register_pipeline_steps(self, manifest: ExtensionManifest, directory: Path) -> None:
        steps = manifest.contributes.pipeline_steps
        if not steps or not manifest.has_capability(CAP_STUDIO_PIPELINE):
            return
        from quill.core.audio_studio import pipeline_registry

        for step in steps:
            handler_name = step.handler

            def _handler(
                stage: str,
                m: ExtensionManifest = manifest,
                d: Path = directory,
                hn: str = handler_name,
            ) -> str:
                return self._invoke_result_handler(m, d, hn, {"stage": stage}, PIPELINE_RESULT_KEY)

            pipeline_registry.register_step(step.id, step.stage, step.display_name, _handler)
            self._pipeline_step_ids.add(step.id)

    # -- location resolvers (beacon.resolver) --------------------------------
    def _register_location_resolvers(self, manifest: ExtensionManifest, directory: Path) -> None:
        resolvers = manifest.contributes.location_resolvers
        if not resolvers or not manifest.has_capability(CAP_BEACON_RESOLVER):
            return
        from quill.apps.beacon import resolver_registry

        for resolver in resolvers:
            handler_name = resolver.handler

            def _handler(
                loc: dict[str, Any],
                content: str,
                m: ExtensionManifest = manifest,
                d: Path = directory,
                hn: str = handler_name,
            ) -> dict[str, Any] | None:
                raw = self._invoke_result_handler(
                    m, d, hn, {"loc": loc, "content": content}, RESOLVER_RESULT_KEY
                )
                return _decode_object(raw)

            resolver_registry.register_resolver(resolver.id, resolver.content_types, _handler)
            self._resolver_ids.add(resolver.id)

    # -- helpers -------------------------------------------------------------
    def _third_party_enabled(self) -> bool:
        is_enabled = getattr(self._features, "is_enabled", None)
        if not callable(is_enabled):
            return False
        from quill.plugins import THIRD_PARTY_PLUGINS_FEATURE

        return bool(is_enabled(THIRD_PARTY_PLUGINS_FEATURE))
