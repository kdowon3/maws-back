from django.contrib import admin
from .models import SMSMessage, SMSDelivery


@admin.register(SMSMessage)
class SMSMessageAdmin(admin.ModelAdmin):
    list_display = ['gallery', 'sender', 'recipients_count', 'sent_count', 'failed_count', 'status', 'created_at']
    list_filter = ['status', 'gallery', 'created_at']
    search_fields = ['gallery__name', 'sender__username', 'message_template']
    readonly_fields = ['created_at', 'started_at', 'completed_at']
    ordering = ['-created_at']


@admin.register(SMSDelivery)
class SMSDeliveryAdmin(admin.ModelAdmin):
    list_display = ['client', 'phone_number', 'status', 'twilio_status', 'sent_at', 'created_at']
    list_filter = ['status', 'twilio_status', 'message__gallery', 'created_at']
    search_fields = ['client__name', 'phone_number', 'twilio_sid']
    readonly_fields = ['created_at', 'sent_at', 'delivered_at', 'twilio_sid']
    ordering = ['-created_at']
