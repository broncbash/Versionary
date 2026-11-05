"""Feature switches for legacy agent APIs.

Legacy behavior is unchanged unless the explicit settings runtime gate is set.
When it is set, validated staged settings can only RESTRICT the legacy
environment switches; they cannot enable a feature on their own.

Enrollment v2 remains isolated and is not controlled by this module.
"""
import os

from runtime_configuration import effective_flags


def _enabled(name: str) -> bool:
    return os.environ.get(name, "").strip().lower() == "true"


def registration_enabled() -> bool:
    if _enabled("ARBY_SETTINGS_RUNTIME_ENABLED"):
        return effective_flags()["registration_enabled"]
    return _enabled("ARBY_AGENT_REGISTRATION_ENABLED")


def reporting_enabled() -> bool:
    if _enabled("ARBY_SETTINGS_RUNTIME_ENABLED"):
        return effective_flags()["reporting_enabled"]
    return _enabled("ARBY_AGENT_REPORTING_ENABLED")
