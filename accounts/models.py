from django.db import models
from django.contrib.auth.models import AbstractUser
from django.utils import timezone
from datetime import timedelta
import secrets
import string
import re
import uuid


class Gallery(models.Model):
    """갤러리 정보 관리"""
    
    # 기본 정보
    name = models.CharField(max_length=100, verbose_name="갤러리명")
    business_number = models.CharField(max_length=20, unique=True, verbose_name="사업자등록번호", null=True, blank=True)    
    # 연락처 정보
    address = models.TextField(verbose_name="주소")
    phone = models.CharField(max_length=20, verbose_name="전화번호")
    email = models.EmailField(verbose_name="대표 이메일")
    website = models.URLField(blank=True, verbose_name="웹사이트")
    logo = models.ImageField(upload_to='gallery_logos/', blank=True, null=True, verbose_name="갤러리 로고")
    
    # 가입 관리
    registration_code = models.CharField(max_length=20, unique=True, blank=True, null=True, verbose_name="가입 코드")
    max_users = models.PositiveIntegerField(default=10, verbose_name="최대 사용자 수")
    
    # 가입 방식 및 전화번호 인증
    signup_method = models.CharField(
        max_length=20,
        choices=[
            ('quick', '간편 가입'),
            ('code', '코드 가입'),
            ('invited', '초대 가입'),
        ],
        default='quick',
        verbose_name="가입 방식"
    )
    
    verified_phone = models.CharField(
        max_length=20,
        unique=True,
        null=True,
        blank=True,
        verbose_name="인증된 전화번호"
    )
    phone_verified_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="전화번호 인증 시간"
    )
    
    auto_generated = models.BooleanField(
        default=False,
        verbose_name="자동 생성 갤러리"
    )
    
    # 상태 관리
    is_active = models.BooleanField(default=True, verbose_name="활성 상태")
    subscription_expires = models.DateTimeField(null=True, blank=True, verbose_name="구독 만료일")
    
    # 메타 정보
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "갤러리"
        verbose_name_plural = "갤러리"
        ordering = ['name']
    
    def __str__(self):
        return self.name
    
    @property
    def is_subscription_active(self):
        """구독 활성 상태 확인"""
        if not self.subscription_expires:
            return True
        return timezone.now() < self.subscription_expires
    
    def get_user_count(self):
        """현재 사용자 수"""
        return self.users.filter(is_active=True).count()
    
    def can_add_user(self):
        """새 사용자 추가 가능 여부"""
        return self.get_user_count() < self.max_users
    
    def generate_registration_code(self):
        """등록 코드 자동 생성"""
        while True:
            code = ''.join(secrets.choice(string.ascii_uppercase + string.digits) for _ in range(8))
            if not Gallery.objects.filter(registration_code=code).exists():
                self.registration_code = code
                break
    
    def save(self, *args, **kwargs):
        # 간편 가입시에만 코드 자동 생성 (선택사항)
        if self.signup_method == 'quick' and not self.registration_code:
            self.generate_registration_code()
            self.auto_generated = True
        elif self.signup_method == 'code' and not self.registration_code:
            self.generate_registration_code()
        super().save(*args, **kwargs)


