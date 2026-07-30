from prometheus_client import CollectorRegistry, Counter, Gauge, Histogram

REGISTRY = CollectorRegistry()

AUTH_REQUESTS = Counter(
    "vid_auth_requests_total",
    "Total V-ID authentication requests.",
    ["result", "valid", "client_type", "reason"],
    registry=REGISTRY,
)
AUTH_DURATION = Histogram(
    "vid_auth_request_duration_seconds",
    "V-ID authentication request duration in seconds.",
    ["result", "client_type", "reason"],
    buckets=(0.05, 0.1, 0.2, 0.3, 0.5, 0.75, 1, 2, 5),
    registry=REGISTRY,
)
OTP_SEND_ATTEMPTS = Counter(
    "vid_otp_send_attempts_total",
    "Total V-ID OTP delivery attempts.",
    ["result", "provider", "channel", "reason"],
    registry=REGISTRY,
)
OTP_VERIFICATION_ATTEMPTS = Counter(
    "vid_otp_verification_attempts_total",
    "Total V-ID OTP verification attempts.",
    ["result", "valid", "channel", "reason"],
    registry=REGISTRY,
)
TOKEN_REQUESTS = Counter(
    "vid_token_requests_total",
    "Total V-ID token requests.",
    ["result", "valid", "token_type", "grant_type", "reason"],
    registry=REGISTRY,
)
HTTP_REQUESTS = Counter(
    "vid_http_requests_total",
    "Total V-ID platform HTTP requests.",
    ["service", "endpoint", "method", "status_code", "critical"],
    registry=REGISTRY,
)

AUTH_IN_PROGRESS = Gauge(
    "vid_auth_requests_in_progress",
    "Authentication requests currently being processed.",
    registry=REGISTRY,
)
OTP_QUEUE_SIZE = Gauge(
    "vid_otp_queue_size",
    "Number of OTP messages waiting for delivery.",
    registry=REGISTRY,
)
TOKEN_IN_PROGRESS = Gauge(
    "vid_token_requests_in_progress",
    "Token requests currently being processed.",
    registry=REGISTRY,
)
OTP_PROVIDER_STATUS = Gauge(
    "vid_otp_provider_status",
    "OTP provider status (1=up, 0=down).",
    ["provider"],
    registry=REGISTRY,
)
