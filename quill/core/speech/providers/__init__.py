"""Speech-to-text provider implementations (#617).

Each provider is imported lazily (only when activated) so an uninstalled optional
engine never affects QUILL startup or other providers.
"""
