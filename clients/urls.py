from django.urls import path
from .views import (
    DynamicClientListCreateView, 
    DynamicClientRetrieveUpdateView,
    TagListCreateView,
    TagRetrieveUpdateDestroyView,
    create_tag_if_not_exists,
    filter_clients_by_tag,
    analyze_excel_headers,
    process_excel_data,
    update_client_tags_only,
    process_excel_file_pandas,
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
    
    # 기존 엑셀 처리 API (복잡한 로직)
    path('excel/analyze-headers/', analyze_excel_headers, name='analyze-excel-headers'),
    path('excel/process-data/', process_excel_data, name='process-excel-data'),
    
    # 새로운 pandas 기반 엑셀 처리 API (단순화된 로직)
    path('excel/upload/', process_excel_file_pandas, name='process-excel-file-pandas'),
    path('excel/upload-with-mapping/', process_excel_file_pandas_with_mapping, name='process-excel-file-pandas-with-mapping'),
    
    # 태그 전용 업데이트 API
    path('clients/<int:client_id>/tags/', update_client_tags_only, name='update-client-tags-only'),
] 