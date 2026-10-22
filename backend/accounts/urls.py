from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView

from .views import (
    AdminAuditLogListView,
    AdminDashboardView,
    LoginView,
    LogoutView,
    MeView,
    ResetPasswordView,
    StudentRegistrationView,
    TeacherProfileListView,
    UserAvatarView,
    UserDetailView,
    UserListCreateView,
    UserProfileView,
)

urlpatterns = [
    path('admin/dashboard/', AdminDashboardView.as_view(), name='admin-dashboard'),
    path('admin/audit-logs/', AdminAuditLogListView.as_view(), name='admin-audit-logs'),
    path('auth/login/', LoginView.as_view(), name='login'),
    path('auth/register/', StudentRegistrationView.as_view(), name='student-register'),
    path('auth/me/', MeView.as_view(), name='me'),
    path('auth/profile/', UserProfileView.as_view(), name='user-profile'),
    path('auth/logout/', LogoutView.as_view(), name='logout'),
    path('auth/token/refresh/', TokenRefreshView.as_view(), name='token-refresh'),
    path('users/', UserListCreateView.as_view(), name='user-list'),
    path('users/<int:pk>/', UserDetailView.as_view(), name='user-detail'),
    path('users/<int:pk>/avatar/', UserAvatarView.as_view(), name='user-avatar'),
    path('users/<int:pk>/reset-password/', ResetPasswordView.as_view(), name='reset-password'),
    path('teachers/', TeacherProfileListView.as_view(), name='teacher-list'),
]
