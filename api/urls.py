from django.urls import path
from .views import (
    RegisterView,
    LoginView,
    ChangePasswordView,
    IPRegisterList,
    IPRegisterDetail,
    IspList,
    IspDetail,
    MemberList,
    MemberDetail,
    DocumentList,
    DocumentDetail,
    IPChangeRequestListView,
    IPChangeRequestApprovalView,
)
from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', include('api.urls')),  # Includes all routes under /api/
]

urlpatterns = [
    # Auth Endpoints
    path('register/', RegisterView.as_view(), name='register'),
    path('login/', LoginView.as_view(), name='login'),
    
    path('auth/login/', LoginView.as_view(), name='auth-login'),
    path('change-password/', ChangePasswordView.as_view(), name='change-password'),
    path('auth/reset-password/', ChangePasswordView.as_view(), name='reset-password'),

    # IP Register Routes
    path('ip-register/', IPRegisterList.as_view(), name='ip-list'),
    path('ip-register/<str:ip>/', IPRegisterDetail.as_view(), name='ip-detail'),

    # ISP Routes
    path('isp/', IspList.as_view(), name='isp-list'),
    path('isp/<int:pk>/', IspDetail.as_view(), name='isp-detail'),

    # Member Routes
    path('members/', MemberList.as_view(), name='member-list'),
    path('members/<int:pk>/', MemberDetail.as_view(), name='member-detail'),

    # Document & Request Routes
    path('documents/', DocumentList.as_view(), name='document-list'),
    path('documents/<int:pk>/', DocumentDetail.as_view(), name='document-detail'),
    path('ip-requests/', IPChangeRequestListView.as_view(), name='ip-requests'),
    path('ip-requests/<int:pk>/approve/', IPChangeRequestApprovalView.as_view(), name='ip-request-approve'),
]