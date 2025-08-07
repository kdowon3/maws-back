from rest_framework import status, generics, permissions
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.exceptions import TokenError, InvalidToken
from django.contrib.auth import logout
from django.utils import timezone
from django.db import transaction
import random
import re
from datetime import timedelta
from .models import User, Gallery, LoginHistory, PhoneVerification
from .firebase_auth import check_firebase_settings
from .serializers import (
    CustomTokenObtainPairSerializer,
    UserSerializer,
    UserRegistrationSerializer,
    PasswordChangeSerializer,
    LoginHistorySerializer,
    GallerySerializer,
    QuickSignupSerializer
)


class CustomTokenObtainPairView(TokenObtainPairView):
    """커스텀 로그인 뷰"""
    serializer_class = CustomTokenObtainPairSerializer


class CustomTokenRefreshView(TokenRefreshView):
    """커스텀 토큰 갱신 뷰"""
    
    def post(self, request, *args, **kwargs):
        """토큰 갱신 시 사용자 정보도 함께 반환"""
        response = super().post(request, *args, **kwargs)
        
        if response.status_code == 200:
            try:
                # 새로운 액세스 토큰에서 사용자 정보 추출
                refresh = RefreshToken(request.data.get('refresh'))
                user_id = refresh.payload.get('user_id')
                user = User.objects.select_related('gallery').get(id=user_id)
                
                # 사용자 정보 추가
                response.data.update({
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
                        },
                        'permissions': {
                            'manage_clients': user.can_manage_clients,
                            'manage_artworks': user.can_manage_artworks,
                            'export_data': user.can_export_data,
                            'send_messages': user.can_send_messages,
                            'view_reports': user.can_view_reports,
                            'manage_users': user.can_manage_users,
                            'manage_gallery_settings': user.can_manage_gallery_settings,
                        }
                    }
                })
            except (User.DoesNotExist, TokenError):
                pass
        
        return response


class RegisterView(generics.CreateAPIView):
    """사용자 등록 뷰"""
    queryset = User.objects.all()
    serializer_class = UserRegistrationSerializer
    permission_classes = [permissions.AllowAny]
    
    def create(self, request, *args, **kwargs):
        """사용자 등록 처리"""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        with transaction.atomic():
            user = serializer.save()
            
            # 등록 성공 응답
            return Response({
                'message': '계정이 성공적으로 생성되었습니다.',
                'user': {
                    'id': user.id,
                    'username': user.username,
                    'email': user.email,
                    'gallery': user.gallery.name
                }
            }, status=status.HTTP_201_CREATED)


class LogoutView(APIView):
    """로그아웃 뷰"""
    permission_classes = [permissions.IsAuthenticated]
    
    def post(self, request):
        """로그아웃 처리"""
        try:
            # 리프레시 토큰 블랙리스트 추가
            refresh_token = request.data.get('refresh')
            if refresh_token:
                token = RefreshToken(refresh_token)
                token.blacklist()
            
            # 로그인 이력 업데이트 (로그아웃 시간 기록)
            self.update_login_history(request.user)
            
            return Response({
                'message': '성공적으로 로그아웃되었습니다.'
            }, status=status.HTTP_200_OK)
            
        except TokenError:
            return Response({
                'error': '유효하지 않은 토큰입니다.'
            }, status=status.HTTP_400_BAD_REQUEST)
    
    def update_login_history(self, user):
        """로그인 이력 업데이트"""
        # 가장 최근의 활성 세션 찾기
        recent_login = LoginHistory.objects.filter(
            user=user,
            logout_time__isnull=True
        ).order_by('-login_time').first()
        
        if recent_login:
            logout_time = timezone.now()
            recent_login.logout_time = logout_time
            recent_login.session_duration = logout_time - recent_login.login_time
            recent_login.save(update_fields=['logout_time', 'session_duration'])


class UserProfileView(generics.RetrieveUpdateAPIView):
    """사용자 프로필 조회/수정 뷰"""
    serializer_class = UserSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_object(self):
        return self.request.user


class PasswordChangeView(APIView):
    """비밀번호 변경 뷰"""
    permission_classes = [permissions.IsAuthenticated]
    
    def post(self, request):
        """비밀번호 변경 처리"""
        serializer = PasswordChangeSerializer(
            data=request.data,
            context={'request': request}
        )
        
        if serializer.is_valid():
            serializer.save()
            return Response({
                'message': '비밀번호가 성공적으로 변경되었습니다.'
            }, status=status.HTTP_200_OK)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET'])
@permission_classes([permissions.AllowAny])
def check_firebase_config(request):
    """Firebase 설정 상태 확인 API"""
    config_status = check_firebase_settings()
    return Response(config_status, status=status.HTTP_200_OK)


class LoginHistoryView(generics.ListAPIView):
    """로그인 이력 조회 뷰"""
    serializer_class = LoginHistorySerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        """현재 사용자의 로그인 이력만 반환"""
        return LoginHistory.objects.filter(
            user=self.request.user
        ).order_by('-login_time')


