from django.shortcuts import render
from rest_framework import generics, permissions
from .models import Client, Tag
from .serializers import DynamicClientSerializer, TagSerializer
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from django.db.models import Q
from .column_mapper import normalize_columns, map_excel_data
import pandas as pd
import io
import base64
import re
from django.core.files.uploadedfile import InMemoryUploadedFile

# Create your views here.

class DynamicClientListCreateView(generics.ListCreateAPIView):
    serializer_class = DynamicClientSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = getattr(self.request, 'user', None)
        if user and getattr(user, 'gallery_id', None):
            return Client.objects.filter(gallery_id=user.gallery_id).prefetch_related('tags')
        return Client.objects.none()

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context['request'] = self.request
        return context
    
    def create(self, request, *args, **kwargs):
        return super().create(request, *args, **kwargs)

class DynamicClientRetrieveUpdateView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = DynamicClientSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = getattr(self.request, 'user', None)
        if user and getattr(user, 'gallery_id', None):
            return Client.objects.filter(gallery_id=user.gallery_id).prefetch_related('tags')
        return Client.objects.none()

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context['request'] = self.request
        return context


# 기존 태그 API들 - ManyToMany 모델에 맞게 수정
@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def filter_clients_by_tag(request):
    """태그로 고객을 필터링합니다."""
    tag_ids = request.GET.getlist('tag_ids[]') or request.GET.getlist('tag_ids')
    
    if not tag_ids:
        return Response({'error': '태그를 지정해주세요.'}, status=status.HTTP_400_BAD_REQUEST)
    
    # 태그 중 하나라도 포함하는 고객 찾기 (OR 조건) + 갤러리 스코프
    user = getattr(request, 'user', None)
    clients_qs = Client.objects.filter(tags__id__in=tag_ids)
    if user and getattr(user, 'gallery_id', None):
        clients_qs = clients_qs.filter(gallery_id=user.gallery_id)
    clients = clients_qs.distinct()
    
    serializer = DynamicClientSerializer(clients, many=True)
    return Response(serializer.data)


# Tag CRUD API
class TagListCreateView(generics.ListCreateAPIView):
    """태그 목록 조회 및 생성"""
    serializer_class = TagSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = getattr(self.request, 'user', None)
        if user and getattr(user, 'gallery_id', None):
            return Tag.objects.filter(gallery_id=user.gallery_id)
        return Tag.objects.none()

    def perform_create(self, serializer):
        serializer.save(gallery_id=self.request.user.gallery_id)


class TagRetrieveUpdateDestroyView(generics.RetrieveUpdateDestroyAPIView):
    """태그 상세 조회, 수정, 삭제"""
    serializer_class = TagSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = getattr(self.request, 'user', None)
        if user and getattr(user, 'gallery_id', None):
            return Tag.objects.filter(gallery_id=user.gallery_id)
        return Tag.objects.none()


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def create_tag_if_not_exists(request):
    """태그가 없으면 생성하고 있으면 기존 태그 반환"""
    name = request.data.get('name', '').strip()
    color = request.data.get('color', '#3B82F6')
    
    if not name:
        return Response({'error': '태그명을 입력해주세요.'}, status=status.HTTP_400_BAD_REQUEST)
    
    tag, created = Tag.objects.get_or_create(
        name=name,
        gallery_id=getattr(request.user, 'gallery_id', None),
        defaults={'color': color}
    )
    
    serializer = TagSerializer(tag)
    response_data = serializer.data
    response_data['created'] = created
    
    return Response(response_data)


# 새로운 컬럼 매핑 API
# analyze_excel_headers 함수 제거됨 (UI에서 사용하지 않음)


# process_excel_data 함수 제거됨 (UI에서 사용하지 않음)


