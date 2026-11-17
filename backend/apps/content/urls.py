from django.urls import path

from . import views

C = "chapters/<str:slug>/<str:key>"

urlpatterns = [
    path(f"{C}/summary/", views.SummaryView.as_view()),
    path(f"{C}/cards/confirm/", views.ConfirmCardView.as_view()),
    path(f"{C}/documents/<str:kind>/", views.RawDocumentView.as_view()),
    path(f"{C}/points/<str:point_key>/check-answer/", views.CheckAnswerView.as_view()),
    path(f"{C}/points/<str:point_key>/activity/", views.PointActivityView.as_view()),
    path(f"{C}/<str:kind>/", views.CardsView.as_view()),  # flashcards | quiz
    path("materials/<str:slug>/notes/", views.NotesView.as_view()),
    path("materials/<str:slug>/notes/<str:note_id>/", views.NoteDetailView.as_view()),
]
