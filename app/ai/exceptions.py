class AIException(Exception):
    """Base exception for AI-related errors."""
    pass


class ProviderException(AIException):
    """Raised when an external AI provider fails (e.g. rate limit, API error)."""
    pass


class ConfigurationException(AIException):
    """Raised when AI provider is not properly configured."""
    pass
