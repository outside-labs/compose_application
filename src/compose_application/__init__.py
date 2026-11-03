"""Optional composition of typed storage, APIs and spatial interfaces.

Application assembly APIs are developed through the Cohesion Block A roadmap.
"""

from .service import ProfileError, Service, ServiceConfig, application

__all__ = ["ProfileError", "Service", "ServiceConfig", "application"]
