from django.contrib import admin
from django.contrib import messages
from django.http import HttpResponseRedirect
from django.urls import path
from django.shortcuts import render
from django.db import transaction
from .models import Client
from api.models import ClientColumn

@admin.action(description='선택된 고객 데이터 삭제')
def delete_selected_clients(modeladmin, request, queryset):
    """선택된 고객들을 삭제하는 액션"""
    count = queryset.count()
    queryset.delete()
    messages.success(request, f'{count}개의 고객 데이터가 삭제되었습니다.')

@admin.action(description='⚠️ 모든 고객 데이터 초기화 (위험)')
def reset_all_clients(modeladmin, request, queryset):
    """모든 고객 데이터를 삭제하는 위험한 액션"""
    if 'confirmed' in request.POST:
        with transaction.atomic():
            count = Client.objects.count()
            Client.objects.all().delete()
            messages.success(request, f'모든 고객 데이터({count}개)가 초기화되었습니다.')
        return HttpResponseRedirect(request.get_full_path())
    
    # 확인 페이지 렌더링
    context = {
        'title': '⚠️ 위험: 모든 고객 데이터 초기화',
        'message': '정말로 모든 고객 데이터를 삭제하시겠습니까?',
        'warning': '이 작업은 되돌릴 수 없습니다!',
        'total_count': Client.objects.count(),
        'action': 'reset_all_clients'
    }
    return render(request, 'admin/confirmation.html', context)

@admin.action(description='⚠️ 모든 컬럼 구조 초기화 (위험)')
def reset_all_columns(modeladmin, request, queryset):
    """모든 컬럼 구조를 삭제하는 위험한 액션"""
    if 'confirmed' in request.POST:
        with transaction.atomic():
            count = ClientColumn.objects.count()
            ClientColumn.objects.all().delete()
            messages.success(request, f'모든 컬럼 구조({count}개)가 초기화되었습니다.')
        return HttpResponseRedirect(request.get_full_path())
    
    # 확인 페이지 렌더링
    context = {
        'title': '⚠️ 위험: 모든 컬럼 구조 초기화',
        'message': '정말로 모든 컬럼 구조를 삭제하시겠습니까?',
        'warning': '이 작업은 되돌릴 수 없으며, 프론트엔드 테이블 구조에 영향을 줍니다!',
        'total_count': ClientColumn.objects.count(),
        'action': 'reset_all_columns'
    }
    return render(request, 'admin/confirmation.html', context)

class ClientAdmin(admin.ModelAdmin):
    list_display = ['id', 'name', 'phone', 'created_at', 'updated_at']
    list_filter = ['created_at', 'updated_at']
    search_fields = ['name', 'phone']
    readonly_fields = ['created_at', 'updated_at']
    
    actions = [
        delete_selected_clients,
        reset_all_clients,
        reset_all_columns,
    ]
    
    def get_queryset(self, request):
        return super().get_queryset(request).order_by('-created_at')

admin.site.register(Client, ClientAdmin)
