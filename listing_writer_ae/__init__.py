"""listing-writer-ae: bilingual (Arabic/English) AI property listing writer for Dubai with a claims checker."""

__version__ = "0.1.0"

from .checks import Finding, check_text  # noqa: E402
from .generate import Listing, write_listing  # noqa: E402
from .schema import Property, PropertyError  # noqa: E402

__all__ = ["Finding", "Listing", "Property", "PropertyError", "check_text", "write_listing", "__version__"]
