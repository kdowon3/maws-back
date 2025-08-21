# MAWS 관리자 API 보안 미들웨어 (간소화 버전)
from django.http import JsonResponse
from django.utils import timezone
from django.conf import settings
import logging
import json

logger = logging.getLogger(__name__)

class AdminSecurityMiddleware:
    """관리자 API 보안 미들웨어 - IP 필터링만 담당"""
    
    def __init__(self, get_response):
        self.get_response = get_response
        # IP 화이트리스트 (설정에서 가져오기)
        self.allowed_ips = getattr(settings, 'ADMIN_ALLOWED_IPS', [])
        
        # 보안 헤더 설정
        self.security_headers = {
            'X-Content-Type-Options': 'nosniff',
            'X-Frame-Options': 'DENY',
            'X-XSS-Protection': '1; mode=block',
            'Referrer-Policy': 'strict-origin-when-cross-origin',
            'Content-Security-Policy': "default-src 'self'",
        }
    
    def __call__(self, request):
        # /api/admin/ 경로에 대해서는 IP 필터링만 수행 (DRF에서 인증 처리)
        if request.path.startswith('/api/admin/') and self.allowed_ips:
            client_ip = self.get_client_ip(request)
            if client_ip not in self.allowed_ips:
                logger.warning(f"🚨 [ADMIN IP BLOCKED] {json.dumps({
                    'timestamp': timezone.now().isoformat(),
                    'client_ip': client_ip,
                    'path': request.path,
                    'allowed_ips': self.allowed_ips
                })}")
                return JsonResponse({
                    'error': 'Access denied from this IP',
                    'message': 'Your IP address is not authorized for admin access',
                    'timestamp': timezone.now().isoformat()
                }, status=403)
        
        # 요청 처리
        response = self.get_response(request)
        
        # 관리자 경로에 보안 헤더 추가
        if request.path.startswith('/api/admin/') or request.path.startswith('/admin/'):
            for header, value in self.security_headers.items():
                response[header] = value
        
        return response
    
    def get_client_ip(self, request):
        """클라이언트 IP 주소 추출"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0].strip()
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip

