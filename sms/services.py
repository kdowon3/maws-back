import os
import re
import time
from django.conf import settings
from django.utils import timezone
from twilio.rest import Client as TwilioClient
from twilio.base.exceptions import TwilioException
from .models import SMSMessage, SMSDelivery
from clients.models import Client


class TwilioSMSService:
    """Twilio SMS 발송 서비스"""
    
    def __init__(self):
        self.account_sid = getattr(settings, 'TWILIO_ACCOUNT_SID', None)
        self.auth_token = getattr(settings, 'TWILIO_AUTH_TOKEN', None)
        self.from_number = getattr(settings, 'TWILIO_PHONE_NUMBER', None)
        
        if not all([self.account_sid, self.auth_token, self.from_number]):
            raise ValueError("Twilio 환경변수가 설정되지 않았습니다. TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, TWILIO_PHONE_NUMBER를 확인하세요.")
        
        self.client = TwilioClient(self.account_sid, self.auth_token)
    
    def send_sms(self, to_number, message):
        """개별 SMS 발송"""
        try:
            # 전화번호 형식 정리
            formatted_number = self.format_phone_number(to_number)
            
            # Twilio API 호출
            twilio_message = self.client.messages.create(
                body=message,
                from_=self.from_number,
                to=formatted_number
            )
            
            return {
                'success': True,
                'sid': twilio_message.sid,
                'status': twilio_message.status,
                'error': None
            }
            
        except TwilioException as e:
            return {
                'success': False,
                'sid': None,
                'status': 'failed',
                'error': str(e)
            }
        except Exception as e:
            return {
                'success': False,
                'sid': None,
                'status': 'failed',
                'error': f"예상치 못한 오류: {str(e)}"
            }
    
    def format_phone_number(self, phone_number):
        """전화번호를 국제 형식으로 변환"""
        if not phone_number:
            raise ValueError("전화번호가 비어있습니다.")
        
        # 숫자만 추출
        digits_only = re.sub(r'\D', '', phone_number)
        
        # 한국 번호 형식 처리
        if digits_only.startswith('010'):
            return f'+82{digits_only[1:]}'  # 010 -> +8210
        elif digits_only.startswith('82'):
            return f'+{digits_only}'  # 82 -> +82
        elif digits_only.startswith('1') and len(digits_only) == 11:
            return f'+{digits_only}'  # 미국 번호 (테스트용)
        else:
            # 기타 형식은 그대로 + 추가
            return f'+{digits_only}' if not digits_only.startswith('+') else digits_only
    
    def render_template(self, template, client, gallery):
        """메시지 템플릿에서 변수 치환"""
        if not template:
            return template
        
        # 사용 가능한 변수들
        variables = {
            '{{고객명}}': client.name or '고객',
            '{{갤러리명}}': gallery.name or '갤러리',
            '{{갤러리_연락처}}': gallery.phone or '',
            '{{갤러리_주소}}': gallery.address or '',
        }
        
        # 변수 치환
        rendered_message = template
        for placeholder, value in variables.items():
            rendered_message = rendered_message.replace(placeholder, str(value))
        
        return rendered_message


class BulkSMSService:
    """대량 SMS 발송 서비스"""
    
    def __init__(self):
        self.twilio_service = TwilioSMSService()
    
    def send_bulk_sms(self, gallery, sender, client_ids, message_template):
        """대량 SMS 발송 처리"""
        
        # SMS 메시지 레코드 생성
        sms_message = SMSMessage.objects.create(
            gallery=gallery,
            sender=sender,
            message_template=message_template,
            recipients_count=len(client_ids),
            status='sending',
            started_at=timezone.now()
        )
        
        # 발송 가능한 고객들 필터링
        eligible_clients = self.get_eligible_clients(gallery, client_ids)
        
        sent_count = 0
        failed_count = 0
        results = []
        
        try:
            for client in eligible_clients:
                # 개인화된 메시지 생성
                personalized_message = self.twilio_service.render_template(
                    message_template, client, gallery
                )
                
                # 개별 발송 기록 생성
                delivery = SMSDelivery.objects.create(
                    message=sms_message,
                    client=client,
                    phone_number=client.phone,
                    personalized_message=personalized_message,
                    status='pending'
                )
                
                # SMS 발송
                result = self.twilio_service.send_sms(client.phone, personalized_message)
                
                # 결과 업데이트
                if result['success']:
                    delivery.status = 'sent'
                    delivery.twilio_sid = result['sid']
                    delivery.twilio_status = result['status']
                    delivery.sent_at = timezone.now()
                    sent_count += 1
                else:
                    delivery.status = 'failed'
                    delivery.error_message = result['error']
                    failed_count += 1
                
                delivery.save()
                
                # 점진적 발송을 위한 대기 시간 (API 과부하 방지)
                delay = getattr(settings, 'SMS_SEND_DELAY', 1.5)
                time.sleep(delay)
                
                # 결과 수집
                results.append({
                    'client_id': client.id,
                    'client_name': client.name,
                    'phone': client.phone,
                    'success': result['success'],
                    'sid': result['sid'],
                    'error': result['error']
                })
            
            # SMS 메시지 상태 업데이트
            sms_message.sent_count = sent_count
            sms_message.failed_count = failed_count
            sms_message.status = 'completed'
            sms_message.completed_at = timezone.now()
            sms_message.save()
            
            return {
                'success': True,
                'message_id': sms_message.id,
                'total_count': len(eligible_clients),
                'sent_count': sent_count,
                'failed_count': failed_count,
                'results': results
            }
            
        except Exception as e:
            # 전체 발송 실패 시
            sms_message.status = 'failed'
            sms_message.failed_count = sms_message.recipients_count
            sms_message.completed_at = timezone.now()
            sms_message.save()
            
            return {
                'success': False,
                'message_id': sms_message.id,
                'error': str(e),
                'total_count': len(client_ids),
                'sent_count': 0,
                'failed_count': len(client_ids),
                'results': []
            }
    
    def get_eligible_clients(self, gallery, client_ids):
        """발송 가능한 고객들만 필터링"""
        
        clients = Client.objects.filter(
            id__in=client_ids,
            gallery=gallery
        )
        
        eligible_clients = []
        
        for client in clients:
            # 전화번호 확인
            if not client.phone or client.phone.strip() == '':
                continue
            
            # 수신 동의 확인 (data 필드의 문자수신동의)
            if hasattr(client, 'data') and client.data:
                if client.data.get('문자수신동의') == False:
                    continue
            
            eligible_clients.append(client)
        
        return eligible_clients