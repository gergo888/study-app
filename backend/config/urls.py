from django.urls import include, path

urlpatterns = [
    path("api/auth/", include("apps.core.urls")),
    path("api/", include("apps.materials.urls")),
    path("api/", include("apps.content.urls")),
    path("api/", include("apps.study.urls")),
]
