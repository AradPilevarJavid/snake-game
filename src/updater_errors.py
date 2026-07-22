"""Updater-specific exceptions with user-safe messages."""


class UpdaterError(Exception):
    """Base class for expected updater failures."""


class ConfigurationError(UpdaterError):
    """Launcher configuration is missing or unsafe."""


class ManifestError(UpdaterError):
    """The remote update manifest is invalid."""


class DownloadError(UpdaterError):
    """A payload file could not be downloaded or verified."""


class InstallError(UpdaterError):
    """A staged release could not be installed or activated."""
