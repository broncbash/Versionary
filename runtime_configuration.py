"""Fail-closed runtime configuration bridge for staged agent capabilities.

A settings file alone cannot activate network features. Activation additionally
requires the existing per-feature environment gate and an explicit runtime gate.
"""
import os
from pathlib import Path
from server_settings import DEFAULT_PATH, SettingsError, load


def _enabled(name):
    return os.environ.get(name, '').strip().lower() == 'true'


def effective_flags(settings_path=None):
    """Return effective flags; invalid configuration fails closed."""
    result = {'registration_enabled': False, 'reporting_enabled': False,
              'runtime_enabled': _enabled('ARBY_SETTINGS_RUNTIME_ENABLED'),
              'configuration_valid': False}
    if not result['runtime_enabled']:
        return result
    try:
        selected_path = Path(settings_path or os.environ.get('ARBY_SETTINGS_PATH', str(DEFAULT_PATH)))
        # Defaults are safe, but an absent file is not a valid activation config.
        if not selected_path.is_file() or selected_path.is_symlink():
            return result
        settings = load(selected_path)
    except (SettingsError, OSError, ValueError):
        return result
    result['configuration_valid'] = True
    if not settings['public_url']:
        return result
    result['registration_enabled'] = bool(settings['enrollment_enabled']) and _enabled('ARBY_AGENT_REGISTRATION_ENABLED')
    result['reporting_enabled'] = bool(settings['reporting_enabled']) and _enabled('ARBY_AGENT_REPORTING_ENABLED')
    return result
