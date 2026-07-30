from prometheus_client import CollectorRegistry, Counter, Gauge, Histogram

REGISTRY = CollectorRegistry()

# Authentication raw metrics
AUTH_REQUESTS = Counter(
    "auth_requests",
    "Total authentication requests.",
    ["client_type"],
    registry=REGISTRY,
)
AUTH_SUCCESS = Counter(
    "auth_success",
    "Total successful authentication requests.",
    ["client_type"],
    registry=REGISTRY,
)
AUTH_FAILED = Counter(
    "auth_failed",
    "Total failed authentication requests.",
    ["client_type", "reason"],
    registry=REGISTRY,
)
AUTH_DURATION = Histogram(
    "auth_request_duration_seconds",
    "Authentication request duration in seconds.",
    ["result", "client_type"],
    buckets=(0.025, 0.05, 0.075, 0.1, 0.15, 0.2, 0.3, 0.45, 0.5, 0.7, 1, 2, 5),
    registry=REGISTRY,
)

# OTP raw metrics
OTP_SEND = Counter(
    "otp_send",
    "Total OTP delivery attempts.",
    ["provider", "channel"],
    registry=REGISTRY,
)
OTP_DELIVERY_SUCCESS = Counter(
    "otp_delivery_success",
    "Total successfully delivered OTP messages.",
    ["provider", "channel"],
    registry=REGISTRY,
)
OTP_DELIVERY_FAILED = Counter(
    "otp_delivery_failed",
    "Total failed OTP deliveries.",
    ["provider", "channel", "reason"],
    registry=REGISTRY,
)
OTP_VERIFY = Counter(
    "otp_verify",
    "Total OTP verification attempts.",
    ["channel"],
    registry=REGISTRY,
)
OTP_VERIFY_SUCCESS = Counter(
    "otp_verify_success",
    "Total successful OTP verifications.",
    ["channel"],
    registry=REGISTRY,
)
OTP_VERIFY_FAILED = Counter(
    "otp_verify_failed",
    "Total failed OTP verifications.",
    ["channel", "reason"],
    registry=REGISTRY,
)

# Token raw metrics
TOKEN_REQUEST = Counter(
    "token_request",
    "Total token requests.",
    ["token_type", "grant_type"],
    registry=REGISTRY,
)
TOKEN_ISSUE = Counter(
    "token_issue",
    "Total successfully issued tokens.",
    ["token_type", "grant_type"],
    registry=REGISTRY,
)
TOKEN_FAILED = Counter(
    "token_failed",
    "Total failed token requests.",
    ["token_type", "grant_type", "reason"],
    registry=REGISTRY,
)
TOKEN_DURATION = Histogram(
    "token_request_duration_seconds",
    "Token request duration in seconds.",
    ["token_type", "grant_type", "result"],
    buckets=(0.01, 0.025, 0.05, 0.1, 0.2, 0.3, 0.5, 0.7, 1, 2, 5),
    registry=REGISTRY,
)

# Platform raw metrics
HTTP_REQUESTS = Counter(
    "http_requests",
    "Total platform HTTP requests.",
    ["service", "endpoint", "method", "critical"],
    registry=REGISTRY,
)
HTTP_REQUESTS_5XX = Counter(
    "http_requests_5xx",
    "Total platform HTTP requests returning a 5xx response.",
    ["service", "endpoint", "method", "critical", "status_code"],
    registry=REGISTRY,
)
HTTP_DURATION = Histogram(
    "http_request_duration_seconds",
    "Platform HTTP request duration in seconds.",
    ["service", "endpoint", "method"],
    buckets=(0.025, 0.05, 0.1, 0.2, 0.3, 0.5, 0.7, 1, 2, 5),
    registry=REGISTRY,
)

# Supporting raw operational metrics
AUTHORIZATION_DECISIONS = Counter(
    "authorization_decisions",
    "Total authorization policy decisions.",
    ["resource", "decision", "reason"],
    registry=REGISTRY,
)
APPLICATION_ERRORS = Counter(
    "application_errors",
    "Total classified application errors.",
    ["service", "error_type", "severity"],
    registry=REGISTRY,
)
DATABASE_QUERIES = Counter(
    "database_queries",
    "Total database queries.",
    ["database", "operation", "result"],
    registry=REGISTRY,
)
DATABASE_QUERY_DURATION = Histogram(
    "database_query_duration_seconds",
    "Database query duration in seconds.",
    ["database", "operation", "result"],
    buckets=(0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1, 2, 5),
    registry=REGISTRY,
)
OTP_QUEUE_SIZE = Gauge(
    "otp_queue_size",
    "Number of OTP messages waiting for delivery.",
    registry=REGISTRY,
)
OTP_PROVIDER_STATUS = Gauge(
    "otp_provider_status",
    "OTP provider status (1=up, 0=down).",
    ["provider"],
    registry=REGISTRY,
)
SERVICE_HEALTH = Gauge(
    "service_health",
    "Service health (1=healthy, 0=unhealthy).",
    ["service"],
    registry=REGISTRY,
)
INFRASTRUCTURE_CPU_USAGE = Gauge(
    "infrastructure_cpu_usage_ratio",
    "CPU usage ratio for a simulated node.",
    ["node"],
    registry=REGISTRY,
)
INFRASTRUCTURE_MEMORY_USAGE = Gauge(
    "infrastructure_memory_usage_ratio",
    "Memory usage ratio for a simulated node.",
    ["node"],
    registry=REGISTRY,
)
POD_READY = Gauge(
    "pod_ready",
    "Pod readiness (1=ready, 0=not ready).",
    ["service", "pod"],
    registry=REGISTRY,
)
DATABASE_CONNECTIONS = Gauge(
    "database_connections",
    "Current database connections by state.",
    ["database", "state"],
    registry=REGISTRY,
)
DATABASE_MAX_CONNECTIONS = Gauge(
    "database_max_connections",
    "Configured maximum database connections.",
    ["database"],
    registry=REGISTRY,
)
SIMULATION_TPS = Gauge(
    "simulation_current_tps",
    "Current generated authentication traffic rate.",
    ["profile"],
    registry=REGISTRY,
)
SIMULATION_EVENT_ACTIVE = Gauge(
    "simulation_event_active",
    "Whether a scheduled simulation event is active.",
    ["event"],
    registry=REGISTRY,
)
