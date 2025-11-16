from __future__ import annotations

import os

# Feature flags
DEBUG = os.getenv("DJANGO_DEBUG", "True").lower() in {"1", "true", "yes"}
ACL_ENABLED = os.getenv("ACL_ENABLED", "True").lower() in {"1", "true", "yes"}

# Centralized middleware order
# Recommended order:
#   Cors → Security → Session → Common → Csrf → Authentication → [RequestAccess] → [Log] → Messages → Clickjacking
MIDDLEWARE = [
    # "corsheaders.middleware.CorsMiddleware",  # enable if corsheaders is installed
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "aclcore.middleware.HttpAclMiddleware",
    # RequestAccess (optional) could be placed here
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

if ACL_ENABLED:
    # ACLCore already included; no legacy insertion
    pass

if DEBUG:
    # If django-silk is installed and desired:
    # MIDDLEWARE.insert(0, "silk.middleware.SilkyMiddleware")
    pass