class User(AbstractUser):
    """확장된 사용자 모델"""
    
    # 역할 정의
    ROLE_CHOICES = [
        ('owner', '갤러리 오너'),        # 모든 권한    
        ('manager', '매니저'),          # 관리 권한
        ('staff', '직원'),             # 기본 업무 권한
        ('viewer', '조회자'),          # 읽기 전용
        ('intern', '인턴'),            # 제한적 권한
    ]
    
    # 기본 정보
    gallery = models.ForeignKey(
        Gallery, 
        on_delete=models.CASCADE, 
        verbose_name="소속 갤러리",
        related_name="users",
        null=True,
        blank=True
    )
    role = models.CharField(
        max_length=20, 
        choices=ROLE_CHOICES, 
        default='staff',
        verbose_name="역할"
    )
    
    # 연락처
    phone = models.CharField(max_length=20, blank=True, verbose_name="전화번호")
    emergency_contact = models.CharField(max_length=100, blank=True, verbose_name="비상연락처")
    job_title = models.CharField(max_length=100, blank=True, verbose_name="직책")
    
    # 세부 권한 (역할과 별개의 개별 권한)
    can_manage_clients = models.BooleanField(default=True, verbose_name="고객 관리")
    can_manage_artworks = models.BooleanField(default=True, verbose_name="작품 관리")
    can_export_data = models.BooleanField(default=False, verbose_name="데이터 내보내기")
    can_send_messages = models.BooleanField(default=False, verbose_name="메시지 발송")
    can_view_reports = models.BooleanField(default=False, verbose_name="리포트 조회")
    can_manage_users = models.BooleanField(default=False, verbose_name="사용자 관리")
    can_manage_gallery_settings = models.BooleanField(default=False, verbose_name="갤러리 설정")
    
    # 보안 관련
    last_login_ip = models.GenericIPAddressField(null=True, blank=True, verbose_name="마지막 로그인 IP")
    failed_login_attempts = models.PositiveIntegerField(default=0, verbose_name="로그인 실패 횟수")
    account_locked_until = models.DateTimeField(null=True, blank=True, verbose_name="계정 잠금 해제 시간")
    password_changed_at = models.DateTimeField(auto_now_add=True, verbose_name="비밀번호 변경일")
    
    # 이메일 인증
    email_verified = models.BooleanField(default=False, verbose_name="이메일 인증 여부")
    email_verified_at = models.DateTimeField(null=True, blank=True, verbose_name="이메일 인증 시간")
    
    # 개인 설정
    timezone_setting = models.CharField(max_length=50, default='Asia/Seoul', verbose_name="시간대")
    language = models.CharField(max_length=10, default='ko', verbose_name="언어")
    theme_preference = models.CharField(
        max_length=10, 
        choices=[('light', '라이트'), ('dark', '다크'), ('auto', '자동')],
        default='light',
        verbose_name="테마 설정"
    )
    
    # 메타 정보
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "사용자"
        verbose_name_plural = "사용자"
        unique_together = ['gallery', 'username']  # 갤러리별 고유 사용자명
    
    def __str__(self):
        return f"{self.get_full_name() or self.username} ({self.gallery.name})"
    
    def has_permission(self, permission):
        """권한 체크 메서드"""
        # 오너는 모든 권한
        if self.role == 'owner':
            return True
        
        # 개별 권한 체크
        permission_map = {
            'manage_clients': self.can_manage_clients,
            'manage_artworks': self.can_manage_artworks,
            'export_data': self.can_export_data,
            'send_messages': self.can_send_messages,
            'view_reports': self.can_view_reports,
            'manage_users': self.can_manage_users,
            'manage_gallery_settings': self.can_manage_gallery_settings,
        }
        
        return permission_map.get(permission, False)
    
    def get_role_display_ko(self):
        """한국어 역할명 반환"""
        return dict(self.ROLE_CHOICES).get(self.role, self.role)
    
    def is_account_locked(self):
        """계정 잠금 상태 확인"""
        if not self.account_locked_until:
            return False
        return timezone.now() < self.account_locked_until
    
    def lock_account(self, minutes=30):
        """계정 임시 잠금"""
        self.account_locked_until = timezone.now() + timedelta(minutes=minutes)
        self.save(update_fields=['account_locked_until'])
    
    def unlock_account(self):
        """계정 잠금 해제"""
        self.account_locked_until = None
        self.failed_login_attempts = 0
        self.save(update_fields=['account_locked_until', 'failed_login_attempts'])


