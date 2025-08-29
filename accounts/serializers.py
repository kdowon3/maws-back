from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from django.contrib.auth import authenticate
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.utils import timezone
from django.db import transaction
import re
from .models import Gallery, User, LoginHistory, PhoneVerification, EmailVerification
import user_agents
import logging

logger = logging.getLogger(__name__)


class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    """커스텀 JWT 토큰 시리얼라이저"""
    
    def validate(self, attrs):
        """로그인 검증 및 추가 정보 반환"""
        username = attrs.get('username')
        password = attrs.get('password')
        
        # 사용자 인증
        user = authenticate(username=username, password=password)
        
        if not user:
            # 로그인 실패 처리
            try:
                user_obj = User.objects.get(username=username)
                user_obj.failed_login_attempts += 1
                
                # 5회 실패시 계정 잠금 (30분)
                if user_obj.failed_login_attempts >= 5:
                    user_obj.lock_account(minutes=30)
                
                user_obj.save(update_fields=['failed_login_attempts'])
            except User.DoesNotExist:
                pass
            
            raise serializers.ValidationError('로그인 정보가 올바르지 않습니다.')
        
        # 계정 잠금 확인
        if user.is_account_locked():
            raise serializers.ValidationError('계정이 임시 잠금되었습니다. 잠시 후 다시 시도해주세요.')
        
        # 슈퍼유저가 아닌 경우에만 갤러리 상태 확인
        if not user.is_superuser:
            # 갤러리가 없는 경우 체크
            if not hasattr(user, 'gallery') or not user.gallery:
                raise serializers.ValidationError('소속 갤러리가 없습니다.')
                
            # 갤러리 활성 상태 확인
            if not user.gallery.is_active:
                raise serializers.ValidationError('소속 갤러리가 비활성 상태입니다.')
            
            # 구독 상태 확인
            if not user.gallery.is_subscription_active:
                raise serializers.ValidationError('갤러리 구독이 만료되었습니다.')
        
        # 기본 토큰 생성
        data = super().validate(attrs)
        
        # 로그인 성공 처리
        user.failed_login_attempts = 0
        user.last_login = timezone.now()
        
        # IP 주소 저장
        request = self.context.get('request')
        if request:
            ip_address = self.get_client_ip(request)
            user.last_login_ip = ip_address
            user.save(update_fields=['failed_login_attempts', 'last_login', 'last_login_ip'])
            
            # 로그인 이력 생성
            self.create_login_history(user, request, ip_address)
        
        # 사용자 정보 구성
        user_data = {
            'id': user.id,
            'username': user.username,
            'email': user.email,
            'first_name': user.first_name,
            'last_name': user.last_name,
            'role': user.role,
            'role_display': user.get_role_display_ko(),
            'is_superuser': user.is_superuser,
            'is_staff': user.is_staff,
            'permissions': {
                'manage_clients': user.can_manage_clients,
                'manage_artworks': user.can_manage_artworks,
                'export_data': user.can_export_data,
                'send_messages': user.can_send_messages,
                'view_reports': user.can_view_reports,
                'manage_users': user.can_manage_users,
                'manage_gallery_settings': user.can_manage_gallery_settings,
            },
            'settings': {
                'timezone': user.timezone_setting,
                'language': user.language,
                'theme': user.theme_preference,
            }
        }
        
        # 슈퍼유저가 아닌 경우에만 갤러리 정보 추가
        if not user.is_superuser and user.gallery:
            user_data['gallery'] = {
                'id': user.gallery.id,
                'name': user.gallery.name,
                'phone': user.gallery.phone,
                'address': user.gallery.address,
                'email': user.gallery.email,
                'registration_code': user.gallery.registration_code,
            }
        
        # 사용자 정보 및 권한 추가
        data.update({
            'user': user_data
        })
        
        return data
    
    def get_client_ip(self, request):
        """클라이언트 IP 주소 추출"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip
    
    def create_login_history(self, user, request, ip_address):
        """로그인 이력 생성"""
        user_agent_string = request.META.get('HTTP_USER_AGENT', '')
        user_agent = user_agents.parse(user_agent_string)
        
        # 기기 유형 판단
        if user_agent.is_mobile:
            device_type = 'mobile'
        elif user_agent.is_tablet:
            device_type = 'tablet'
        elif user_agent.is_pc:
            device_type = 'desktop'
        else:
            device_type = 'unknown'
        
        LoginHistory.objects.create(
            user=user,
            ip_address=ip_address,
            user_agent=user_agent_string,
            device_type=device_type,
            browser=user_agent.browser.family,
            os=user_agent.os.family
        )


class UserSerializer(serializers.ModelSerializer):
    """사용자 정보 시리얼라이저"""
    
    gallery = serializers.SerializerMethodField()
    gallery_name = serializers.CharField(source='gallery.name', read_only=True)
    role_display = serializers.CharField(source='get_role_display_ko', read_only=True)
    full_name = serializers.CharField(source='get_full_name', read_only=True)
    
    def get_gallery(self, obj):
        """갤러리 정보 반환"""
        if obj.gallery:
            return {
                'id': obj.gallery.id,
                'name': obj.gallery.name,
                'phone': obj.gallery.phone,
                'address': obj.gallery.address,
                'email': obj.gallery.email,
            }
        return None
    
    class Meta:
        model = User
        fields = [
            'id', 'username', 'email', 'first_name', 'last_name', 'full_name',
            'phone', 'emergency_contact', 'job_title', 'role', 'role_display', 
            'gallery', 'gallery_name',
            'can_manage_clients', 'can_manage_artworks', 'can_export_data',
            'can_send_messages', 'can_view_reports', 'can_manage_users',
            'can_manage_gallery_settings', 'timezone_setting', 'language',
            'theme_preference', 'last_login', 'created_at'
        ]
        read_only_fields = ['id', 'username', 'last_login', 'created_at']


class UserRegistrationSerializer(serializers.ModelSerializer):
    """사용자 등록 시리얼라이저"""
    
    registration_code = serializers.CharField(write_only=True)
    password = serializers.CharField(write_only=True, style={'input_type': 'password'})
    password_confirm = serializers.CharField(write_only=True, style={'input_type': 'password'})
    
    class Meta:
        model = User
        fields = [
            'username', 'email', 'password', 'password_confirm',
            'first_name', 'last_name', 'phone', 'emergency_contact', 'job_title',
            'registration_code'
        ]
    
    def validate_registration_code(self, value):
        """가입 코드 검증"""
        try:
            gallery = Gallery.objects.get(registration_code=value, is_active=True)
        except Gallery.DoesNotExist:
            raise serializers.ValidationError('유효하지 않은 가입 코드입니다.')
        
        # 구독 상태 확인
        if not gallery.is_subscription_active:
            raise serializers.ValidationError('해당 갤러리의 구독이 만료되었습니다.')
        
        # 사용자 수 제한 확인
        if not gallery.can_add_user():
            raise serializers.ValidationError('해당 갤러리의 사용자 수가 제한에 도달했습니다.')
        
        return value
    
    def validate_username(self, value):
        """아이디 중복 확인"""
        if User.objects.filter(username=value).exists():
            raise serializers.ValidationError('이미 사용 중인 아이디입니다.')
        return value
    
    def validate_email(self, value):
        """이메일 중복 확인"""
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError('이미 사용 중인 이메일입니다.')
        return value
    
    def validate(self, attrs):
        """전체 데이터 검증"""
        password = attrs.get('password')
        password_confirm = attrs.get('password_confirm')
        
        # 비밀번호 확인
        if password != password_confirm:
            raise serializers.ValidationError({'password_confirm': '비밀번호가 일치하지 않습니다.'})
        
        # Django 비밀번호 검증
        try:
            validate_password(password)
        except ValidationError as e:
            raise serializers.ValidationError({'password': e.messages})
        
        return attrs
    
    def create(self, validated_data):
        """사용자 생성"""
        # 가입 코드로 갤러리 찾기
        registration_code = validated_data.pop('registration_code')
        password_confirm = validated_data.pop('password_confirm')
        
        gallery = Gallery.objects.get(registration_code=registration_code)
        
        # 사용자 생성
        user = User.objects.create_user(
            gallery=gallery,
            role='staff',  # 기본 역할
            **validated_data
        )
        
        return user


class PasswordChangeSerializer(serializers.Serializer):
    """비밀번호 변경 시리얼라이저"""
    
    old_password = serializers.CharField(style={'input_type': 'password'})
    new_password = serializers.CharField(style={'input_type': 'password'})
    new_password_confirm = serializers.CharField(style={'input_type': 'password'})
    
    def validate_old_password(self, value):
        """기존 비밀번호 확인"""
        user = self.context['request'].user
        if not user.check_password(value):
            raise serializers.ValidationError('기존 비밀번호가 올바르지 않습니다.')
        return value
    
    def validate(self, attrs):
        """전체 데이터 검증"""
        new_password = attrs.get('new_password')
        new_password_confirm = attrs.get('new_password_confirm')
        
        # 새 비밀번호 확인
        if new_password != new_password_confirm:
            raise serializers.ValidationError({'new_password_confirm': '새 비밀번호가 일치하지 않습니다.'})
        
        # Django 비밀번호 검증
        try:
            validate_password(new_password, self.context['request'].user)
        except ValidationError as e:
            raise serializers.ValidationError({'new_password': e.messages})
        
        return attrs
    
    def save(self):
        """비밀번호 변경"""
        user = self.context['request'].user
        user.set_password(self.validated_data['new_password'])
        user.password_changed_at = timezone.now()
        user.save(update_fields=['password', 'password_changed_at'])
        return user


class LoginHistorySerializer(serializers.ModelSerializer):
    """로그인 이력 시리얼라이저"""
    
    user_name = serializers.CharField(source='user.get_full_name', read_only=True)
    session_duration_display = serializers.CharField(source='get_session_duration_display', read_only=True)
    is_active = serializers.BooleanField(source='is_active_session', read_only=True)
    
    class Meta:
        model = LoginHistory
        fields = [
            'id', 'user_name', 'ip_address', 'device_type', 'browser', 'os',
            'login_time', 'logout_time', 'session_duration_display', 'is_active'
        ]
        read_only_fields = ['__all__']


class GallerySerializer(serializers.ModelSerializer):
    """갤러리 정보 시리얼라이저"""
    
    user_count = serializers.IntegerField(source='get_user_count', read_only=True)
    subscription_active = serializers.BooleanField(source='is_subscription_active', read_only=True)
    can_add_user = serializers.BooleanField(read_only=True)
    
    class Meta:
        model = Gallery
        fields = [
            'id', 'name', 'business_number', 'address', 'phone', 
            'email', 'website', 'max_users', 'user_count', 
            'subscription_active', 'can_add_user', 'created_at'
        ]
        read_only_fields = [
            'id', 'user_count', 'subscription_active', 
            'can_add_user', 'created_at'
        ]


class QuickSignupSerializer(serializers.ModelSerializer):
    """간편 가입 시리얼라이저 (이메일 인증 기반)"""
    
    gallery_name = serializers.CharField(max_length=100, write_only=True, label="갤러리명")
    password = serializers.CharField(write_only=True, style={'input_type': 'password'})
    password_confirm = serializers.CharField(write_only=True, style={'input_type': 'password'})
    
    class Meta:
        model = User
        fields = [
            'gallery_name', 'username', 'email', 'password', 'password_confirm',
            'first_name', 'last_name', 'job_title'
        ]
    
    def validate_gallery_name(self, value):
        """갤러리명 검증"""
        if len(value.strip()) < 2:
            raise serializers.ValidationError('갤러리명은 2글자 이상이어야 합니다.')
        
        # 갤러리명 중복 확인 (간편 가입용)
        if Gallery.objects.filter(name=value.strip()).exists():
            raise serializers.ValidationError('이미 사용 중인 갤러리명입니다.')
        
        return value.strip()
    
    
    def validate_username(self, value):
        """아이디 중복 확인"""
        if User.objects.filter(username=value).exists():
            raise serializers.ValidationError('이미 사용 중인 아이디입니다.')
        return value
    
    def validate_email(self, value):
        """이메일 중복 확인"""
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError('이미 사용 중인 이메일입니다.')
        return value
    
    def validate(self, attrs):
        """전체 데이터 검증"""
        # 비밀번호 확인
        password = attrs.get('password')
        password_confirm = attrs.get('password_confirm')
        
        if password != password_confirm:
            raise serializers.ValidationError({
                'password_confirm': '비밀번호가 일치하지 않습니다.'
            })
        
        # Django 비밀번호 검증
        try:
            validate_password(password)
        except ValidationError as e:
            raise serializers.ValidationError({'password': e.messages})
        
        return attrs
    
    def create(self, validated_data):
        """갤러리 + 사용자 생성 (이메일 인증 기반)"""
        from .email_utils import send_verification_email
        import os
        
        gallery_name = validated_data.pop('gallery_name')
        password_confirm = validated_data.pop('password_confirm')
        
        # 이메일 인증 스킵 여부 확인
        skip_email_verification = os.environ.get('SKIP_EMAIL_VERIFICATION', 'False').lower() == 'true'
        
        with transaction.atomic():
            # 1. 갤러리 자동 생성
            gallery = Gallery.objects.create(
                name=gallery_name,
                signup_method='quick',
                auto_generated=True,
                # 기본값들 (사용자가 나중에 수정 가능)
                address=f"{gallery_name} 주소",  # 임시값
                phone="000-0000-0000",  # 임시값
                email=validated_data['email']
            )
            
            # 2. 사용자 생성 (갤러리 오너로 설정)
            user = User.objects.create_user(
                gallery=gallery,
                role='owner',  # 간편가입자는 자동으로 오너
                is_active=True if skip_email_verification else False,  # 스킵 옵션에 따라 즉시 활성화
                email_verified=True if skip_email_verification else False,  # 스킵 시 이메일 인증도 완료로 표시
                **validated_data
            )
            
            # 3. 기본 ClientColumn 생성
            from clients.models import ClientColumn
            default_columns = [
                {"header": "고객명", "accessor": "name", "type": "text", "order": 1},
                {"header": "연락처", "accessor": "phone", "type": "text", "order": 2}, 
                {"header": "고객분류", "accessor": "tags", "type": "tag", "order": 3}
            ]
            for col_data in default_columns:
                ClientColumn.objects.create(gallery=gallery, **col_data)
            print(f"[SUCCESS] 갤러리 '{gallery_name}'에 기본 컬럼 {len(default_columns)}개 생성 완료")
            
            # 4. 이메일 인증번호 발송 (스킵 옵션이 False일 때만)
            if not skip_email_verification:
                success, message = send_verification_email(user)
                if not success:
                    # 이메일 발송 실패시 사용자 생성을 롤백하지 않고 로그만 남김
                    logger.warning(f"이메일 발송 실패: {user.email}, {message}")
                print(f"이메일 인증으로 갤러리 '{gallery_name}' 생성 완료: {user.email}")
            else:
                print(f"즉시 활성화로 갤러리 '{gallery_name}' 생성 완료: {user.email}")
            
            return user


class EmailVerificationSerializer(serializers.Serializer):
    """이메일 인증번호 발송 시리얼라이저"""
    
    email = serializers.EmailField()
    
    def validate_email(self, value):
        """이메일 존재 여부 확인"""
        try:
            user = User.objects.get(email=value, is_active=False)
            return value
        except User.DoesNotExist:
            raise serializers.ValidationError('해당 이메일로 가입된 미인증 계정을 찾을 수 없습니다.')


class EmailVerificationConfirmSerializer(serializers.Serializer):
    """이메일 인증번호 확인 시리얼라이저"""
    
    email = serializers.EmailField()
    code = serializers.CharField(max_length=6, min_length=6)
    
    def validate_email(self, value):
        """이메일 존재 여부 확인"""
        try:
            user = User.objects.get(email=value, is_active=False)
            return value
        except User.DoesNotExist:
            raise serializers.ValidationError('해당 이메일로 가입된 미인증 계정을 찾을 수 없습니다.')
    
    def validate_code(self, value):
        """인증번호 형식 확인"""
        if not value.isdigit():
            raise serializers.ValidationError('인증번호는 6자리 숫자여야 합니다.')
        return value


