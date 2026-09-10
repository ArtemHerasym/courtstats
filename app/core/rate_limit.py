from slowapi import Limiter
from slowapi.util import get_remote_address


# Production must derive the client address from a trusted reverse proxy.
# Do not trust arbitrary forwarded-for headers at the application boundary.
limiter = Limiter(
    key_func=get_remote_address,
    storage_uri="memory://",
)
