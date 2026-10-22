from django.urls import path

from .views import (
    AcademicLevelDetailView,
    AcademicLevelListCreateView,
    AcademicYearDetailView,
    AcademicYearListCreateView,
    FacultyDetailView,
    FacultyListCreateView,
    SubjectDetailView,
    SubjectListCreateView,
)

urlpatterns = [
    path('faculties/', FacultyListCreateView.as_view(), name='faculty-list'),
    path('faculties/<int:pk>/', FacultyDetailView.as_view(), name='faculty-detail'),
    path('levels/', AcademicLevelListCreateView.as_view(), name='academic-level-list'),
    path('levels/<int:pk>/', AcademicLevelDetailView.as_view(), name='academic-level-detail'),
    path('academic-years/', AcademicYearListCreateView.as_view(), name='academic-year-list'),
    path('academic-years/<int:pk>/', AcademicYearDetailView.as_view(), name='academic-year-detail'),
    path('subjects/', SubjectListCreateView.as_view(), name='subject-list'),
    path('subjects/<int:pk>/', SubjectDetailView.as_view(), name='subject-detail'),
]
