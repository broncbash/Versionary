"""Feature switches for agent API capabilities."""

import os


def registration_enabled() -> bool:
    return (
        os.environ.get(
            "ARBY_AGENT_REGISTRATION_ENABLED", "false"
        ).strip().lower() == "true"
    )


def reporting_enabled() -> bool:
    return (
        os.environ.get(
            "ARBY_AGENT_REPORTING_ENABLED", "false"
        ).strip().lower() == "true"
    )
