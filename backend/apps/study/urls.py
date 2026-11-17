from django.urls import path

from . import views

urlpatterns = [
    path("practice/session/", views.PracticeSessionView.as_view()),
    path("practice/answer/", views.AnswerView.as_view()),
    path("materials/<str:slug>/plan/", views.PlanView.as_view()),
    path("stats/dashboard/", views.DashboardView.as_view()),
]
