from django.urls import path

from . import views

C = "chapters/<str:slug>/<str:key>"

urlpatterns = [
    path("materials/", views.MaterialListView.as_view()),
    path("materials/<str:slug>/", views.MaterialDetailView.as_view()),
    path("materials/<str:slug>/pdf/", views.MaterialPdfView.as_view()),
    path("materials/<str:slug>/outline/", views.MaterialOutlineView.as_view()),
    path("materials/<str:slug>/chapters/build/", views.BuildChaptersView.as_view()),
    path(f"{C}/", views.ChapterDetailView.as_view()),
    path(f"{C}/pdf/", views.ChapterPdfView.as_view()),
    path(f"{C}/files/<path:path>", views.ChapterFileView.as_view()),
    path(f"{C}/figures/", views.FiguresView.as_view()),
]