@api_view(['PATCH'])
@permission_classes([permissions.IsAuthenticated])
def update_client_tags_only(request, client_id):
    """
    클라이언트의 태그만 업데이트 (다른 데이터는 보존)
    """
    
    print(f"🏷️ [TAG UPDATE] update_client_tags_only 호출됨")
    print(f"🏷️ [TAG UPDATE] client_id: {client_id}")
    print(f"🏷️ [TAG UPDATE] request.data: {request.data}")
    
    try:
        client = Client.objects.get(id=client_id)
        print(f"🏷️ [TAG UPDATE] 클라이언트 찾음: {client.name} (ID: {client.id})")
        print(f"🏷️ [TAG UPDATE] 기존 태그: {[tag.name for tag in client.tags.all()]}")
    except Client.DoesNotExist:
        print(f"❌ [TAG UPDATE] 클라이언트를 찾을 수 없음: {client_id}")
        return Response({'error': '클라이언트를 찾을 수 없습니다.'}, status=status.HTTP_404_NOT_FOUND)
    
    tag_ids = request.data.get('tag_ids', [])
    print(f"🏷️ [TAG UPDATE] 받은 tag_ids: {tag_ids}")
    
    try:
        # 태그만 업데이트 (다른 필드는 건드리지 않음)
        if tag_ids:
            tags = Tag.objects.filter(id__in=tag_ids)
            if getattr(request.user, 'gallery_id', None):
                tags = tags.filter(gallery_id=request.user.gallery_id)
                print(f"🏷️ [TAG UPDATE] 갤러리 필터 적용: gallery_id={request.user.gallery_id}")
            
            tag_list = list(tags)
            print(f"🏷️ [TAG UPDATE] 찾은 태그들: {[tag.name for tag in tag_list]}")
            
            client.tags.set(tags)
            print(f"🏷️ [TAG UPDATE] 태그 설정 완료")
        else:
            client.tags.clear()
            print(f"🏷️ [TAG UPDATE] 태그 모두 제거")
        
        # updated_at만 갱신
        client.save(update_fields=['updated_at'])
        print(f"🏷️ [TAG UPDATE] 클라이언트 저장 완료")
        
        # 저장 후 태그 확인
        updated_tags = list(client.tags.all())
        print(f"🏷️ [TAG UPDATE] 저장 후 태그: {[tag.name for tag in updated_tags]}")
        
        # 업데이트된 클라이언트 정보 반환
        serializer = DynamicClientSerializer(client)
        response_data = {
            'success': True,
            'client': serializer.data,
            'message': '태그가 성공적으로 업데이트되었습니다.'
        }
        
        
        return Response(response_data)
        
    except Exception as e:
        return Response({
            'error': f'태그 업데이트 실패: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def fix_clients_without_tags(request):
    """
    태그가 없는 클라이언트들에게 기본 태그 할당
    """
    
    try:
        gallery_id = getattr(request.user, 'gallery_id', None)
        if not gallery_id:
            return Response({'error': '갤러리 ID가 없습니다.'}, status=status.HTTP_400_BAD_REQUEST)
        
        # 태그가 없는 클라이언트들 찾기
        clients_without_tags = Client.objects.filter(
            gallery_id=gallery_id,
            tags__isnull=True
        ).distinct()
        
        print(f"🔧 [FIX TAGS] 태그가 없는 클라이언트 수: {clients_without_tags.count()}")
        
        # 기본 태그 생성 또는 찾기
        default_tag, created = Tag.objects.get_or_create(
            gallery_id=gallery_id,
            name='일반고객',
            defaults={'color': '#6B7280'}
        )
        
        if created:
            print(f"🔧 [FIX TAGS] 기본 태그 생성됨: {default_tag.name}")
        else:
            print(f"🔧 [FIX TAGS] 기존 기본 태그 사용: {default_tag.name}")
        
        # 각 클라이언트에 기본 태그 할당
        fixed_count = 0
        for client in clients_without_tags:
            client.tags.add(default_tag)
            print(f"🔧 [FIX TAGS] {client.name} (ID: {client.id})에 기본 태그 할당")
            fixed_count += 1
        
        return Response({
            'success': True,
            'message': f'{fixed_count}개 클라이언트에 기본 태그가 할당되었습니다.',
            'fixed_count': fixed_count
        })
        
    except Exception as e:
        print(f"❌ [FIX TAGS] 태그 수정 실패: {e}")
        return Response({
            'error': f'태그 수정 실패: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def log_frontend_debug(request):
    """
    프론트엔드 디버그 로그를 백엔드 콘솔에 출력
    """
    
    try:
        message = request.data.get('message', '')
        data = request.data.get('data', {})
        level = request.data.get('level', 'INFO')
        
        print(f"🔍 [FRONTEND {level}] {message}")
        if data:
            import json
            print(f"🔍 [FRONTEND DATA] {json.dumps(data, indent=2, ensure_ascii=False)}")
        
        return Response({'success': True})
        
    except Exception as e:
        print(f"❌ [FRONTEND LOG ERROR] {e}")
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def process_excel_file_pandas_with_mapping(request):
    """
    pandas를 사용한 엑셀 파일 처리 (컬럼 매핑 정보 포함)
    """
    if 'file' not in request.FILES:
        return Response({'error': '파일이 필요합니다.'}, status=status.HTTP_400_BAD_REQUEST)
    
    excel_file = request.FILES['file']
    column_mappings_str = request.POST.get('column_mappings', '{}')
    
    try:
        # 매핑 정보 파싱
        import json
        column_mappings = json.loads(column_mappings_str)
        
        # pandas로 엑셀 파일 읽기
        df = pd.read_excel(excel_file, engine='openpyxl', header=0)
        df = df.dropna(how='all')
        
        
        # 🔧 Unnamed 컬럼 처리 + 중복 문제 해결 (기존 성공 로직 적용)
        cleaned_columns = []
        for i, col in enumerate(df.columns):
            # Unnamed 컬럼의 경우 첫 번째 행의 값을 헤더로 사용
            if str(col).startswith('Unnamed'):
                first_row_value = df.iloc[0, i]
                if pd.notna(first_row_value) and str(first_row_value).strip():
                    cleaned_columns.append(str(first_row_value).strip())
                else:
                    cleaned_columns.append(f'column{i+1}')
            else:
                cleaned_columns.append(str(col).strip())
        
        # 중복 컬럼명 처리
        final_columns = []
        column_counts = {}
        for col in cleaned_columns:
            if col in column_counts:
                column_counts[col] += 1
                final_columns.append(f"{col}_{column_counts[col]}")
            else:
                column_counts[col] = 0
                final_columns.append(col)
        
        # 컬럼명 적용
        df.columns = final_columns
        
        # 헤더로 사용된 첫 번째 행 제거 (Unnamed 컬럼이 있었던 경우)
        has_unnamed = any(str(original_col).startswith('Unnamed') for original_col in pd.read_excel(excel_file, engine='openpyxl', header=0).columns)
        if has_unnamed:
            df = df.iloc[1:].reset_index(drop=True)
        
        
        # 매핑 정보에 따라 컬럼명 변경 및 새 컬럼 생성 준비
        column_rename_map = {}
        new_columns_to_create = []
        
        print(f"🔍 [EXCEL DEBUG] 전달받은 매핑 정보: {column_mappings}")
        
        # 기존 컬럼 정보를 가져와서 ID -> accessor 매핑 테이블 생성
        from .models import ClientColumn
        user_gallery_id = getattr(request.user, 'gallery_id', None)
        existing_columns = ClientColumn.objects.filter(gallery_id=user_gallery_id)
        id_to_accessor_map = {str(col.id): col.accessor for col in existing_columns}
        id_to_header_map = {str(col.id): col.header for col in existing_columns}
        
        print(f"🔍 [EXCEL DEBUG] ID->accessor 매핑: {id_to_accessor_map}")
        print(f"🔍 [EXCEL DEBUG] ID->header 매핑: {id_to_header_map}")
        
        for original_header, mapped_to in column_mappings.items():
            print(f"🔍 [EXCEL DEBUG] 매핑 처리: {original_header} -> {mapped_to}")
            
            if mapped_to.startswith('new_'):
                # 새 컬럼인 경우 헤더명 그대로 사용하고 생성할 컬럼 목록에 추가
                column_rename_map[original_header] = original_header
                new_columns_to_create.append({
                    'header': original_header,
                    'accessor': original_header,  # 🔧 header와 동일하게 설정하여 데이터 매핑 일관성 유지
                    'type': 'text',
                    'order': 100 + len(new_columns_to_create)  # 기본 컬럼 이후에 배치
                })
                print(f"✅ [EXCEL DEBUG] 새 컬럼 추가: {original_header}")
            else:
                # 기존 컬럼에 매핑하는 경우 - ID를 accessor로 변환
                if mapped_to in id_to_accessor_map:
                    target_accessor = id_to_accessor_map[mapped_to]
                    column_rename_map[original_header] = target_accessor
                    print(f"✅ [EXCEL DEBUG] 기존 컬럼 매핑: {original_header} -> {target_accessor} (ID: {mapped_to})")
                else:
                    # ID를 찾을 수 없는 경우 - 새 컬럼으로 처리
                    column_rename_map[original_header] = original_header
                    new_columns_to_create.append({
                        'header': original_header,
                        'accessor': original_header,
                        'type': 'text',
                        'order': 100 + len(new_columns_to_create)
                    })
                    print(f"⚠️ [EXCEL DEBUG] ID를 찾을 수 없어 새 컬럼으로 생성: {original_header} -> {mapped_to}")
        
        print(f"🔍 [EXCEL DEBUG] 생성할 새 컬럼 목록: {new_columns_to_create}")
        print(f"🔍 [EXCEL DEBUG] 최종 컬럼 매핑: {column_rename_map}")
        
        # 새 컬럼들을 데이터베이스에 생성 (갤러리별 중복 방지)
        from .models import ClientColumn
        user_gallery_id = getattr(request.user, 'gallery_id', None)
        created_columns = []
        
        for col_data in new_columns_to_create:
            try:
                print(f"🔧 [EXCEL DEBUG] 새 컬럼 생성 시도: {col_data}")
                
                # 갤러리별 중복 체크: 같은 갤러리 내에서만 중복 확인
                existing_column = ClientColumn.objects.filter(
                    gallery_id=user_gallery_id,
                    accessor=col_data['accessor']  # accessor로 중복 체크 (더 정확함)
                ).first()
                
                if existing_column:
                    print(f"✅ [EXCEL DEBUG] 기존 컬럼 사용: {existing_column.header} (ID: {existing_column.id})")
                    created_columns.append(existing_column)
                else:
                    # 새 컬럼 생성 (갤러리 정보 포함)
                    new_column = ClientColumn.objects.create(
                        gallery_id=user_gallery_id,
                        header=col_data['header'],
                        accessor=col_data['accessor'],
                        type=col_data['type'],
                        order=col_data['order']
                    )
                    print(f"✅ [EXCEL DEBUG] 새 컬럼 생성 완료: {new_column.header} (ID: {new_column.id})")
                    created_columns.append(new_column)
                    
            except Exception as e:
                print(f"❌ [EXCEL DEBUG] 컬럼 생성 실패: {col_data['header']}, 에러: {e}")
                pass  # 컬럼 생성 실패 시 무시하고 계속
        
        print(f"🔍 [EXCEL DEBUG] 생성/확인된 컬럼 수: {len(created_columns)}")
        
        
        
        # 실제 컬럼명 변경
        df = df.rename(columns=column_rename_map)
        
        print(f"🔍 [EXCEL DEBUG] 컬럼명 변경 후 DataFrame 컬럼들: {list(df.columns)}")
        print(f"🔍 [EXCEL DEBUG] DataFrame 첫 번째 행 샘플: {df.iloc[0].to_dict() if len(df) > 0 else 'No data'}")
        
        # 나머지는 기존 pandas 로직과 동일
        df_dict = df.to_dict('records')
        
        created_count = 0
        failed_count = 0
        
        for row_data in df_dict:
            try:
                print(f"🔍 [EXCEL DEBUG] 처리할 row_data 키들: {list(row_data.keys())}")
                print(f"🔍 [EXCEL DEBUG] row_data 샘플: {dict(list(row_data.items())[:5])}")
                
                # 기본 필드 분리 - 매핑된 accessor와 원본 컬럼명 모두 확인
                name = ''
                phone = ''
                tags_data = ''
                
                # 매핑된 컬럼들을 기반으로 기본 필드 추출
                print(f"🔍 [EXCEL DEBUG] 매핑 전 row_data 키들: {list(row_data.keys())}")
                print(f"🔍 [EXCEL DEBUG] 컬럼 매핑 정보: {column_rename_map}")
                
                # 기본 필드 매핑 테이블 생성 (원본 컬럼명 -> 기본 필드)
                name_fields = ['name', '고객명', 'customer_name']
                phone_fields = ['phone', '연락처', '전화번호', '휴대폰', '핸드폰']
                category_fields = ['category', '고객분류', '고객 분류', 'tags']
                
                # row_data에서 기본 필드 추출
                keys_to_remove = []
                for key, value in row_data.items():
                    # 고객명 추출
                    if key in name_fields or any(mapped_key in name_fields for mapped_key in [column_rename_map.get(key, key)]):
                        name = str(value).strip() if value and pd.notna(value) else ''
                        keys_to_remove.append(key)
                        print(f"🔍 [EXCEL DEBUG] name 필드 데이터 추출 (key: {key}): '{name}'")
                    
                    # 연락처 추출
                    elif key in phone_fields or any(mapped_key in phone_fields for mapped_key in [column_rename_map.get(key, key)]):
                        phone = str(value).strip() if value and pd.notna(value) else ''
                        keys_to_remove.append(key)
                        print(f"🔍 [EXCEL DEBUG] phone 필드 데이터 추출 (key: {key}): '{phone}'")
                    
                    # 고객분류/태그 추출
                    elif key in category_fields or any(mapped_key in category_fields for mapped_key in [column_rename_map.get(key, key)]):
                        tags_data = str(value).strip() if value and pd.notna(value) else ''
                        keys_to_remove.append(key)
                        print(f"🔍 [EXCEL DEBUG] tags 필드 데이터 추출 (key: {key}): '{tags_data}'")
                
                # 추출한 기본 필드들을 row_data에서 제거
                for key in keys_to_remove:
                    row_data.pop(key, None)
                
                print(f"🔍 [EXCEL DEBUG] 추출된 기본 데이터: name='{name}', phone='{phone}', tags='{tags_data}'")
                
                # 나머지는 data 필드에 저장
                client_data = {key: value for key, value in row_data.items() 
                             if pd.notna(value) and str(value).strip()}
                
                print(f"🔍 [EXCEL DEBUG] 남은 client_data: {client_data}")
                
                print(f"🔍 [EXCEL DEBUG] 최종 저장될 데이터: name='{name}', phone='{phone}'")
                print(f"🔍 [EXCEL DEBUG] client_data에 저장될 데이터: {client_data}")
                
                # 빈 데이터 필터링
                clean_client_data = {}
                for key, value in client_data.items():
                    if pd.notna(value) and str(value).strip():
                        clean_client_data[key] = str(value).strip()
                
                
                client = Client.objects.create(
                    gallery_id=getattr(request.user, 'gallery_id', None),
                    name=name,
                    phone=phone,
                    data=clean_client_data
                )
                
                # 태그 처리 (고객분류 데이터가 있는 경우)
                if tags_data:
                    try:
                        # 태그명으로 기존 태그 찾거나 생성
                        tag, created = Tag.objects.get_or_create(
                            gallery_id=getattr(request.user, 'gallery_id', None),
                            name=tags_data,
                            defaults={'color': '#3B82F6'}  # 기본 파란색
                        )
                        client.tags.add(tag)
                        print(f"🔍 [EXCEL DEBUG] 태그 추가: '{tags_data}' ({'새 태그' if created else '기존 태그'})")
                    except Exception as tag_error:
                        print(f"❌ [EXCEL DEBUG] 태그 생성/할당 실패: {tag_error}")
                
                # 태그가 없으면 기본 태그 할당
                if not client.tags.exists():
                    try:
                        default_tag, created = Tag.objects.get_or_create(
                            gallery_id=getattr(request.user, 'gallery_id', None),
                            name='일반고객',
                            defaults={'color': '#6B7280'}
                        )
                        client.tags.add(default_tag)
                        print(f"🔍 [EXCEL DEBUG] 기본 태그 할당: 일반고객")
                    except Exception as tag_error:
                        print(f"❌ [EXCEL DEBUG] 기본 태그 할당 실패: {tag_error}")
                        pass  # 기본 태그 할당 실패 시 무시
                created_count += 1
                
            except Exception as row_error:
                failed_count += 1
                continue
        
        # 중복 컬럼 정리 로직 제거 - 수동 매핑으로 중복 방지 완료, 갤러리별 독립성 보장
        
        
        return Response({
            'message': f'업로드 완료: 성공 {created_count}건, 실패 {failed_count}건',
            'created_count': created_count,
            'failed_count': failed_count,
            'column_mapping': column_rename_map,
            'new_columns_created': len(new_columns_to_create)
        })
        
    except Exception as e:
        return Response({'error': f'엑셀 처리 중 오류: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

# process_excel_file_pandas 함수 제거됨 (UI에서 사용하지 않음)