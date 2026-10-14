"""Safe provider errors used to distinguish failed calls from empty results."""


class ProviderConfigurationError(RuntimeError):
    """Raised when an explicitly selected provider is not configured."""


class ProviderRequestError(RuntimeError):
    """Raised when a configured provider call fails."""

    def __init__(self, provider: str, error_type: str) -> None:
        self.provider = provider
        self.error_type = error_type
        super().__init__(f"{provider} request failed ({error_type})")


def safe_provider_error(provider: str, error: Exception) -> ProviderRequestError:
    """Create an error suitable for run records without provider response data."""
    if isinstance(error, ProviderRequestError):
        return error
    return ProviderRequestError(provider, type(error).__name__)
