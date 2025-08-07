from rest_framework import permissions
from rest_framework.permissions import BasePermission


class IsGalleryOwner(BasePermission):
    """갤러리 오너 권한"""
    
    def has_permission(self, request, view):
        return (
            request.user and 
            request.user.is_authenticated and 
            request.user.role == 'owner'
        )


class IsGalleryManager(BasePermission):
    """갤러리 매니저 이상 권한 (오너 + 매니저)"""
    
    def has_permission(self, request, view):
        return (
            request.user and 
            request.user.is_authenticated and 
            request.user.role in ['owner', 'manager']
        )


class IsGalleryStaff(BasePermission):
    """갤러리 직원 이상 권한 (오너 + 매니저 + 직원)"""
    
    def has_permission(self, request, view):
        return (
            request.user and 
            request.user.is_authenticated and 
            request.user.role in ['owner', 'manager', 'staff']
        )


class HasClientManagementPermission(BasePermission):
    """고객 관리 권한"""
    
    def has_permission(self, request, view):
        return (
            request.user and 
            request.user.is_authenticated and 
            (request.user.role == 'owner' or request.user.can_manage_clients)
        )


class HasArtworkManagementPermission(BasePermission):
    """작품 관리 권한"""
    
    def has_permission(self, request, view):
        return (
            request.user and 
            request.user.is_authenticated and 
            (request.user.role == 'owner' or request.user.can_manage_artworks)
        )


class HasDataExportPermission(BasePermission):
    """데이터 내보내기 권한"""
    
    def has_permission(self, request, view):
        return (
            request.user and 
            request.user.is_authenticated and 
            (request.user.role == 'owner' or request.user.can_export_data)
        )


class HasMessageSendPermission(BasePermission):
    """메시지 발송 권한"""
    
    def has_permission(self, request, view):
        return (
            request.user and 
            request.user.is_authenticated and 
            (request.user.role == 'owner' or request.user.can_send_messages)
        )


class HasReportViewPermission(BasePermission):
    """리포트 조회 권한"""
    
    def has_permission(self, request, view):
        return (
            request.user and 
            request.user.is_authenticated and 
            (request.user.role == 'owner' or request.user.can_view_reports)
        )


class HasUserManagementPermission(BasePermission):
    """사용자 관리 권한"""
    
    def has_permission(self, request, view):
        return (
            request.user and 
            request.user.is_authenticated and 
            (request.user.role == 'owner' or request.user.can_manage_users)
        )


class HasGallerySettingsPermission(BasePermission):
    """갤러리 설정 권한"""
    
    def has_permission(self, request, view):
        return (
            request.user and 
            request.user.is_authenticated and 
            (request.user.role == 'owner' or request.user.can_manage_gallery_settings)
        )


class IsSameGallery(BasePermission):
    """같은 갤러리 사용자인지 확인"""
    
    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated
    
    def has_object_permission(self, request, view, obj):
        # obj가 User 객체인 경우
        if hasattr(obj, 'gallery'):
            return request.user.gallery == obj.gallery
        
        # obj가 갤러리와 연관된 다른 모델인 경우
        if hasattr(obj, 'user') and hasattr(obj.user, 'gallery'):
            return request.user.gallery == obj.user.gallery
        
        return False


class IsOwnerOrReadOnly(BasePermission):
    """본인 데이터만 수정 가능, 같은 갤러리는 읽기 가능"""
    
    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated
    
    def has_object_permission(self, request, view, obj):
        # 읽기 권한: 같은 갤러리
        if request.method in permissions.SAFE_METHODS:
            if hasattr(obj, 'gallery'):
                return request.user.gallery == obj.gallery
            if hasattr(obj, 'user') and hasattr(obj.user, 'gallery'):
                return request.user.gallery == obj.user.gallery
        
        # 쓰기 권한: 본인 데이터만
        if hasattr(obj, 'user'):
            return obj.user == request.user
        
        return obj == request.user


class ReadOnlyOrManagementPermission(BasePermission):
    """읽기는 모든 인증 사용자, 쓰기는 관리 권한 필요"""
    
    def __init__(self, management_permission_name):
        self.management_permission_name = management_permission_name
    
    def has_permission(self, request, view):
        if not (request.user and request.user.is_authenticated):
            return False
        
        # 읽기 권한
        if request.method in permissions.SAFE_METHODS:
            return True
        
        # 쓰기 권한
        return (
            request.user.role == 'owner' or 
            request.user.has_permission(self.management_permission_name)
        )


class ActiveGalleryRequired(BasePermission):
    """활성 갤러리 소속 사용자만 허용"""
    
    def has_permission(self, request, view):
        return (
            request.user and 
            request.user.is_authenticated and 
            request.user.gallery.is_active and
            request.user.gallery.is_subscription_active
        )


class AccountNotLocked(BasePermission):
    """계정 잠금되지 않은 사용자만 허용"""
    
    def has_permission(self, request, view):
        return (
            request.user and 
            request.user.is_authenticated and 
            not request.user.is_account_locked()
        )


