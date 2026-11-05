from fastapi import Request


def client_ip(request: Request) -> str:
    """Caller IP for rate limits. uvicorn runs with --proxy-headers, so this is the visitor, not the HF proxy."""
    return request.client.host if request.client else "unknown"
