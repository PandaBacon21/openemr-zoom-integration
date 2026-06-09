"""Epic-ZCC CTI middleware constants.

Hardcoded across all Zoomly deployments so route registration, URL builders,
and the React config UI agree on a single source of truth.
"""

EPIC_PATH_SLUG = "interconnect-amcurprd-oauth"

EPIC_KEY_VERSION = "1"

EPIC_DEFAULT_SCOPES = "Patient.read Patient.search"

EPIC_TOKEN_TTL_SECONDS = 3600

EPIC_JTI_REPLAY_TTL_SECONDS = 300

EPIC_JWKS_CACHE_TTL_SECONDS = 600

EPIC_INBOUND_JWT_ALGS = ("RS384", "ES384")

EPIC_JKU_HOST_ALLOWLIST = ("zoom.us", "zoom.com")
