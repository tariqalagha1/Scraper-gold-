from importlib import import_module

from fastapi import APIRouter

from app.config import settings
v1_router = APIRouter(prefix=settings.API_V1_PREFIX)

_ROUTERS = (
    ("auth", "/auth", ["Authentication"]),
    ("account", "/account", ["Account"]),
    ("user", "/user", ["User Data"]),
    ("api_keys", "/api-keys", ["API Keys"]),
    ("credentials", "/credentials", ["Credentials"]),
    ("jobs", "/jobs", ["Jobs"]),
    ("runs", "/runs", ["Runs"]),
    ("results", "/results", ["Results"]),
    ("exports", "/exports", ["Exports"]),
    ("scraping_types", "/scraping-types", ["Scraping Types"]),
    ("demo", "/demo", ["Demo"]),
    ("system", "/system", ["System"]),
)

for module_name, prefix, tags in _ROUTERS:
    module = import_module(f"app.api.v1.{module_name}")
    v1_router.include_router(module.router, prefix=prefix, tags=tags)
