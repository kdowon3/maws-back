from django.urls import path
from . import views

app_name = 'sms'

urlpatterns = [
    path('send/', views.send_bulk_sms, name='send_bulk_sms'),
    path('history/', views.sms_history, name='sms_history'),
    path('detail/<int:message_id>/', views.sms_detail, name='sms_detail'),
]