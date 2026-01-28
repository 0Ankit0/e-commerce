from django.urls import include, path, re_path
from drf_yasg import openapi
from drf_yasg.generators import OpenAPISchemaGenerator
from drf_yasg.views import get_schema_view
from rest_framework import permissions

api_info = openapi.Info(
    title="E-Commerce Backend API",
    default_version="v1",
    description="REST API for E-Commerce Backend with Auth, Payments, Subscriptions, Multi-tenancy, CMS & OpenAI",
)


class HttpAndHttpsSchemaGenerator(OpenAPISchemaGenerator):
    def get_schema(self, request=None, public=False):
        schema = super().get_schema(request, public)
        schema.schemes = ["http", "https"]
        return schema


schema_view = get_schema_view(
    api_info,
    public=True,
    generator_class=HttpAndHttpsSchemaGenerator,
    permission_classes=(permissions.AllowAny,),
)

urlpatterns = [
    re_path(r"^swagger(?P<format>\.json|\.yaml)$", schema_view.without_ui(cache_timeout=0), name="schema-json"),
    re_path(r"^doc/", schema_view.with_ui("swagger"), name="schema-swagger-ui"),
    re_path(r"^redoc/", schema_view.with_ui("redoc"), name="schema-redoc"),
    path(
        "api/",
        include(
            [
                # Authentication & User Management (single include to avoid namespace conflicts)
                path("", include("apps.users.urls")),
                # Multi-tenancy
                path("tenants/", include("apps.multitenancy.urls")),
                # Notifications
                path("", include("apps.notifications.urls")),
                # Finances & Subscriptions
                path("finances/", include("apps.finances.urls")),
                # Content Management (Contentful CMS)
                path("content/", include("apps.content.urls")),
                # Integrations (OpenAI)
                path("integrations/", include("apps.integrations.urls")),
            ]
        ),
    ),
]
