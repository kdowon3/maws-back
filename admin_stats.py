# MAWS 관리자 통계 서비스 - Zero-Knowledge 원칙 준수
from accounts.models import Gallery, User, LoginHistory
from clients.models import Client, Tag
from artworks.models import Artwork
from clients.models import ClientColumn
from django.db.models import Count, Q
from django.utils import timezone
from datetime import timedelta
import logging

logger = logging.getLogger(__name__)

class MAWSAdminStats:
    """MAWS 관리자 통계 서비스 - Zero-Knowledge 원칙 준수"""
    
    @staticmethod
    def get_system_overview():
        """전체 시스템 현황 (개인정보 없음)"""
        try:
            return {
                # 기본 통계
                'total_galleries': Gallery.objects.count(),
                'active_galleries': Gallery.objects.filter(is_active=True).count(),
                'total_users': User.objects.count(),
                'active_users': User.objects.filter(is_active=True).count(),
                
                # 관리 데이터 통계 (개수만)
                'total_clients': Client.objects.count(),
                'total_artworks': Artwork.objects.count(),
                'total_tags': Tag.objects.count(),
                'total_columns': ClientColumn.objects.count(),
                
                # 생성일 기준 신규 통계
                'new_galleries_this_month': Gallery.objects.filter(
                    created_at__gte=timezone.now().replace(day=1)
                ).count(),
                'new_users_this_month': User.objects.filter(
                    created_at__gte=timezone.now().replace(day=1)
                ).count(),
                
                # 추가 시스템 지표
                'galleries_with_clients': Gallery.objects.annotate(
                    client_count=Count('clients')
                ).filter(client_count__gt=0).count(),
                'galleries_with_artworks': Gallery.objects.annotate(
                    artwork_count=Count('artworks')
                ).filter(artwork_count__gt=0).count(),
            }
        except Exception as e:
            logger.error(f"Error in get_system_overview: {e}")
            return {}
    
    @staticmethod
    def get_gallery_distribution():
        """갤러리 분포 현황 (개인정보 제외)"""
        try:
            return {
                # 가입 방식별 분포
                'signup_methods': dict(
                    Gallery.objects.values('signup_method').annotate(
                        count=Count('id')
                    ).values_list('signup_method', 'count')
                ),
                
                # 구독 상태별 분포
                'subscription_status': {
                    'active': Gallery.objects.filter(
                        is_active=True,
                        subscription_expires__gt=timezone.now()
                    ).count() if Gallery.objects.filter(subscription_expires__isnull=False).exists() else Gallery.objects.filter(is_active=True).count(),
                    'expiring_soon': Gallery.objects.filter(
                        is_active=True,
                        subscription_expires__lte=timezone.now() + timedelta(days=30),
                        subscription_expires__gt=timezone.now()
                    ).count() if Gallery.objects.filter(subscription_expires__isnull=False).exists() else 0,
                    'expired': Gallery.objects.filter(
                        Q(subscription_expires__lte=timezone.now()) | Q(is_active=False)
                    ).count() if Gallery.objects.filter(subscription_expires__isnull=False).exists() else Gallery.objects.filter(is_active=False).count()
                },
                
                # 사용자 수 분포
                'user_count_distribution': {
                    '1-3명': Gallery.objects.annotate(
                        user_count=Count('users')
                    ).filter(user_count__lte=3).count(),
                    '4-7명': Gallery.objects.annotate(
                        user_count=Count('users')
                    ).filter(user_count__range=(4, 7)).count(),
                    '8-10명': Gallery.objects.annotate(
                        user_count=Count('users')
                    ).filter(user_count__range=(8, 10)).count(),
                    '10명+': Gallery.objects.annotate(
                        user_count=Count('users')
                    ).filter(user_count__gt=10).count(),
                },
                
                # 갤러리 활동 상태
                'activity_status': {
                    'with_data': Gallery.objects.annotate(
                        total_data=Count('clients') + Count('artworks')
                    ).filter(total_data__gt=0).count(),
                    'empty': Gallery.objects.annotate(
                        total_data=Count('clients') + Count('artworks')
                    ).filter(total_data=0).count(),
                }
            }
        except Exception as e:
            logger.error(f"Error in get_gallery_distribution: {e}")
            return {}
    
    @staticmethod
    def get_user_analytics():
        """사용자 분석 (개인정보 제외)"""
        try:
            return {
                # 역할별 분포
                'role_distribution': dict(
                    User.objects.values('role').annotate(
                        count=Count('id')
                    ).values_list('role', 'count')
                ),
                
                # 활성도 분석
                'activity_stats': {
                    'email_verified': User.objects.filter(email_verified=True).count(),
                    'email_unverified': User.objects.filter(email_verified=False).count(),
                    'locked_accounts': User.objects.filter(
                        account_locked_until__gt=timezone.now()
                    ).count(),
                    'recent_login': User.objects.filter(
                        last_login__gte=timezone.now() - timedelta(days=7)
                    ).count() if User.objects.filter(last_login__isnull=False).exists() else 0,
                },
                
                # 권한 분포
                'permission_stats': {
                    'can_manage_clients': User.objects.filter(can_manage_clients=True).count(),
                    'can_manage_artworks': User.objects.filter(can_manage_artworks=True).count(),
                    'can_export_data': User.objects.filter(can_export_data=True).count(),
                    'can_send_messages': User.objects.filter(can_send_messages=True).count(),
                    'can_view_reports': User.objects.filter(can_view_reports=True).count(),
                    'can_manage_users': User.objects.filter(can_manage_users=True).count(),
                    'can_manage_gallery_settings': User.objects.filter(can_manage_gallery_settings=True).count(),
                },
                
                # 계정 보안 상태
                'security_stats': {
                    'strong_passwords': User.objects.filter(
                        password_changed_at__gte=timezone.now() - timedelta(days=90)
                    ).count() if User.objects.filter(password_changed_at__isnull=False).exists() else 0,
                    'failed_login_attempts': User.objects.filter(
                        failed_login_attempts__gt=0
                    ).count(),
                }
            }
        except Exception as e:
            logger.error(f"Error in get_user_analytics: {e}")
            return {}
    
    @staticmethod
    def get_usage_patterns():
        """사용 패턴 분석 (익명화된 데이터)"""
        try:
            # 갤러리별 데이터 현황 (개인정보 없는 숫자만)
            gallery_stats = []
            for gallery in Gallery.objects.filter(is_active=True):
                gallery_stats.append({
                    'gallery_id': gallery.id,  # ID만 (갤러리명 제외)
                    'client_count': Client.objects.filter(gallery=gallery).count(),
                    'artwork_count': Artwork.objects.filter(gallery=gallery).count(),
                    'user_count': User.objects.filter(gallery=gallery, is_active=True).count(),
                    'tag_count': Tag.objects.filter(gallery=gallery).count(),
                    'column_count': ClientColumn.objects.filter(gallery=gallery).count(),
                    'created_days_ago': (timezone.now().date() - gallery.created_at.date()).days,
                    'signup_method': gallery.signup_method,
                })
            
            # 평균 계산 (0으로 나누기 방지)
            total_galleries = len(gallery_stats)
            avg_clients = sum(g['client_count'] for g in gallery_stats) / total_galleries if total_galleries > 0 else 0
            avg_artworks = sum(g['artwork_count'] for g in gallery_stats) / total_galleries if total_galleries > 0 else 0
            avg_users = sum(g['user_count'] for g in gallery_stats) / total_galleries if total_galleries > 0 else 0
            
            return {
                'gallery_usage_stats': gallery_stats,
                'average_clients_per_gallery': round(avg_clients, 2),
                'average_artworks_per_gallery': round(avg_artworks, 2),
                'average_users_per_gallery': round(avg_users, 2),
                
                # 사용량 분포
                'usage_distribution': {
                    'heavy_users': len([g for g in gallery_stats if g['client_count'] > 50]),
                    'medium_users': len([g for g in gallery_stats if 10 <= g['client_count'] <= 50]),
                    'light_users': len([g for g in gallery_stats if 1 <= g['client_count'] < 10]),
                    'no_data': len([g for g in gallery_stats if g['client_count'] == 0]),
                },
                
                # 기간별 가입 분포
                'signup_timeline': {
                    'last_7_days': len([g for g in gallery_stats if g['created_days_ago'] <= 7]),
                    'last_30_days': len([g for g in gallery_stats if g['created_days_ago'] <= 30]),
                    'last_90_days': len([g for g in gallery_stats if g['created_days_ago'] <= 90]),
                    'older': len([g for g in gallery_stats if g['created_days_ago'] > 90]),
                }
            }
        except Exception as e:
            logger.error(f"Error in get_usage_patterns: {e}")
            return {}
    
    @staticmethod
    def get_security_metrics():
        """보안 지표 (개인정보 제외)"""
        try:
            last_24h = timezone.now() - timedelta(hours=24)
            last_7d = timezone.now() - timedelta(days=7)
            
            return {
                # 로그인 현황 (최근 24시간)
                'login_stats_24h': {
                    'total_logins': LoginHistory.objects.filter(
                        login_time__gte=last_24h
                    ).count() if LoginHistory.objects.exists() else 0,
                    'unique_users': LoginHistory.objects.filter(
                        login_time__gte=last_24h
                    ).values('user').distinct().count() if LoginHistory.objects.exists() else 0,
                    'failed_attempts': User.objects.filter(
                        failed_login_attempts__gt=0
                    ).count(),
                },
                
                # 세션 현황
                'session_stats': {
                    'active_sessions': LoginHistory.objects.filter(
                        logout_time__isnull=True
                    ).count() if LoginHistory.objects.exists() else 0,
                    'total_sessions_7d': LoginHistory.objects.filter(
                        login_time__gte=last_7d
                    ).count() if LoginHistory.objects.exists() else 0,
                },
                
                # 보안 알림
                'security_alerts': {
                    'locked_accounts': User.objects.filter(
                        account_locked_until__gt=timezone.now()
                    ).count(),
                    'recent_password_changes': User.objects.filter(
                        password_changed_at__gte=last_7d
                    ).count() if User.objects.filter(password_changed_at__isnull=False).exists() else 0,
                    'unverified_emails': User.objects.filter(
                        email_verified=False,
                        is_active=True
                    ).count(),
                },
                
                # 시스템 접근 패턴
                'access_patterns': {
                    'superuser_count': User.objects.filter(is_superuser=True).count(),
                    'staff_count': User.objects.filter(is_staff=True).count(),
                    'admin_logins_24h': LoginHistory.objects.filter(
                        login_time__gte=last_24h,
                        user__is_staff=True
                    ).count() if LoginHistory.objects.exists() else 0,
                }
            }
        except Exception as e:
            logger.error(f"Error in get_security_metrics: {e}")
            return {}
    
    @classmethod
    def get_all_stats(cls):
        """모든 통계를 한번에 수집"""
        try:
            return {
                'system_overview': cls.get_system_overview(),
                'gallery_distribution': cls.get_gallery_distribution(),
                'user_analytics': cls.get_user_analytics(),
                'usage_patterns': cls.get_usage_patterns(),
                'security_metrics': cls.get_security_metrics(),
                'last_updated': timezone.now().isoformat(),
                'collection_success': True,
            }
        except Exception as e:
            logger.error(f"Error in get_all_stats: {e}")
            return {
                'error': 'Statistics collection failed',
                'last_updated': timezone.now().isoformat(),
                'collection_success': False,
            }


