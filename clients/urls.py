from django.urls import path
from .views import (
    DynamicClientListCreateView, 
    DynamicClientRetrieveUpdateView,
    TagListCreateView,
    TagRetrieveUpdateDestroyView,
    create_tag_if_not_exists,
    filter_clients_by_tag,
    update_client_tags_only,
    fix_clients_without_tags,
    log_frontend_debug,
    process_excel_file_pandas_with_mapping
)

urlpatterns = [
    path('clients/', DynamicClientListCreateView.as_view(), name='dynamic-client-list-create'),
    path('clients/<int:pk>/', DynamicClientRetrieveUpdateView.as_view(), name='dynamic-client-detail-update'),
    
    # 태그 CRUD API
    path('tags/', TagListCreateView.as_view(), name='tag-list-create'),
    path('tags/<int:pk>/', TagRetrieveUpdateDestroyView.as_view(), name='tag-detail-update-delete'),
    path('tags/create-if-not-exists/', create_tag_if_not_exists, name='create-tag-if-not-exists'),
    path('clients/filter-by-tag/', filter_clients_by_tag, name='filter-clients-by-tag'),
    
    # 엑셀 처리 API (UI에서 실제 사용하는 것만 유지)
    path('excel/upload-with-mapping/', process_excel_file_pandas_with_mapping, name='process-excel-file-pandas-with-mapping'),
    
    # 태그 전용 업데이트 API
    path('clients/<int:client_id>/tags/', update_client_tags_only, name='update-client-tags-only'),
    
    # 태그 없는 클라이언트 수정 API
    path('clients/fix-tags/', fix_clients_without_tags, name='fix-clients-without-tags'),
    
    # 프론트엔드 디버그 로그 API
    path('debug/log/', log_frontend_debug, name='log-frontend-debug'),
] 