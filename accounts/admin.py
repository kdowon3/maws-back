from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils.html import format_html
from .models import Gallery, User, LoginHistory


@admin.register(Gallery)
class GalleryAdmin(admin.ModelAdmin):
    """갤러리 관리자"""
    list_display = ['name', 'business_number', 'phone', 'user_count', 'is_active', 'subscription_status', 'created_at']
    list_filter = ['is_active', 'created_at']
    search_fields = ['name', 'business_number', 'email']
    readonly_fields = ['registration_code', 'created_at', 'updated_at', 'user_count']
    
    actions = ['delete_gallery_with_related']
    
    def delete_gallery_with_related(self, request, queryset):
        """관련 객체들과 함께 갤러리 삭제"""
        deleted_count = 0
        for gallery in queryset:
            try:
                # 1. 관련된 LoginHistory 삭제
                login_histories = LoginHistory.objects.filter(user__gallery=gallery)
                login_histories.delete()
                
                # 2. 관련된 User 삭제
                users = gallery.users.all()
                users.delete()
                
                # 3. 갤러리 삭제
                gallery.delete()
                deleted_count += 1
                
            except Exception as e:
                self.message_user(request, f"갤러리 '{gallery.name}' 삭제 실패: {str(e)}", level='ERROR')
        
        if deleted_count > 0:
            self.message_user(request, f"{deleted_count}개의 갤러리가 관련 객체들과 함께 삭제되었습니다.")
    
    delete_gallery_with_related.short_description = "선택된 갤러리들을 관련 객체들과 함께 삭제"
    
    fieldsets = (
        ('기본 정보', {
            'fields': ('name', 'business_number', 'address', 'phone', 'email', 'website')
        }),
        ('가입 관리', {
            'fields': ('registration_code', 'max_users', 'user_count')
        }),
        ('상태 관리', {
            'fields': ('is_active', 'subscription_expires')
        }),
        ('메타 정보', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def user_count(self, obj):
        """현재 사용자 수"""
        count = obj.get_user_count()
        return f"{count}/{obj.max_users}"
    user_count.short_description = "사용자 수"
    
    def subscription_status(self, obj):
        """구독 상태"""
        if obj.is_subscription_active:
            return format_html('<span style="color: green;">활성</span>')
        else:
            return format_html('<span style="color: red;">만료</span>')
    subscription_status.short_description = "구독 상태"

    def has_add_permission(self, request):
        return request.user.is_superuser or super().has_add_permission(request)
    def has_change_permission(self, request, obj=None):
        return request.user.is_superuser or super().has_change_permission(request, obj)
    def has_delete_permission(self, request, obj=None):
        return request.user.is_superuser or super().has_delete_permission(request, obj)


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    """사용자 관리자"""
    list_display = ['username', 'get_full_name', 'email', 'gallery', 'role', 'is_active', 'last_login']
    list_filter = ['role', 'is_active', 'gallery', 'created_at']
    search_fields = ['username', 'first_name', 'last_name', 'email']
    ordering = ['gallery', 'username']
    
    fieldsets = (
        ('기본 정보', {
            'fields': ('username', 'password', 'email', 'first_name', 'last_name')
        }),
        ('갤러리 정보', {
            'fields': ('gallery', 'role')
        }),
        ('연락처', {
            'fields': ('phone', 'emergency_contact')
        }),
        ('권한 설정', {
            'fields': (
                'can_manage_clients', 'can_manage_artworks', 'can_export_data',
                'can_send_messages', 'can_view_reports', 'can_manage_users',
                'can_manage_gallery_settings'
            ),
            'classes': ('collapse',)
        }),
        ('개인 설정', {
            'fields': ('timezone_setting', 'language', 'theme_preference'),
            'classes': ('collapse',)
        }),
        ('보안 정보', {
            'fields': ('last_login_ip', 'failed_login_attempts', 'account_locked_until', 'password_changed_at'),
            'classes': ('collapse',)
        }),
        ('시스템 권한', {
            'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions'),
            'classes': ('collapse',)
        }),
        ('메타 정보', {
            'fields': ('last_login', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    readonly_fields = ['last_login_ip', 'failed_login_attempts', 'account_locked_until', 
                      'password_changed_at', 'last_login', 'created_at', 'updated_at']
    
    def get_full_name(self, obj):
        """전체 이름"""
        return obj.get_full_name() or obj.username
    get_full_name.short_description = "이름"
    
    def get_queryset(self, request):
        """쿼리셋 최적화"""
        return super().get_queryset(request).select_related('gallery')

    def has_add_permission(self, request):
        return request.user.is_superuser or super().has_add_permission(request)
    def has_change_permission(self, request, obj=None):
        return request.user.is_superuser or super().has_change_permission(request, obj)
    def has_delete_permission(self, request, obj=None):
        return request.user.is_superuser or super().has_delete_permission(request, obj)


@admin.register(LoginHistory)
class LoginHistoryAdmin(admin.ModelAdmin):
    """로그인 이력 관리자"""
    list_display = ['user', 'ip_address', 'device_type', 'browser', 'login_time', 'session_status', 'session_duration_display']
    list_filter = ['device_type', 'login_time', 'user__gallery']
    search_fields = ['user__username', 'ip_address', 'browser']
    readonly_fields = ['user', 'ip_address', 'user_agent', 'login_time', 'logout_time', 
                      'session_duration', 'device_type', 'browser', 'os']
    date_hierarchy = 'login_time'
    ordering = ['-login_time']
    
    fieldsets = (
        ('사용자 정보', {
            'fields': ('user',)
        }),
        ('접속 정보', {
            'fields': ('ip_address', 'login_time', 'logout_time', 'session_duration')
        }),
        ('기기 정보', {
            'fields': ('device_type', 'browser', 'os', 'user_agent'),
            'classes': ('collapse',)
        }),
    )
    
    def session_status(self, obj):
        """세션 상태"""
        if obj.is_active_session():
            return format_html('<span style="color: green;">활성</span>')
        else:
            return format_html('<span style="color: gray;">종료</span>')
    session_status.short_description = "세션 상태"
    
    def session_duration_display(self, obj):
        """세션 지속 시간"""
        return obj.get_session_duration_display()
    session_duration_display.short_description = "지속 시간"
    
    def get_queryset(self, request):
        """쿼리셋 최적화"""
        return super().get_queryset(request).select_related('user', 'user__gallery')
    
    def has_add_permission(self, request):
        return request.user.is_superuser or super().has_add_permission(request)
    def has_change_permission(self, request, obj=None):
        return request.user.is_superuser or super().has_change_permission(request, obj)
    def has_delete_permission(self, request, obj=None):
        return request.user.is_superuser or super().has_delete_permission(request, obj)
    
    actions = ['delete_old_login_history']
    
    def delete_old_login_history(self, request, queryset):
        """오래된 로그인 이력 삭제"""
        from django.utils import timezone
        from datetime import timedelta
        
        # 30일 이상 된 로그인 이력 삭제
        cutoff_date = timezone.now() - timedelta(days=30)
        old_records = queryset.filter(login_time__lt=cutoff_date)
        deleted_count = old_records.count()
        old_records.delete()
        
        self.message_user(request, f"{deleted_count}개의 오래된 로그인 이력이 삭제되었습니다.")
    
    delete_old_login_history.short_description = "선택된 오래된 로그인 이력 삭제"


# Admin 사이트 커스터마이징
admin.site.site_header = "MAWS 관리자"
admin.site.site_title = "MAWS Admin"
admin.site.index_title = "갤러리 관리 시스템"