class DataSafetyValidator:
    """수집 데이터의 개인정보 포함 여부 검증"""
    
    FORBIDDEN_FIELDS = [
        'client_name', 'client_phone', 'client_email', 'client_address',  # 고객 개인정보
        'encrypted_name', 'encrypted_phone', 'encrypted_email',  # 암호화된 개인정보
        'message_content', 'conversation', 'chat',  # 커뮤니케이션 내용
        'password', 'password_hash', 'token',  # 인증 정보
        'api_key', 'secret_key', 'private_key',  # API 키
    ]
    
    FORBIDDEN_PATTERNS = [
        'personal', 'private', 'confidential', 'sensitive'
    ]
    
    @classmethod
    def validate_response(cls, data):
        """응답 데이터에 개인정보가 포함되지 않았는지 검증"""
        def check_dict(obj, path=""):
            if isinstance(obj, dict):
                for key, value in obj.items():
                    current_path = f"{path}.{key}" if path else key
                    
                    # 금지된 필드명 체크 (정확한 일치만)
                    if key.lower() in [field.lower() for field in cls.FORBIDDEN_FIELDS]:
                        raise ValueError(f"Forbidden field detected: {current_path}")
                    
                    # 금지된 패턴 체크 (포함되어 있는 경우만)
                    if any(pattern in key.lower() for pattern in cls.FORBIDDEN_PATTERNS):
                        raise ValueError(f"Forbidden pattern detected: {current_path}")
                    
                    # 재귀적으로 하위 객체 검사
                    if isinstance(value, (dict, list)):
                        check_dict(value, current_path)
                    
                    # 문자열 값에서 개인정보 패턴 검사
                    elif isinstance(value, str) and len(value) > 50:
                        # 긴 문자열은 개인정보일 가능성이 있으므로 경고
                        logger.warning(f"Long string value detected in {current_path}: {len(value)} characters")
            
            elif isinstance(obj, list):
                for i, item in enumerate(obj):
                    if isinstance(item, (dict, list)):
                        check_dict(item, f"{path}[{i}]")
        
        try:
            check_dict(data)
            return True
        except ValueError as e:
            logger.error(f"Data safety validation failed: {e}")
            raise e
    
    @classmethod
    def sanitize_stats(cls, stats):
        """통계 데이터 사후 검증 및 정화"""
        try:
            # 응답 데이터 검증
            cls.validate_response(stats)
            
            # 추가 보안 체크
            if 'gallery_usage_stats' in stats.get('usage_patterns', {}):
                for gallery_stat in stats['usage_patterns']['gallery_usage_stats']:
                    # 갤러리 ID만 유지, 다른 식별 정보 제거
                    allowed_keys = {'gallery_id', 'client_count', 'artwork_count', 'user_count', 
                                  'tag_count', 'column_count', 'created_days_ago', 'signup_method'}
                    gallery_stat = {k: v for k, v in gallery_stat.items() if k in allowed_keys}
            
            logger.info("Statistics data validation passed")
            return stats
            
        except Exception as e:
            logger.error(f"Statistics sanitization failed: {e}")
            # 실패시 기본 안전한 응답만 반환
            return {
                'error': 'Data sanitization required',
                'safe_stats': {
                    'total_galleries': stats.get('system_overview', {}).get('total_galleries', 0),
                    'total_users': stats.get('system_overview', {}).get('total_users', 0),
                }
            }