class LoginHistory(models.Model):
    """로그인 이력 관리"""
    
    user = models.ForeignKey(
        User, 
        on_delete=models.CASCADE, 
        related_name='login_history',
        verbose_name="사용자"
    )
    ip_address = models.GenericIPAddressField(verbose_name="IP 주소")
    user_agent = models.TextField(verbose_name="User Agent")
    login_time = models.DateTimeField(auto_now_add=True, verbose_name="로그인 시간")
    logout_time = models.DateTimeField(null=True, blank=True, verbose_name="로그아웃 시간")
    session_duration = models.DurationField(null=True, blank=True, verbose_name="세션 지속 시간")
    
    # 추가 정보
    device_type = models.CharField(
        max_length=20,
        choices=[
            ('desktop', '데스크톱'),
            ('mobile', '모바일'),
            ('tablet', '태블릿'),
            ('unknown', '알 수 없음'),
        ],
        default='unknown',
        verbose_name="기기 유형"
    )
    browser = models.CharField(max_length=50, blank=True, verbose_name="브라우저")
    os = models.CharField(max_length=50, blank=True, verbose_name="운영체제")
    
    class Meta:
        verbose_name = "로그인 이력"
        verbose_name_plural = "로그인 이력"
        ordering = ['-login_time']
        indexes = [
            models.Index(fields=['user', '-login_time']),
            models.Index(fields=['ip_address']),
            models.Index(fields=['login_time']),
        ]
    
    def __str__(self):
        return f"{self.user.username} - {self.login_time.strftime('%Y-%m-%d %H:%M:%S')}"
    
    def get_session_duration_display(self):
        """세션 지속 시간을 읽기 쉬운 형태로 반환"""
        if not self.session_duration:
            return "진행 중"
        
        total_seconds = int(self.session_duration.total_seconds())
        hours = total_seconds // 3600
        minutes = (total_seconds % 3600) // 60
        seconds = total_seconds % 60
        
        if hours > 0:
            return f"{hours}시간 {minutes}분"
        elif minutes > 0:
            return f"{minutes}분 {seconds}초"
        else:
            return f"{seconds}초"
    
    def is_active_session(self):
        """현재 활성 세션인지 확인"""
        return self.logout_time is None
    
    @classmethod
    def get_active_sessions_count(cls, user):
        """사용자의 활성 세션 수"""
        return cls.objects.filter(user=user, logout_time__isnull=True).count()
    
    @classmethod
    def get_recent_login_attempts(cls, ip_address, hours=24):
        """특정 IP의 최근 로그인 시도 횟수"""
        from django.utils import timezone
        since = timezone.now() - timedelta(hours=hours)
        return cls.objects.filter(
            ip_address=ip_address, 
            login_time__gte=since
        ).count()


class PhoneVerification(models.Model):
    """전화번호 인증 관리"""
    
    phone_number = models.CharField(max_length=20, verbose_name="전화번호")
    verification_code = models.CharField(max_length=6, verbose_name="인증 코드")
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField(verbose_name="만료 시간")
    verified = models.BooleanField(default=False, verbose_name="인증 완료")
    attempts = models.PositiveIntegerField(default=0, verbose_name="시도 횟수")
    
    class Meta:
        verbose_name = "전화번호 인증"
        verbose_name_plural = "전화번호 인증"
        ordering = ['-created_at']
        
    def __str__(self):
        return f"{self.phone_number} - {self.verification_code}"
        
    def is_expired(self):
        """만료 여부 확인"""
        return timezone.now() > self.expires_at
        
    def is_valid_code(self, code):
        """인증 코드 유효성 확인"""
        return (
            not self.is_expired() and 
            self.verification_code == code and 
            self.attempts < 5
        )
    
    @classmethod
    def clean_expired(cls):
        """만료된 인증 기록 정리"""
        cls.objects.filter(expires_at__lt=timezone.now()).delete()


