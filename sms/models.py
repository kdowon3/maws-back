from django.db import models
from django.contrib.auth import get_user_model
from accounts.models import Gallery
from clients.models import Client

User = get_user_model()


class SMSMessage(models.Model):
    """SMS 메시지 발송 기록"""
    
    STATUS_CHOICES = [
        ('pending', '대기중'),
        ('sending', '발송중'),
        ('completed', '완료'),
        ('failed', '실패'),
        ('cancelled', '취소'),
    ]
    
    # 기본 정보
    gallery = models.ForeignKey(Gallery, on_delete=models.CASCADE, related_name='sms_messages')
    sender = models.ForeignKey(User, on_delete=models.CASCADE, related_name='sent_sms_messages')
    
    # 메시지 내용
    message_template = models.TextField(help_text="전송된 메시지 템플릿")
    
    # 발송 대상
    recipients_count = models.PositiveIntegerField(default=0, help_text="발송 대상자 수")
    
    # 상태 및 결과
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    sent_count = models.PositiveIntegerField(default=0, help_text="실제 발송된 건수")
    failed_count = models.PositiveIntegerField(default=0, help_text="실패한 건수")
    
    # 시간 정보
    created_at = models.DateTimeField(auto_now_add=True)
    started_at = models.DateTimeField(null=True, blank=True, help_text="발송 시작 시간")
    completed_at = models.DateTimeField(null=True, blank=True, help_text="발송 완료 시간")
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = 'SMS 메시지'
        verbose_name_plural = 'SMS 메시지들'
    
    def __str__(self):
        return f"{self.gallery.name} - {self.created_at.strftime('%Y-%m-%d %H:%M')}"


class SMSDelivery(models.Model):
    """개별 SMS 발송 기록"""
    
    STATUS_CHOICES = [
        ('pending', '대기중'),
        ('queued', '발송대기'),
        ('sent', '발송완료'),
        ('delivered', '전달완료'),
        ('failed', '실패'),
        ('undelivered', '전달실패'),
    ]
    
    # 관계
    message = models.ForeignKey(SMSMessage, on_delete=models.CASCADE, related_name='deliveries')
    client = models.ForeignKey(Client, on_delete=models.CASCADE, related_name='sms_deliveries')
    
    # 발송 정보
    phone_number = models.CharField(max_length=20, help_text="발송된 전화번호")
    personalized_message = models.TextField(help_text="개인화된 메시지 내용")
    
    # Twilio 정보
    twilio_sid = models.CharField(max_length=100, null=True, blank=True, help_text="Twilio 메시지 SID")
    twilio_status = models.CharField(max_length=50, null=True, blank=True, help_text="Twilio 상태")
    
    # 상태 및 오류
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    error_message = models.TextField(null=True, blank=True, help_text="오류 메시지")
    
    # 시간 정보
    created_at = models.DateTimeField(auto_now_add=True)
    sent_at = models.DateTimeField(null=True, blank=True, help_text="실제 발송 시간")
    delivered_at = models.DateTimeField(null=True, blank=True, help_text="전달 확인 시간")
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = 'SMS 발송 기록'
        verbose_name_plural = 'SMS 발송 기록들'
    
    def __str__(self):
        return f"{self.client.name} - {self.phone_number} ({self.status})"