class GalleryInfoView(generics.RetrieveAPIView):
    """갤러리 정보 조회 뷰"""
    serializer_class = GallerySerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_object(self):
        return self.request.user.gallery


class GalleryUsersView(generics.ListAPIView):
    """갤러리 사용자 목록 조회 뷰"""
    serializer_class = UserSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        """같은 갤러리 사용자만 반환"""
        user = self.request.user
        
        # 사용자 관리 권한 확인
        if not user.has_permission('manage_users') and user.role not in ['owner', 'manager']:
            return User.objects.none()
        
        return User.objects.filter(
            gallery=user.gallery,
            is_active=True
        ).select_related('gallery').order_by('username')


@api_view(['POST'])
@permission_classes([permissions.AllowAny])
def validate_registration_code(request):
    """가입 코드 유효성 검증 API"""
    code = request.data.get('registration_code')
    
    if not code:
        return Response({
            'valid': False,
            'message': '가입 코드를 입력해주세요.'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        gallery = Gallery.objects.get(registration_code=code, is_active=True)
        
        # 구독 상태 확인
        if not gallery.is_subscription_active:
            return Response({
                'valid': False,
                'message': '해당 갤러리의 구독이 만료되었습니다.'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # 사용자 수 제한 확인
        if not gallery.can_add_user():
            return Response({
                'valid': False,
                'message': '해당 갤러리의 사용자 수가 제한에 도달했습니다.'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        return Response({
            'valid': True,
            'gallery': {
                'name': gallery.name,
                'user_count': gallery.get_user_count(),
                'max_users': gallery.max_users
            }
        }, status=status.HTTP_200_OK)
        
    except Gallery.DoesNotExist:
        return Response({
            'valid': False,
            'message': '유효하지 않은 가입 코드입니다.'
        }, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def check_permission(request):
    """권한 확인 API"""
    permission = request.data.get('permission')
    
    if not permission:
        return Response({
            'error': '권한명을 입력해주세요.'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    has_permission = request.user.has_permission(permission)
    
    return Response({
        'permission': permission,
        'has_permission': has_permission,
        'user_role': request.user.role
    }, status=status.HTTP_200_OK)


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def user_dashboard_data(request):
    """사용자 대시보드 데이터 API"""
    user = request.user
    gallery = user.gallery
    
    # 최근 로그인 이력 (최대 5개)
    recent_logins = LoginHistory.objects.filter(
        user=user
    ).order_by('-login_time')[:5]
    
    # 활성 세션 수
    active_sessions = LoginHistory.get_active_sessions_count(user)
    
    # 갤러리 사용자 수 (권한이 있는 경우만)
    gallery_users_count = None
    if user.has_permission('manage_users') or user.role in ['owner', 'manager']:
        gallery_users_count = gallery.get_user_count()
    
    return Response({
        'user': {
            'full_name': user.get_full_name() or user.username,
            'role_display': user.get_role_display_ko(),
            'job_title': user.job_title,
            'last_login': user.last_login,
            'last_login_ip': user.last_login_ip,
        },
        'gallery': {
            'name': gallery.name,
            'users_count': gallery_users_count,
            'max_users': gallery.max_users if gallery_users_count is not None else None,
            'subscription_active': gallery.is_subscription_active,
        },
        'security': {
            'active_sessions': active_sessions,
            'recent_logins': LoginHistorySerializer(recent_logins, many=True).data,
        }
    }, status=status.HTTP_200_OK)


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def force_logout_session(request):
    """특정 세션 강제 로그아웃 API"""
    session_id = request.data.get('session_id')
    
    if not session_id:
        return Response({
            'error': '세션 ID를 입력해주세요.'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        login_history = LoginHistory.objects.get(
            id=session_id,
            user=request.user,
            logout_time__isnull=True
        )
        
        # 로그아웃 시간 기록
        logout_time = timezone.now()
        login_history.logout_time = logout_time
        login_history.session_duration = logout_time - login_history.login_time
        login_history.save(update_fields=['logout_time', 'session_duration'])
        
        return Response({
            'message': '세션이 성공적으로 종료되었습니다.'
        }, status=status.HTTP_200_OK)
        
    except LoginHistory.DoesNotExist:
        return Response({
            'error': '유효하지 않은 세션입니다.'
        }, status=status.HTTP_404_NOT_FOUND)


@api_view(['POST'])
@permission_classes([permissions.AllowAny])
def send_phone_verification(request):
    """전화번호 인증 코드 발송"""
    phone_number = request.data.get('phone_number')
    
    if not phone_number:
        return Response({
            'error': '전화번호를 입력해주세요.'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    # 전화번호 형식 검증 (한국 휴대폰 번호)
    phone_pattern = r'^01[016789]-?\d{3,4}-?\d{4}$'
    if not re.match(phone_pattern, phone_number.replace(' ', '')):
        return Response({
            'error': '올바른 전화번호 형식이 아닙니다. (예: 010-1234-5678)'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    # 번호 정규화 (하이픈 제거)
    clean_phone = re.sub(r'[^0-9]', '', phone_number)
    
    # 이미 사용 중인 번호 확인
    if Gallery.objects.filter(verified_phone=clean_phone).exists():
        return Response({
            'error': '이미 사용 중인 전화번호입니다.'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    # 6자리 랜덤 코드 생성
    verification_code = str(random.randint(100000, 999999))
    expires_at = timezone.now() + timedelta(minutes=5)  # 5분 후 만료
    
    # 기존 인증 시도 삭제 후 새로 생성
    PhoneVerification.objects.filter(phone_number=clean_phone).delete()
    phone_verification = PhoneVerification.objects.create(
        phone_number=clean_phone,
        verification_code=verification_code,
        expires_at=expires_at
    )
    
    # 실제 SMS 발송 (개발용으로는 콘솔 출력만)
    try:
        # TODO: 실제 SMS 서비스 연동 (예: 네이버 클라우드 플랫폼, AWS SNS 등)
        # 현재는 개발용으로 콘솔에만 출력
        
        # 한국 번호 형식으로 변환
        korean_phone = f"+82{clean_phone[1:]}" if clean_phone.startswith('0') else clean_phone
        
        print(f"[MAWS] SMS 발송 시도:")
        print(f"  전화번호: {korean_phone}")
        print(f"  인증번호: {verification_code}")
        print(f"  만료시간: {expires_at.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"  발송시간: {timezone.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        # 실제 SMS 발송 로직 (향후 구현)
        # sms_service.send_sms(korean_phone, f"[MAWS] 인증번호: {verification_code}")
        
        return Response({
            'message': '인증번호가 발송되었습니다.',
            'expires_in': 300,  # 5분 = 300초
            'dev_code': verification_code,  # 개발용 - 실제 배포시 제거
            'phone_number': korean_phone,  # 발송된 번호
            'note': '개발 환경에서는 실제 SMS가 발송되지 않습니다.'
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        print(f"[MAWS] SMS 발송 실패: {e}")
        return Response({
            'error': '인증번호 발송에 실패했습니다.'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
    except Exception as e:
        return Response({
            'error': '인증번호 발송에 실패했습니다.'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([permissions.AllowAny])
def verify_phone_code(request):
    """전화번호 인증 코드 확인"""
    phone_number = request.data.get('phone_number')
    code = request.data.get('code')
    
    if not phone_number or not code:
        return Response({
            'error': '전화번호와 인증번호를 입력해주세요.'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    # 번호 정규화
    clean_phone = re.sub(r'[^0-9]', '', phone_number)
    
    try:
        phone_verification = PhoneVerification.objects.get(
            phone_number=clean_phone,
            verified=False
        )
        
        # 시도 횟수 증가
        phone_verification.attempts += 1
        phone_verification.save()
        
        if phone_verification.is_valid_code(code):
            phone_verification.verified = True
            phone_verification.save()
            
            return Response({
                'verified': True,
                'message': '전화번호 인증이 완료되었습니다.'
            }, status=status.HTTP_200_OK)
        elif phone_verification.is_expired():
            return Response({
                'verified': False,
                'error': '인증번호가 만료되었습니다. 새로 요청해주세요.'
            }, status=status.HTTP_400_BAD_REQUEST)
        elif phone_verification.attempts >= 5:
            return Response({
                'verified': False,
                'error': '인증 시도 횟수를 초과했습니다. 새로 요청해주세요.'
            }, status=status.HTTP_400_BAD_REQUEST)
        else:
            return Response({
                'verified': False,
                'error': f'인증번호가 올바르지 않습니다. ({5 - phone_verification.attempts}회 남음)'
            }, status=status.HTTP_400_BAD_REQUEST)
            
    except PhoneVerification.DoesNotExist:
        return Response({
            'verified': False,
            'error': '인증번호를 먼저 요청해주세요.'
        }, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@permission_classes([permissions.AllowAny])
def quick_signup(request):
    """간편 회원가입"""
    serializer = QuickSignupSerializer(data=request.data)
    
    if serializer.is_valid():
        try:
            user = serializer.save()
            
            return Response({
                'message': f'{user.gallery.name} 갤러리가 성공적으로 생성되었습니다!',
                'gallery': {
                    'id': user.gallery.id,
                    'name': user.gallery.name,
                    'registration_code': user.gallery.registration_code,
                    'verified_phone': user.gallery.verified_phone
                },
                'user': {
                    'id': user.id,
                    'username': user.username,
                    'email': user.email,
                    'full_name': f'{user.first_name} {user.last_name}',
                    'role': '갤러리 오너',
                    'role_code': user.role
                },
                'next_steps': [
                    '갤러리 상세 정보 입력',
                    '첫 번째 작품 등록',
                    '팀원 초대 (선택사항)'
                ]
            }, status=status.HTTP_201_CREATED)
            
        except Exception as e:
            return Response({
                'error': f'갤러리 생성 중 오류가 발생했습니다: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)