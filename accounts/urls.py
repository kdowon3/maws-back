from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    CustomTokenObtainPairView,
    CustomTokenRefreshView,
    RegisterView,
    LogoutView,
    UserProfileView,
    PasswordChangeView,
    LoginHistoryView,
    GalleryInfoView,
    GalleryUsersView,
    validate_registration_code,
    check_permission,
    user_dashboard_data,
    force_logout_session,
    send_phone_verification,
    verify_phone_code,
    quick_signup,
    check_firebase_config,
)

app_name = 'accounts'

urlpatterns = [
    # 인증 관련
    path('auth/login/', CustomTokenObtainPairView.as_view(), name='login'),
    path('auth/refresh/', CustomTokenRefreshView.as_view(), name='token_refresh'),
    path('auth/register/', RegisterView.as_view(), name='register'),
    path('auth/logout/', LogoutView.as_view(), name='logout'),
    
    # 간편 가입 관련
    path('auth/quick-signup/', quick_signup, name='quick_signup'),
    path('auth/send-phone-verification/', send_phone_verification, name='send_phone_verification'),
    path('auth/verify-phone-code/', verify_phone_code, name='verify_phone_code'),
    
    # 사용자 관리
    path('profile/', UserProfileView.as_view(), name='user_profile'),
    path('password/change/', PasswordChangeView.as_view(), name='password_change'),
    path('login-history/', LoginHistoryView.as_view(), name='login_history'),
    
    # 갤러리 관련
    path('gallery/info/', GalleryInfoView.as_view(), name='gallery_info'),
    path('gallery/users/', GalleryUsersView.as_view(), name='gallery_users'),
    
    # 유틸리티
    path('validate-code/', validate_registration_code, name='validate_registration_code'),
    path('check-permission/', check_permission, name='check_permission'),
    path('dashboard/', user_dashboard_data, name='user_dashboard_data'),
    path('force-logout/', force_logout_session, name='force_logout_session'),
    path('check-firebase-config/', check_firebase_config, name='check_firebase_config'),
]