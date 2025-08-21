# MAWS 관리자 전용 API 뷰 - 간소화 버전
from django.utils import timezone
from django.conf import settings
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
import logging

from admin_stats import MAWSAdminStats, DataSafetyValidator

logger = logging.getLogger(__name__)


class AdminDashboardAPI(APIView):
    """관리자 전용 대시보드 API - 간소화 버전"""
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        """관리자 대시보드 통계 반환"""
        # superuser 권한 확인
        if not request.user.is_superuser:
            return Response({
                'error': 'Admin access required', 
                'message': 'Superuser privileges required for this action',
                'timestamp': timezone.now().isoformat()
            }, status=status.HTTP_403_FORBIDDEN)
        
        try:
            # 통계 데이터 수집
            stats = MAWSAdminStats.get_all_stats()
            
            # 데이터 안전성 검증
            validated_stats = DataSafetyValidator.sanitize_stats(stats)
            
            # 메타 정보 추가
            validated_stats['meta'] = {
                'timestamp': timezone.now().isoformat(),
                'version': '1.0.0',
                'data_privacy': 'Zero-Knowledge compliant'
            }
            
            return Response(validated_stats)
            
        except Exception as e:
            logger.error(f"Admin dashboard error: {e}")
            return Response({
                'error': 'Dashboard data unavailable',
                'message': str(e),
                'timestamp': timezone.now().isoformat()
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    def post(self, request):
        """관리자 작업 수행"""
        if not request.user.is_superuser:
            return Response({
                'error': 'Admin access required'
            }, status=status.HTTP_403_FORBIDDEN)
        
        action = request.data.get('action')
        
        if action == 'refresh_cache':
            return Response({
                'message': 'Cache refresh requested',
                'status': 'success',
                'timestamp': timezone.now().isoformat()
            })
        
        elif action == 'health_check':
            try:
                basic_stats = MAWSAdminStats.get_system_overview()
                return Response({
                    'status': 'healthy',
                    'message': 'System is operational',
                    'basic_stats': basic_stats,
                    'timestamp': timezone.now().isoformat()
                })
            except Exception as e:
                return Response({
                    'status': 'unhealthy',
                    'error': str(e),
                    'timestamp': timezone.now().isoformat()
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
        else:
            return Response({
                'error': 'Unknown action',
                'available_actions': ['refresh_cache', 'health_check']
            }, status=status.HTTP_400_BAD_REQUEST)


class AdminSystemInfoAPI(APIView):
    """시스템 정보 API (관리자 전용) - 간소화 버전"""
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        """시스템 정보 반환"""
        if not request.user.is_superuser:
            return Response({
                'error': 'Admin access required',
                'timestamp': timezone.now().isoformat()
            }, status=status.HTTP_403_FORBIDDEN)
        
        try:
            system_info = {
                'django_version': getattr(settings, 'DJANGO_VERSION', 'unknown'),
                'debug_mode': settings.DEBUG,
                'database_engine': settings.DATABASES['default']['ENGINE'],
                'installed_apps_count': len(settings.INSTALLED_APPS),
                'middleware_count': len(settings.MIDDLEWARE),
                'admin_dashboard_enabled': getattr(settings, 'ADMIN_DASHBOARD_ENABLED', True),
                'time_zone': settings.TIME_ZONE,
                'language_code': settings.LANGUAGE_CODE,
                'server_time': timezone.now().isoformat(),
            }
            
            return Response({
                'system_info': system_info,
                'timestamp': timezone.now().isoformat()
            })
            
        except Exception as e:
            logger.error(f"System info error: {e}")
            return Response({
                'error': 'System info unavailable',
                'timestamp': timezone.now().isoformat()
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class AdminStatsDetailAPI(APIView):
    """상세 통계 API (관리자 전용) - 간소화 버전"""
    permission_classes = [IsAuthenticated]
    
    def get(self, request, stat_type):
        """특정 통계 유형의 상세 정보 반환"""
        if not request.user.is_superuser:
            return Response({
                'error': 'Admin access required',
                'timestamp': timezone.now().isoformat()
            }, status=status.HTTP_403_FORBIDDEN)
        
        try:
            if stat_type == 'system':
                data = MAWSAdminStats.get_system_overview()
            elif stat_type == 'galleries':
                data = MAWSAdminStats.get_gallery_distribution()
            elif stat_type == 'users':
                data = MAWSAdminStats.get_user_analytics()
            elif stat_type == 'usage':
                data = MAWSAdminStats.get_usage_patterns()
            elif stat_type == 'security':
                data = MAWSAdminStats.get_security_metrics()
            else:
                return Response({
                    'error': 'Invalid stat type',
                    'available_types': ['system', 'galleries', 'users', 'usage', 'security'],
                    'timestamp': timezone.now().isoformat()
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # 데이터 검증
            DataSafetyValidator.validate_response(data)
            
            return Response({
                'stat_type': stat_type,
                'data': data,
                'timestamp': timezone.now().isoformat()
            })
            
        except Exception as e:
            logger.error(f"Stats detail error ({stat_type}): {e}")
            return Response({
                'error': f'Failed to get {stat_type} statistics',
                'message': str(e),
                'timestamp': timezone.now().isoformat()
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# 권한 확인 유틸리티 뷰 - 간소화 버전
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def check_admin_permission(request):
    """관리자 권한 확인 유틸리티"""
    if not request.user.is_superuser:
        return Response({
            'has_permission': False,
            'reason': 'Insufficient privileges',
            'current_user': request.user.username,
            'is_staff': request.user.is_staff
        })
    
    return Response({
        'has_permission': True,
        'user': request.user.username,
        'permissions': {
            'is_superuser': request.user.is_superuser,
            'is_staff': request.user.is_staff,
            'is_active': request.user.is_active
        }
    })