class EmailVerification(models.Model):
    """이메일 인증 관리"""
    
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='email_verifications',
        verbose_name="사용자",
        null=True,
        blank=True
    )
    email = models.EmailField(verbose_name="이메일 주소", default="")
    code = models.CharField(max_length=6, verbose_name="인증 번호")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="생성 시간")
    expires_at = models.DateTimeField(verbose_name="만료 시간")
    used = models.BooleanField(default=False, verbose_name="사용 여부")
    used_at = models.DateTimeField(null=True, blank=True, verbose_name="사용 시간")
    attempts = models.PositiveIntegerField(default=0, verbose_name="시도 횟수")
    
    class Meta:
        verbose_name = "이메일 인증"
        verbose_name_plural = "이메일 인증"
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['code']),
            models.Index(fields=['user', '-created_at']),
            models.Index(fields=['expires_at']),
        ]
        unique_together = [['user', 'code']]  # 사용자별 인증번호 중복 방지
    
    def __str__(self):
        return f"{self.user.email} - {self.code}"
    
    def is_expired(self):
        """만료 여부 확인"""
        return timezone.now() > self.expires_at
    
    def is_valid(self):
        """유효성 확인 (만료되지 않고 사용되지 않은 인증번호)"""
        return not self.used and not self.is_expired() and self.attempts < 5
    
    def mark_as_used(self):
        """인증번호를 사용된 것으로 표시"""
        self.used = True
        self.used_at = timezone.now()
        self.save(update_fields=['used', 'used_at'])
    
    def increment_attempts(self):
        """시도 횟수 증가"""
        self.attempts += 1
        self.save(update_fields=['attempts'])
    
    @classmethod
    def generate_code(cls):
        """6자리 인증번호 생성"""
        import random
        return f"{random.randint(100000, 999999)}"
    
    @classmethod
    def create_for_user(cls, user):
        """사용자를 위한 이메일 인증번호 생성"""
        # 기존 미사용 인증번호들을 만료시킴
        cls.objects.filter(user=user, used=False).update(used=True, used_at=timezone.now())
        
        # 새 인증번호 생성 (5분 유효)
        code = cls.generate_code()
        expires_at = timezone.now() + timedelta(minutes=5)
        
        return cls.objects.create(
            user=user,
            email=user.email,
            code=code,
            expires_at=expires_at
        )
    
    @classmethod
    def create_for_email(cls, email):
        """이메일을 위한 임시 인증번호 생성 (계정 생성 전)"""
        # 기존 미사용 인증번호들을 만료시킴
        cls.objects.filter(email=email, user__isnull=True, used=False).update(used=True, used_at=timezone.now())
        
        # 새 인증번호 생성 (5분 유효)
        code = cls.generate_code()
        expires_at = timezone.now() + timedelta(minutes=5)
        
        return cls.objects.create(
            user=None,
            email=email,
            code=code,
            expires_at=expires_at
        )
    
    @classmethod
    def verify_code(cls, user, code):
        """인증번호 검증 및 사용자 반환"""
        try:
            verification = cls.objects.filter(user=user, code=code, used=False).latest('created_at')
            
            # 시도 횟수 증가
            verification.increment_attempts()
            
            if not verification.is_valid():
                if verification.is_expired():
                    return None, "인증번호가 만료되었습니다. 새로 요청해주세요."
                elif verification.attempts >= 5:
                    return None, "인증 시도 횟수가 초과되었습니다. 새로 요청해주세요."
                else:
                    return None, "이미 사용된 인증번호입니다."
            
            # 인증번호 사용 처리
            verification.mark_as_used()
            
            # 사용자 이메일 인증 완료 처리
            user.email_verified = True
            user.email_verified_at = timezone.now()
            user.is_active = True  # 계정 활성화
            user.save(update_fields=['email_verified', 'email_verified_at', 'is_active'])
            
            return user, "이메일 인증이 완료되었습니다."
            
        except cls.DoesNotExist:
            return None, "유효하지 않은 인증번호입니다."
    
    @classmethod
    def verify_email_code(cls, email, code):
        """이메일 기반 인증번호 검증 (계정 생성 전/후 모두 지원)"""
        try:
            # 먼저 계정이 없는 임시 인증번호 확인
            verification = cls.objects.filter(
                email=email, 
                code=code, 
                used=False,
                user__isnull=True
            ).latest('created_at')
            
            # 시도 횟수 증가
            verification.increment_attempts()
            
            if not verification.is_valid():
                if verification.is_expired():
                    return None, "인증번호가 만료되었습니다. 새로 요청해주세요."
                elif verification.attempts >= 5:
                    return None, "인증 시도 횟수가 초과되었습니다. 새로 요청해주세요."
                else:
                    return None, "이미 사용된 인증번호입니다."
            
            # 인증번호 사용 처리
            verification.mark_as_used()
            
            return True, "이메일 인증이 완료되었습니다."
            
        except cls.DoesNotExist:
            # 계정이 있는 경우도 확인
            try:
                user = User.objects.get(email=email, is_active=False)
                return cls.verify_code(user, code)
            except User.DoesNotExist:
                return None, "유효하지 않은 인증번호입니다."
    
    @classmethod
    def clean_expired(cls):
        """만료된 인증번호 정리"""
        cls.objects.filter(expires_at__lt=timezone.now()).delete()
