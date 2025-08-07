from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from django.contrib.auth import authenticate
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.utils import timezone
from django.db import transaction
import re
from .models import Gallery, User, LoginHistory, PhoneVerification
import user_agents


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
        
        # 사용자 정보 및 권한 추가
        data.update({
            'user': {
                'id': user.id,
                'username': user.username,
                'email': user.email,
                'first_name': user.first_name,
                'last_name': user.last_name,
                'role': user.role,
                'role_display': user.get_role_display_ko(),
                'gallery': {
                    'id': user.gallery.id,
                    'name': user.gallery.name,
                    'registration_code': user.gallery.registration_code,
                },
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
    
    gallery_name = serializers.CharField(source='gallery.name', read_only=True)
    role_display = serializers.CharField(source='get_role_display_ko', read_only=True)
    full_name = serializers.CharField(source='get_full_name', read_only=True)
    
    class Meta:
        model = User
        fields = [
            'id', 'username', 'email', 'first_name', 'last_name', 'full_name',
            'phone', 'emergency_contact', 'job_title', 'role', 'role_display', 'gallery_name',
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
    """간편 가입 시리얼라이저"""
    
    gallery_name = serializers.CharField(max_length=100, write_only=True, label="갤러리명")
    phone_number = serializers.CharField(max_length=20, write_only=True, label="전화번호")
    firebase_id_token = serializers.CharField(write_only=True, label="Firebase ID 토큰")
    password = serializers.CharField(write_only=True, style={'input_type': 'password'})
    password_confirm = serializers.CharField(write_only=True, style={'input_type': 'password'})
    
    class Meta:
        model = User
        fields = [
            'gallery_name', 'phone_number', 'firebase_id_token',
            'username', 'email', 'password', 'password_confirm',
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
    
    def validate_phone_number(self, value):
        """전화번호 형식 검증"""
        # 번호 정규화
        clean_phone = re.sub(r'[^0-9]', '', value)
        
        # 한국 휴대폰 번호 형식 확인
        if not re.match(r'^01[016789]\d{7,8}$', clean_phone):
            raise serializers.ValidationError('올바른 휴대폰 번호를 입력해주세요.')
        
        # 이미 사용 중인 번호 확인
        if Gallery.objects.filter(verified_phone=clean_phone).exists():
            raise serializers.ValidationError('이미 사용 중인 전화번호입니다.')
        
        return clean_phone
    
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
        from .firebase_auth import verify_firebase_id_token, validate_phone_number_format
        
        # Firebase ID 토큰 검증
        firebase_id_token = attrs.get('firebase_id_token')
        phone_number = attrs.get('phone_number')
        
        if not firebase_id_token:
            raise serializers.ValidationError({
                'firebase_id_token': 'Firebase ID 토큰이 필요합니다.'
            })
        
        # Firebase 토큰 검증
        firebase_user = verify_firebase_id_token(firebase_id_token)
        if not firebase_user:
            raise serializers.ValidationError({
                'firebase_id_token': 'Firebase 토큰이 유효하지 않습니다.'
            })
        
        # Firebase에서 인증된 전화번호와 입력된 전화번호 비교
        firebase_phone = firebase_user.get('phone_number')
        if not firebase_phone:
            raise serializers.ValidationError({
                'firebase_id_token': 'Firebase에서 전화번호를 찾을 수 없습니다.'
            })
        
        # 전화번호 형식 통일 (한국 번호 +82 형식으로)
        def normalize_phone_number(phone):
            # 숫자만 추출
            cleaned = re.sub(r'[^0-9]', '', phone)
            
            # 이미 국가 코드가 있는 경우
            if cleaned.startswith('82'):
                return f"+{cleaned}"
            
            # 010으로 시작하는 한국 번호
            if cleaned.startswith('010'):
                return f"+82{cleaned[1:]}"
            
            # 기본적으로 한국 국가 코드 추가
            return f"+82{cleaned}"
        
        normalized_input_phone = normalize_phone_number(phone_number)
        
        if firebase_phone != normalized_input_phone:
            raise serializers.ValidationError({
                'phone_number': f'Firebase에서 인증된 전화번호({firebase_phone})와 입력된 전화번호({normalized_input_phone})가 일치하지 않습니다.'
            })
        
        # 이미 사용 중인 전화번호 확인
        if Gallery.objects.filter(verified_phone=re.sub(r'[^0-9]', '', firebase_phone)).exists():
            raise serializers.ValidationError({
                'phone_number': '이미 사용 중인 전화번호입니다.'
            })
        
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
        
        # Firebase 사용자 정보를 attrs에 추가
        attrs['firebase_user'] = firebase_user
        attrs['verified_phone'] = re.sub(r'[^0-9]', '', firebase_phone)
        
        return attrs
    
    def create(self, validated_data):
        """갤러리 + 사용자 생성 (Firebase 인증 기반)"""
        gallery_name = validated_data.pop('gallery_name')
        phone_number = validated_data.pop('phone_number')
        firebase_id_token = validated_data.pop('firebase_id_token')
        firebase_user = validated_data.pop('firebase_user')
        verified_phone = validated_data.pop('verified_phone')
        password_confirm = validated_data.pop('password_confirm')
        
        with transaction.atomic():
            # 1. 갤러리 자동 생성 (Firebase 인증된 전화번호 사용)
            gallery = Gallery.objects.create(
                name=gallery_name,
                signup_method='quick',
                verified_phone=verified_phone,
                phone_verified_at=timezone.now(),
                auto_generated=True,
                # 기본값들 (사용자가 나중에 수정 가능)
                address=f"{gallery_name} 주소",  # 임시값
                phone=verified_phone,
                email=validated_data['email']
                # business_number는 나중에 추가 가능
            )
            
            # 2. 사용자 생성 (갤러리 오너로 설정)
            user = User.objects.create_user(
                gallery=gallery,
                role='owner',  # 간편가입자는 자동으로 오너
                phone=verified_phone,
                **validated_data
            )
            
            # 3. Firebase UID를 사용자 정보에 저장 (옵션)
            # user.firebase_uid = firebase_user.get('uid')
            # user.save()
            
            print(f"✅ Firebase 인증으로 갤러리 '{gallery_name}' 생성 완료: {firebase_user.get('uid')}")
            
            return user