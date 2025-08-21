from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.conf import settings
from django.urls import reverse
from .models import EmailVerification
import logging

logger = logging.getLogger(__name__)


def send_verification_email_to_address(email, request=None):
    """이메일 주소로 직접 인증번호 발송 (계정 생성 전)"""
    try:
        # 이메일 인증번호 생성
        verification = EmailVerification.create_for_email(email)
        
        # 이메일 템플릿 컨텍스트
        context = {
            'user': None,
            'email': email,
            'gallery_name': '',
            'verification_code': verification.code,
            'expires_minutes': 5,
            'site_name': 'MAWS',
            'support_email': getattr(settings, 'DEFAULT_FROM_EMAIL', 'support@maws.com'),
        }
        
        # HTML 및 텍스트 메시지 생성
        subject = f"[MAWS] 이메일 인증번호: {verification.code}"
        
        html_message = render_to_string('emails/email_verification.html', context)
        plain_message = render_to_string('emails/email_verification.txt', context)
        
        # 이메일 발송
        send_mail(
            subject=subject,
            message=plain_message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[email],
            html_message=html_message,
            fail_silently=False,
        )
        
        logger.info(f"이메일 인증번호 발송 완료: {email}, 인증번호: {verification.code}")
        return True, "인증번호가 이메일로 발송되었습니다."
        
    except Exception as e:
        logger.error(f"이메일 발송 실패: {email}, Error: {str(e)}")
        return False, "이메일 발송에 실패했습니다. 관리자에게 문의하세요."


def send_verification_email(user, request=None):
    """사용자에게 이메일 인증번호 발송"""
    try:
        # 이메일 인증번호 생성
        verification = EmailVerification.create_for_user(user)
        
        # 이메일 템플릿 컨텍스트
        context = {
            'user': user,
            'gallery_name': user.gallery.name if user.gallery else '',
            'verification_code': verification.code,
            'expires_minutes': 5,
            'site_name': 'MAWS',
            'support_email': getattr(settings, 'DEFAULT_FROM_EMAIL', 'support@maws.com'),
        }
        
        # HTML 및 텍스트 메시지 생성
        subject = f"[MAWS] 이메일 인증번호: {verification.code}"
        
        html_message = render_to_string('emails/email_verification.html', context)
        plain_message = render_to_string('emails/email_verification.txt', context)
        
        # 이메일 발송
        send_mail(
            subject=subject,
            message=plain_message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email],
            html_message=html_message,
            fail_silently=False,
        )
        
        logger.info(f"이메일 인증번호 발송 완료: {user.email}, 인증번호: {verification.code}")
        return True, "인증번호가 이메일로 발송되었습니다."
        
    except Exception as e:
        logger.error(f"이메일 발송 실패: {user.email}, Error: {str(e)}")
        return False, "이메일 발송에 실패했습니다. 관리자에게 문의하세요."


def send_welcome_email(user):
    """이메일 인증 완료 후 환영 메일 발송"""
    try:
        context = {
            'user': user,
            'gallery_name': user.gallery.name if user.gallery else '',
            'login_url': getattr(settings, 'FRONTEND_DOMAIN', 'localhost:3000') + '/auth/login',
            'site_name': 'MAWS',
            'support_email': getattr(settings, 'DEFAULT_FROM_EMAIL', 'support@maws.com'),
        }
        
        subject = f"[MAWS] {user.gallery.name if user.gallery else ''} 갤러리 가입을 환영합니다!"
        
        html_message = render_to_string('emails/welcome.html', context)
        plain_message = render_to_string('emails/welcome.txt', context)
        
        send_mail(
            subject=subject,
            message=plain_message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email],
            html_message=html_message,
            fail_silently=True,  # 환영 메일은 실패해도 무시
        )
        
        logger.info(f"환영 이메일 발송 완료: {user.email}")
        
    except Exception as e:
        logger.error(f"환영 이메일 발송 실패: {user.email}, Error: {str(e)}")


def resend_verification_email(user, request=None):
    """이메일 인증번호 재발송"""
    # 최근 1분 내에 발송한 이메일이 있는지 확인
    from django.utils import timezone
    from datetime import timedelta
    
    recent_verification = EmailVerification.objects.filter(
        user=user,
        created_at__gte=timezone.now() - timedelta(minutes=1)
    ).first()
    
    if recent_verification:
        return False, "인증번호 재발송은 1분 후에 가능합니다."
    
    return send_verification_email(user, request)


def verify_email_code_by_email(email, code):
    """이메일 기반 인증번호 검증 (계정 생성 전/후 모두 지원)"""
    result, message = EmailVerification.verify_email_code(email, code)
    
    # 사용자가 반환되면 환영 이메일 발송
    if result and hasattr(result, 'email'):
        send_welcome_email(result)
        
    return result, message


def verify_email_code(user, code):
    """이메일 인증번호 검증 및 계정 활성화"""
    user_result, message = EmailVerification.verify_code(user, code)
    
    if user_result:
        # 환영 이메일 발송
        send_welcome_email(user_result)
        
    return user_result, message