"""
Root URL configuration.

Every business route lives under /api/v1/ and is contributed by the module that
owns it. Adding a module means adding one line here -- no cross-module routing
knowledge leaks into this file.
"""

from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView

from jandrishti.shared.api.views import health_view

api_v1 = [
    path("auth/", include("jandrishti.modules.authentication.api.urls")),
    path("users/", include("jandrishti.modules.accounts.api.urls")),
    path("verification/", include("jandrishti.modules.professional_verification.api.urls")),
    path("", include("jandrishti.modules.catalog.api.urls")),
    path("media/", include("jandrishti.modules.media.api.urls")),
    path("problems/", include("jandrishti.modules.problems.api.urls")),
    path("experiences/", include("jandrishti.modules.experience.api.urls")),
    path("comments/", include("jandrishti.modules.comments.api.urls")),
    path("social/", include("jandrishti.modules.social.api.urls")),
    path("clusters/", include("jandrishti.modules.issue_clustering.api.urls")),
    path("projects/", include("jandrishti.modules.projects.api.urls")),
    path("funding/", include("jandrishti.modules.funding.api.urls")),
    path("notifications/", include("jandrishti.modules.notifications.api.urls")),
    path("moderation/", include("jandrishti.modules.moderation.api.urls")),
    path("search/", include("jandrishti.modules.search.api.urls")),
    path("stats/", include("jandrishti.modules.analytics.api.urls")),
    path("government/", include("jandrishti.modules.government.api.urls")),
    path("audit/", include("jandrishti.modules.audit.api.urls")),
]

urlpatterns = [
    path("admin/", admin.site.urls),
    path("health/", health_view, name="health"),
    path("api/v1/", include((api_v1, "v1"), namespace="v1")),
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path(
        "api/docs/",
        SpectacularSwaggerView.as_view(url_name="schema"),
        name="swagger-ui",
    ),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
