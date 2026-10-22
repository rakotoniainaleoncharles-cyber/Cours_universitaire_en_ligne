from django.urls import path

from .views import EnrollmentDetailView, EnrollmentListCreateView

urlpatterns = [
    path('enrollments/', EnrollmentListCreateView.as_view(), name='enrollment-list'),
    path('enrollments/<int:pk>/', EnrollmentDetailView.as_view(), name='enrollment-detail'),
]
