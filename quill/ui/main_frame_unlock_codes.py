"""Help > Redeem Unlock Code... -- lets a trusted tester unlock a
pre-beta, ``locked_off`` feature (see ``quill/core/unlock_codes.py`` and
``quill/core/feature_catalog.py``) with a signed code minted by Jeff via
``python -m quill.tools.mint_unlock_code``. No network call, no bits-acb
dependency: the code's signature is verified entirely offline.
"""

from __future__ import annotations

from quill.core.unlock_codes import RedeemResult, UnlockCodeStore, redeem_code
from quill.ui.unlock_code_dialog import UnlockCodeDialog


class UnlockCodesMixin:
    """Adds Help > Redeem Unlock Code... to ``MainFrame``."""

    def open_redeem_unlock_code_dialog(self) -> None:
        dialog = UnlockCodeDialog(self.frame, announce_cb=self._announce)
        code = dialog.show()
        if code is None:
            return
        result = redeem_code(code)
        self._apply_redeem_result(code, result)

    def _apply_redeem_result(self, code: str, result: RedeemResult) -> None:
        if not result.ok:
            self._announce(f"Unlock code not accepted: {result.error}")
            return
        store = UnlockCodeStore.load()
        store.add(code)
        store.save()
        self.features.unlocked_feature_ids = store.unlocked_feature_ids()
        from quill.core.feature_catalog import FEATURE_DEFINITIONS

        definition = FEATURE_DEFINITIONS.get(result.feature_id or "")
        feature_name = definition.name if definition is not None else (result.feature_id or "")
        self._announce(
            f"Unlocked: {feature_name}. Restart QUILL if the new feature isn't visible yet."
        )

    def _register_unlock_code_commands(self) -> None:
        self.commands.try_register(
            "help.redeem_unlock_code",
            "Help: Redeem Unlock Code...",
            self.open_redeem_unlock_code_dialog,
            self._binding_for("help.redeem_unlock_code"),
            feature_id="core.app",
        )
