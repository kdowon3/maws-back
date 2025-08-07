import firebase_admin
from firebase_admin import auth, credentials
from django.conf import settings
import logging
import os
import json

logger = logging.getLogger(__name__)

# Firebase Admin SDK 초기화
def initialize_firebase_admin():
    """Firebase Admin SDK 초기화"""
    if not firebase_admin._apps:
        try:
            # 환경변수에서 Firebase 서비스 계정 정보 가져오기
            firebase_config = {
                "type": os.environ.get('FIREBASE_TYPE'),
                "project_id": os.environ.get('FIREBASE_PROJECT_ID'),
                "private_key_id": os.environ.get('FIREBASE_PRIVATE_KEY_ID'),
                "private_key": os.environ.get('FIREBASE_PRIVATE_KEY').replace('\\n', '\n') if os.environ.get('FIREBASE_PRIVATE_KEY') else None,
                "client_email": os.environ.get('FIREBASE_CLIENT_EMAIL'),
                "client_id": os.environ.get('FIREBASE_CLIENT_ID'),
                "auth_uri": os.environ.get('FIREBASE_AUTH_URI'),
                "token_uri": os.environ.get('FIREBASE_TOKEN_URI'),
                "auth_provider_x509_cert_url": os.environ.get('FIREBASE_AUTH_PROVIDER_X509_CERT_URL'),
                "client_x509_cert_url": os.environ.get('FIREBASE_CLIENT_X509_CERT_URL'),
                "universe_domain": os.environ.get('FIREBASE_UNIVERSE_DOMAIN')
            }
            
            # 필수 필드들이 모두 있는지 확인
            required_fields = ['type', 'project_id', 'private_key', 'client_email']
            missing_fields = [field for field in required_fields if not firebase_config.get(field)]
            
            if missing_fields:
                logger.warning(f"Missing Firebase environment variables: {missing_fields}")
                # 기본 인증 사용
                firebase_admin.initialize_app()
                logger.info("Firebase Admin SDK initialized with default credentials")
            else:
                # 환경변수로 Firebase 초기화
                cred = credentials.Certificate(firebase_config)
                firebase_admin.initialize_app(cred)
                logger.info("Firebase Admin SDK initialized with environment variables")
                
        except Exception as e:
            logger.error(f"Failed to initialize Firebase Admin SDK: {e}")
            # 기본 인증으로 fallback
            try:
                firebase_admin.initialize_app()
                logger.info("Firebase Admin SDK initialized with default credentials (fallback)")
            except Exception as fallback_error:
                logger.error(f"Failed to initialize Firebase Admin SDK with fallback: {fallback_error}")
                raise


def verify_firebase_id_token(id_token):
    """
    Firebase ID 토큰을 검증하고 사용자 정보를 반환
    
    Args:
        id_token (str): Firebase ID 토큰
        
    Returns:
        dict: 검증된 토큰 정보 또는 None
    """
    try:
        # Firebase Admin SDK 초기화 확인
        if not firebase_admin._apps:
            initialize_firebase_admin()
        
        # ID 토큰 검증
        decoded_token = auth.verify_id_token(id_token)
        
        logger.info(f"Firebase token verified for user: {decoded_token.get('uid')}")
        
        return {
            'uid': decoded_token.get('uid'),
            'phone_number': decoded_token.get('phone_number'),
            'firebase_claims': decoded_token
        }
        
    except auth.ExpiredIdTokenError:
        logger.warning("Firebase ID token has expired")
        return None
    except auth.RevokedIdTokenError:
        logger.warning("Firebase ID token has been revoked")
        return None
    except auth.InvalidIdTokenError:
        logger.warning("Firebase ID token is invalid")
        return None
    except Exception as e:
        logger.error(f"Error verifying Firebase ID token: {e}")
        return None


def get_firebase_user_by_phone(phone_number):
    """
    전화번호로 Firebase 사용자 정보 조회
    
    Args:
        phone_number (str): 전화번호 (+82 형식)
        
    Returns:
        dict: 사용자 정보 또는 None
    """
    try:
        if not firebase_admin._apps:
            initialize_firebase_admin()
            
        user_record = auth.get_user_by_phone_number(phone_number)
        
        return {
            'uid': user_record.uid,
            'phone_number': user_record.phone_number,
            'email': user_record.email,
            'created_time': user_record.user_metadata.creation_timestamp,
            'last_sign_in': user_record.user_metadata.last_sign_in_timestamp
        }
        
    except auth.UserNotFoundError:
        logger.info(f"No Firebase user found with phone number: {phone_number}")
        return None
    except Exception as e:
        logger.error(f"Error getting Firebase user by phone: {e}")
        return None


def create_custom_token(uid, additional_claims=None):
    """
    Firebase 커스텀 토큰 생성
    
    Args:
        uid (str): Firebase 사용자 UID
        additional_claims (dict): 추가 클레임
        
    Returns:
        str: 커스텀 토큰 또는 None
    """
    try:
        if not firebase_admin._apps:
            initialize_firebase_admin()
            
        custom_token = auth.create_custom_token(uid, additional_claims)
        return custom_token.decode('utf-8')
        
    except Exception as e:
        logger.error(f"Error creating custom token: {e}")
        return None


def validate_phone_number_format(phone_number):
    """
    전화번호 형식 검증 (국제 형식)
    
    Args:
        phone_number (str): 전화번호
        
    Returns:
        bool: 유효한 형식인지 여부
    """
    import re
    
    # 국제 전화번호 형식 (+82로 시작하는 한국 번호)
    pattern = r'^\+82[0-9]{8,10}$'
    return bool(re.match(pattern, phone_number))


def extract_phone_from_firebase_token(id_token):
    """
    Firebase ID 토큰에서 전화번호 추출
    
    Args:
        id_token (str): Firebase ID 토큰
        
    Returns:
        str: 전화번호 또는 None
    """
    verified_token = verify_firebase_id_token(id_token)
    if verified_token:
        return verified_token.get('phone_number')
    return None


# Django 설정에서 Firebase 설정 확인
def check_firebase_settings():
    """Firebase 설정 상태 확인"""
    config_status = {
        'firebase_admin_initialized': bool(firebase_admin._apps),
        'service_account_key_path': getattr(settings, 'FIREBASE_SERVICE_ACCOUNT_KEY_PATH', None),
        'service_account_key_exists': False,
        'project_id': getattr(settings, 'FIREBASE_PROJECT_ID', None)
    }
    
    if config_status['service_account_key_path']:
        config_status['service_account_key_exists'] = os.path.exists(
            config_status['service_account_key_path']
        )
        
        # 파일 내용 확인 (보안상 일부만)
        if config_status['service_account_key_exists']:
            try:
                with open(config_status['service_account_key_path'], 'r') as f:
                    import json
                    key_data = json.load(f)
                    config_status['key_project_id'] = key_data.get('project_id')
                    config_status['key_client_email'] = key_data.get('client_email', '')[:20] + '...'
            except Exception as e:
                config_status['key_read_error'] = str(e)
    
    return config_status