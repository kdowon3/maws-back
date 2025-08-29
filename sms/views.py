from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from django.utils import timezone
from .services import BulkSMSService
from .models import SMSMessage, SMSDelivery


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def send_bulk_sms(request):
    """대량 SMS 발송 API"""
    
    try:
        # 요청 데이터 검증
        client_ids = request.data.get('client_ids', [])
        message = request.data.get('message', '').strip()
        
        if not client_ids:
            return Response({
                'success': False,
                'error': '발송 대상 고객을 선택해주세요.'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        if not message:
            return Response({
                'success': False,
                'error': '메시지 내용을 입력해주세요.'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        if len(message) > 1000:
            return Response({
                'success': False,
                'error': '메시지는 1000자를 초과할 수 없습니다.'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # 사용자 갤러리 정보 확인
        if not hasattr(request.user, 'gallery') or not request.user.gallery:
            return Response({
                'success': False,
                'error': '갤러리 정보가 없습니다. 관리자에게 문의하세요.'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # SMS 발송 권한 확인 (역할 기반)
        allowed_roles = ['owner', 'manager', 'staff']  # SMS 발송 가능한 역할
        if request.user.role not in allowed_roles:
            return Response({
                'success': False,
                'error': 'SMS 발송 권한이 없습니다.'
            }, status=status.HTTP_403_FORBIDDEN)
        
        # 대량 SMS 발송 서비스 호출
        bulk_sms_service = BulkSMSService()
        result = bulk_sms_service.send_bulk_sms(
            gallery=request.user.gallery,
            sender=request.user,
            client_ids=client_ids,
            message_template=message
        )
        
        if result['success']:
            return Response({
                'success': True,
                'message': f"{result['sent_count']}명에게 발송 완료",
                'data': {
                    'message_id': result['message_id'],
                    'total_count': result['total_count'],
                    'sent_count': result['sent_count'],
                    'failed_count': result['failed_count'],
                    'results': result.get('results', [])
                }
            }, status=status.HTTP_200_OK)
        else:
            return Response({
                'success': False,
                'error': result.get('error', '발송 중 오류가 발생했습니다.'),
                'data': {
                    'message_id': result['message_id'],
                    'failed_count': result['failed_count']
                }
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    except Exception as e:
        return Response({
            'success': False,
            'error': f'서버 오류: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def sms_history(request):
    """SMS 발송 이력 조회 API"""
    
    try:
        # 사용자 갤러리의 SMS 메시지들만 조회
        messages = SMSMessage.objects.filter(
            gallery=request.user.gallery
        ).order_by('-created_at')
        
        # 페이지네이션 (간단히 최근 20건)
        messages = messages[:20]
        
        history_data = []
        for msg in messages:
            history_data.append({
                'id': msg.id,
                'message_template': msg.message_template[:50] + '...' if len(msg.message_template) > 50 else msg.message_template,
                'recipients_count': msg.recipients_count,
                'sent_count': msg.sent_count,
                'failed_count': msg.failed_count,
                'status': msg.get_status_display(),
                'created_at': msg.created_at.strftime('%Y-%m-%d %H:%M'),
                'sender': msg.sender.username
            })
        
        return Response({
            'success': True,
            'data': history_data
        }, status=status.HTTP_200_OK)
    
    except Exception as e:
        return Response({
            'success': False,
            'error': f'이력 조회 오류: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def sms_detail(request, message_id):
    """개별 SMS 발송 상세 조회 API"""
    
    try:
        # SMS 메시지 조회 (갤러리 권한 확인)
        sms_message = SMSMessage.objects.filter(
            id=message_id,
            gallery=request.user.gallery
        ).first()
        
        if not sms_message:
            return Response({
                'success': False,
                'error': '해당 메시지를 찾을 수 없습니다.'
            }, status=status.HTTP_404_NOT_FOUND)
        
        # 개별 발송 기록들 조회
        deliveries = SMSDelivery.objects.filter(
            message=sms_message
        ).order_by('-created_at')
        
        delivery_data = []
        for delivery in deliveries:
            delivery_data.append({
                'client_name': delivery.client.name,
                'phone_number': delivery.phone_number,
                'status': delivery.get_status_display(),
                'twilio_status': delivery.twilio_status,
                'sent_at': delivery.sent_at.strftime('%Y-%m-%d %H:%M:%S') if delivery.sent_at else None,
                'error_message': delivery.error_message
            })
        
        return Response({
            'success': True,
            'data': {
                'message_info': {
                    'id': sms_message.id,
                    'message_template': sms_message.message_template,
                    'recipients_count': sms_message.recipients_count,
                    'sent_count': sms_message.sent_count,
                    'failed_count': sms_message.failed_count,
                    'status': sms_message.get_status_display(),
                    'created_at': sms_message.created_at.strftime('%Y-%m-%d %H:%M:%S'),
                    'sender': sms_message.sender.username
                },
                'deliveries': delivery_data
            }
        }, status=status.HTTP_200_OK)
    
    except Exception as e:
        return Response({
            'success': False,
            'error': f'상세 조회 오류: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