# 복합 권한 클래스들
class ClientManagementPermission(BasePermission):
    """고객 관리 복합 권한: 활성 갤러리 + 고객 관리 권한"""
    
    def has_permission(self, request, view):
        if not (request.user and request.user.is_authenticated):
            return False
        
        # 기본 조건: 활성 갤러리, 계정 잠금 없음
        if (not request.user.gallery.is_active or 
            not request.user.gallery.is_subscription_active or
            request.user.is_account_locked()):
            return False
        
        # 고객 관리 권한
        return (
            request.user.role == 'owner' or 
            request.user.can_manage_clients
        )


class ArtworkManagementPermission(BasePermission):
    """작품 관리 복합 권한: 활성 갤러리 + 작품 관리 권한"""
    
    def has_permission(self, request, view):
        if not (request.user and request.user.is_authenticated):
            return False
        
        # 기본 조건: 활성 갤러리, 계정 잠금 없음
        if (not request.user.gallery.is_active or 
            not request.user.gallery.is_subscription_active or
            request.user.is_account_locked()):
            return False
        
        # 작품 관리 권한
        return (
            request.user.role == 'owner' or 
            request.user.can_manage_artworks
        )


class DataExportPermission(BasePermission):
    """데이터 내보내기 복합 권한"""
    
    def has_permission(self, request, view):
        if not (request.user and request.user.is_authenticated):
            return False
        
        # 기본 조건: 활성 갤러리, 계정 잠금 없음
        if (not request.user.gallery.is_active or 
            not request.user.gallery.is_subscription_active or
            request.user.is_account_locked()):
            return False
        
        # 데이터 내보내기 권한
        return (
            request.user.role == 'owner' or 
            request.user.can_export_data
        )


class UserManagementPermission(BasePermission):
    """사용자 관리 복합 권한"""
    
    def has_permission(self, request, view):
        if not (request.user and request.user.is_authenticated):
            return False
        
        # 기본 조건: 활성 갤러리, 계정 잠금 없음
        if (not request.user.gallery.is_active or 
            not request.user.gallery.is_subscription_active or
            request.user.is_account_locked()):
            return False
        
        # 사용자 관리 권한
        return (
            request.user.role == 'owner' or 
            request.user.can_manage_users
        )


# 권한 데코레이터 함수들
def require_permission(permission_name):
    """특정 권한 필요 데코레이터"""
    def decorator(view_func):
        def wrapper(self, request, *args, **kwargs):
            if not request.user.has_permission(permission_name):
                from rest_framework.response import Response
                from rest_framework import status
                return Response(
                    {'error': f'{permission_name} 권한이 필요합니다.'}, 
                    status=status.HTTP_403_FORBIDDEN
                )
            return view_func(self, request, *args, **kwargs)
        return wrapper
    return decorator


def require_role(required_roles):
    """특정 역할 필요 데코레이터"""
    if isinstance(required_roles, str):
        required_roles = [required_roles]
    
    def decorator(view_func):
        def wrapper(self, request, *args, **kwargs):
            if request.user.role not in required_roles:
                from rest_framework.response import Response
                from rest_framework import status
                return Response(
                    {'error': f'{", ".join(required_roles)} 역할이 필요합니다.'}, 
                    status=status.HTTP_403_FORBIDDEN
                )
            return view_func(self, request, *args, **kwargs)
        return wrapper
    return decorator


def require_active_gallery(view_func):
    """활성 갤러리 필요 데코레이터"""
    def wrapper(self, request, *args, **kwargs):
        if not request.user.gallery.is_active:
            from rest_framework.response import Response
            from rest_framework import status
            return Response(
                {'error': '소속 갤러리가 비활성 상태입니다.'}, 
                status=status.HTTP_403_FORBIDDEN
            )
        if not request.user.gallery.is_subscription_active:
            from rest_framework.response import Response
            from rest_framework import status
            return Response(
                {'error': '갤러리 구독이 만료되었습니다.'}, 
                status=status.HTTP_403_FORBIDDEN
            )
        return view_func(self, request, *args, **kwargs)
    return wrapper


# 권한 체크 헬퍼 함수들
def check_gallery_permission(user, target_gallery):
    """갤러리 접근 권한 확인"""
    return user.gallery == target_gallery


def check_user_management_permission(user, target_user):
    """사용자 관리 권한 확인"""
    # 같은 갤러리여야 함
    if user.gallery != target_user.gallery:
        return False
    
    # 본인은 항상 수정 가능
    if user == target_user:
        return True
    
    # 오너는 모든 사용자 관리 가능
    if user.role == 'owner':
        return True
    
    # 사용자 관리 권한이 있어야 함
    if not user.can_manage_users:
        return False
    
    # 매니저는 직원, 조회자, 인턴만 관리 가능
    if user.role == 'manager':
        return target_user.role in ['staff', 'viewer', 'intern']
    
    return False


def get_user_accessible_galleries(user):
    """사용자가 접근 가능한 갤러리 목록"""
    # 일반적으로는 자신의 갤러리만
    return [user.gallery]


def get_permission_hierarchy():
    """권한 계층 구조 반환"""
    return {
        'owner': ['owner'],
        'manager': ['owner', 'manager'],
        'staff': ['owner', 'manager', 'staff'],
        'viewer': ['owner', 'manager', 'staff', 'viewer'],
        'intern': ['owner', 'manager', 'staff', 'viewer', 'intern']
    }