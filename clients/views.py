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
        print(f"🚀 [CLIENT CREATE DEBUG] 호출됨!")
        print(f"[CLIENT CREATE DEBUG] User: {request.user}")
        print(f"[CLIENT CREATE DEBUG] User gallery_id: {getattr(request.user, 'gallery_id', None)}")
        print(f"[CLIENT CREATE DEBUG] Request data: {request.data}")
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
        serializer.save(gallery=self.request.user.gallery)


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
        defaults={'color': color}
    )
    
    serializer = TagSerializer(tag)
    response_data = serializer.data
    response_data['created'] = created
    
    return Response(response_data)


# 새로운 컬럼 매핑 API
@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def analyze_excel_headers(request):
    """
    엑셀 헤더를 분석하여 자동 매핑 정보 반환
    """
    headers = request.data.get('headers', [])
    
    if not headers:
        return Response({'error': '헤더 정보가 필요합니다.'}, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        # 컬럼 매핑 생성
        column_mapping = normalize_columns(headers)
        
        return Response({
            'success': True,
            'mapping': column_mapping,
            'message': f'{len(headers)}개 헤더가 성공적으로 매핑되었습니다.'
        })
        
    except Exception as e:
        return Response({
            'error': f'헤더 분석 실패: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def process_excel_data(request):
    """
    엑셀 데이터를 처리하여 매핑된 형태로 반환
    """
    excel_data = request.data.get('data', [])
    
    if not excel_data:
        return Response({'error': '엑셀 데이터가 필요합니다.'}, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        # 자동 매핑 처리
        mapped_data, column_mapping = map_excel_data(excel_data)
        
        return Response({
            'success': True,
            'mapped_data': mapped_data,
            'column_mapping': column_mapping,
            'total_rows': len(mapped_data),
            'message': '엑셀 데이터가 성공적으로 처리되었습니다.'
        })
        
    except Exception as e:
        return Response({
            'error': f'데이터 처리 실패: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['PATCH'])
@permission_classes([permissions.IsAuthenticated])
def update_client_tags_only(request, client_id):
    """
    클라이언트의 태그만 업데이트 (다른 데이터는 보존)
    """
    print(f"🚀 update_client_tags_only 호출됨")
    print(f"   - client_id: {client_id}")
    print(f"   - request.data: {request.data}")
    
    try:
        client = Client.objects.get(id=client_id)
        print(f"   - 클라이언트 찾음: {client.name}")
    except Client.DoesNotExist:
        print(f"   - 클라이언트를 찾을 수 없음: {client_id}")
        return Response({'error': '클라이언트를 찾을 수 없습니다.'}, status=status.HTTP_404_NOT_FOUND)
    
    tag_ids = request.data.get('tag_ids', [])
    print(f"🏷️ 태그 업데이트: client_id={client_id}, tag_ids={tag_ids}")
    
    try:
        # 태그만 업데이트 (다른 필드는 건드리지 않음)
        if tag_ids:
            tags = Tag.objects.filter(id__in=tag_ids)
            if getattr(request.user, 'gallery_id', None):
                tags = tags.filter(gallery_id=request.user.gallery_id)
            print(f"🏷️ 설정할 태그: {[tag.name for tag in tags]}")
            print(f"🏷️ 설정할 태그 ID들: {[tag.id for tag in tags]}")
            client.tags.set(tags)
            print(f"🏷️ 태그 설정 후 클라이언트 태그: {[tag.name for tag in client.tags.all()]}")
        else:
            print("🏷️ 모든 태그 제거")
            client.tags.clear()
        
        # updated_at만 갱신
        client.save(update_fields=['updated_at'])
        print(f"🏷️ 클라이언트 저장 완료")
        
        # 업데이트된 클라이언트 정보 반환
        serializer = DynamicClientSerializer(client)
        response_data = {
            'success': True,
            'client': serializer.data,
            'message': '태그가 성공적으로 업데이트되었습니다.'
        }
        
        print(f"✅ 태그 업데이트 완료: client_id={client_id}")
        print(f"   - 응답 데이터: {response_data}")
        
        return Response(response_data)
        
    except Exception as e:
        print(f"❌ 태그 업데이트 실패: {e}")
        return Response({
            'error': f'태그 업데이트 실패: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


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
        print(f"📊 받은 컬럼 매핑: {column_mappings}")
        
        # pandas로 엑셀 파일 읽기
        df = pd.read_excel(excel_file, engine='openpyxl', header=0)
        df = df.dropna(how='all')
        
        print(f"📊 원본 엑셀 컬럼: {list(df.columns)}")
        
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
            print("📊 첫 번째 행(헤더 데이터) 제거됨")
        
        print(f"📊 정리된 엑셀 컬럼: {list(df.columns)}")
        
        # 매핑 정보에 따라 컬럼명 변경 (한국어 헤더명 사용)
        column_rename_map = {}
        new_columns_to_create = []
        
        for original_header, mapped_to in column_mappings.items():
            if mapped_to.startswith('new_'):
                # 새 컬럼인 경우 헤더명 그대로 사용하고 생성할 컬럼 목록에 추가
                column_rename_map[original_header] = original_header
                new_columns_to_create.append({
                    'header': original_header,
                    'accessor': original_header,  # 🔧 header와 동일하게 설정하여 데이터 매핑 일관성 유지
                    'type': 'text',
                    'order': 100 + len(new_columns_to_create)  # 기본 컬럼 이후에 배치
                })
                print(f"📝 새 컬럼 준비: {original_header} (accessor: {original_header})")
            else:
                # 기존 컬럼에 매핑하는 경우 (한국어 헤더명으로 매핑)
                column_rename_map[original_header] = mapped_to
        
        # 새 컬럼들을 데이터베이스에 생성 (중복 방지 강화)
        from api.models import ClientColumn
        created_columns = []
        for col_data in new_columns_to_create:
            try:
                # 더 엄격한 중복 체크: header와 accessor 모두 확인
                existing_column = ClientColumn.objects.filter(
                    header=col_data['header']
                ).first()
                
                if existing_column:
                    print(f"⚠️ 이미 존재하는 컬럼: {col_data['header']} (ID: {existing_column.id})")
                    created_columns.append(existing_column)
                else:
                    # 새 컬럼 생성
                    new_column = ClientColumn.objects.create(
                        header=col_data['header'],
                        accessor=col_data['accessor'],
                        type=col_data['type'],
                        order=col_data['order']
                    )
                    print(f"✅ 새 컬럼 생성: {col_data['header']} (ID: {new_column.id})")
                    created_columns.append(new_column)
                    
            except Exception as e:
                print(f"❌ 컬럼 생성 실패: {col_data['header']} - {e}")
        
        print(f"📊 처리된 컬럼 수: {len(created_columns)}개")
        
        print(f"📊 컬럼 리네임 맵: {column_rename_map}")
        
        # 실제 컬럼명 변경
        df = df.rename(columns=column_rename_map)
        
        print(f"📊 변경된 컬럼: {list(df.columns)}")
        
        # 나머지는 기존 pandas 로직과 동일
        df_dict = df.to_dict('records')
        
        created_count = 0
        failed_count = 0
        
        for row_data in df_dict:
            try:
                # 기본 필드 분리 (한국어 헤더명으로 통일)
                name = row_data.pop('고객명', '')
                phone = row_data.pop('연락처', '')
                
                # 고객분류는 별도 처리 (태그 관련)
                tags_data = row_data.pop('고객분류', '')
                
                # 나머지는 data 필드에 저장 (한국어 헤더명 그대로)
                client_data = {key: value for key, value in row_data.items() 
                             if pd.notna(value) and str(value).strip()}
                
                # 클라이언트 생성 (더 안전한 데이터 처리)
                client_name = str(name).strip() if name and pd.notna(name) else ''
                client_phone = str(phone).strip() if phone and pd.notna(phone) else ''
                
                # 빈 데이터 필터링
                clean_client_data = {}
                for key, value in client_data.items():
                    if pd.notna(value) and str(value).strip():
                        clean_client_data[key] = str(value).strip()
                
                print(f"📝 클라이언트 생성: {client_name} ({client_phone}) - 데이터 필드 {len(clean_client_data)}개")
                print(f"📝 데이터 필드 내용: {clean_client_data}")
                
                print(f"[EXCEL CREATE DEBUG] User: {request.user}")
                print(f"[EXCEL CREATE DEBUG] User gallery: {getattr(request.user, 'gallery', None)}")
                print(f"[EXCEL CREATE DEBUG] User gallery_id: {getattr(request.user, 'gallery_id', None)}")
                client = Client.objects.create(
                    gallery=getattr(request.user, 'gallery', None),
                    name=client_name,
                    phone=client_phone,
                    data=clean_client_data
                )
                
                # 기본 태그 할당 확인 (Client.save()에서 자동 처리되지만 명시적으로 확인)
                if not client.tags.exists():
                    try:
                        default_tag, created = Tag.objects.get_or_create(
                            gallery=getattr(request.user, 'gallery', None),
                            name='일반고객',
                            defaults={'color': '#6B7280'}
                        )
                        client.tags.add(default_tag)
                        print(f"✅ {client.name}에게 기본 태그 '{default_tag.name}' 할당 완료")
                    except Exception as tag_error:
                        print(f"⚠️ 기본 태그 할당 실패: {tag_error}")
                created_count += 1
                
            except Exception as row_error:
                print(f"❌ 행 처리 실패: {row_error}")
                failed_count += 1
                continue
        
        # 중복 컬럼 정리 (업로드 후)
        try:
            from django.db.models import Min
            from collections import defaultdict
            
            # 헤더별로 그룹화하여 중복 찾기
            header_groups = defaultdict(list)
            all_columns = ClientColumn.objects.all()
            
            for col in all_columns:
                header_groups[col.header.lower().strip()].append(col)
            
            # 중복 컬럼 정리
            cleaned_count = 0
            for header, columns in header_groups.items():
                if len(columns) > 1:
                    # 가장 낮은 order를 가진 컬럼만 남기고 나머지 삭제
                    columns.sort(key=lambda x: (x.order, x.id))
                    keep_column = columns[0]
                    
                    for col in columns[1:]:
                        print(f"🗑️ 중복 컬럼 삭제: {col.header} (ID: {col.id}, order: {col.order})")
                        col.delete()
                        cleaned_count += 1
            
            if cleaned_count > 0:
                print(f"🧹 중복 컬럼 정리 완료: {cleaned_count}개 삭제")
                
        except Exception as cleanup_error:
            print(f"⚠️ 중복 컬럼 정리 실패: {cleanup_error}")
        
        print(f"📊 최종 결과: 성공 {created_count}건, 실패 {failed_count}건")
        print(f"📊 생성된 새 컬럼: {[col['header'] for col in new_columns_to_create]}")
        
        return Response({
            'message': f'업로드 완료: 성공 {created_count}건, 실패 {failed_count}건',
            'created_count': created_count,
            'failed_count': failed_count,
            'column_mapping': column_rename_map,
            'new_columns_created': len(new_columns_to_create),
            'duplicates_cleaned': cleaned_count if 'cleaned_count' in locals() else 0
        })
        
    except Exception as e:
        print(f"❌ pandas 처리 실패: {e}")
        return Response({'error': f'엑셀 처리 중 오류: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def process_excel_file_pandas(request):
    """
    pandas를 사용한 엑셀 파일 처리 (단순화된 로직)
    """
    if 'file' not in request.FILES:
        return Response({'error': '파일이 필요합니다.'}, status=status.HTTP_400_BAD_REQUEST)
    
    excel_file = request.FILES['file']
    
    try:
        # 1. pandas로 엑셀 파일 읽기 (헤더 명시적 지정)
        df = pd.read_excel(excel_file, engine='openpyxl', header=0)
        
        # 2. 데이터 정리
        # 빈 행 제거
        df = df.dropna(how='all')
        
        print(f"📊 원본 엑셀 컬럼: {list(df.columns)}")
        
        # 컬럼명 정리 (Unnamed 컬럼 처리)
        cleaned_columns = []
        for i, col in enumerate(df.columns):
            if str(col).startswith('Unnamed'):
                # Unnamed 컬럼의 경우 첫 번째 행의 값을 헤더로 사용
                if len(df) > 0:
                    first_row_value = df.iloc[0, i]
                    if pd.notna(first_row_value) and str(first_row_value).strip():
                        cleaned_columns.append(str(first_row_value).strip())
                    else:
                        cleaned_columns.append(f'컬럼_{i+1}')
                else:
                    cleaned_columns.append(f'컬럼_{i+1}')
            else:
                cleaned_columns.append(str(col).strip() if col is not None else f'컬럼_{i+1}')
        
        # 새로운 컬럼명 적용
        df.columns = cleaned_columns
        print(f"🔧 정리된 컬럼: {list(df.columns)}")
        
        # Unnamed 컬럼이 있었다면 첫 번째 행은 헤더였으므로 제거
        original_columns = [str(col) for col in pd.read_excel(excel_file, engine='openpyxl', header=0).columns]
        has_unnamed = any(col.startswith('Unnamed') for col in original_columns)
        
        if has_unnamed:
            df = df.iloc[1:].reset_index(drop=True)
            print(f"📋 헤더 행 제거 후 데이터 행 수: {len(df)}")
        
        print(f"📋 최종 데이터 샘플:")
        if len(df) > 0:
            print(f"첫 번째 행: {df.iloc[0].to_dict()}")
        
        # 3. 컬럼 매핑 (개선된 규칙 기반 + 중복 방지)
        column_mapping = {}
        processed_columns = {}
        mapped_fields = set()  # 이미 매핑된 필드 추적
        
        print(f"🔍 컬럼 매핑 시작: {df.columns.tolist()}")
        
        for original_col in df.columns:
            original_col = str(original_col).strip()
            
            # 이미 매핑된 필드는 건너뛰기
            if original_col in mapped_fields:
                print(f"⏭️ 이미 매핑됨, 건너뛰기: {original_col}")
                continue
            
            # 기본 매핑 규칙 (더 포괄적)
            if any(keyword in original_col for keyword in ['고객명', '이름', '성명', '컬렉터명', '성함']):
                if 'name' not in processed_columns:  # 중복 방지
                    processed_columns['name'] = original_col
                    column_mapping[original_col] = '고객명'
                    mapped_fields.add(original_col)
                    print(f"✅ 고객명 매핑: {original_col} → name")
            elif any(keyword in original_col for keyword in ['연락처', '전화', '휴대폰', '핸드폰', '전화번호']):
                if 'phone' not in processed_columns:  # 중복 방지
                    processed_columns['phone'] = original_col  
                    column_mapping[original_col] = '연락처'
                    mapped_fields.add(original_col)
                    print(f"✅ 연락처 매핑: {original_col} → phone")
            elif '주소' in original_col:
                if 'address' not in processed_columns:  # 중복 방지
                    processed_columns['address'] = original_col
                    column_mapping[original_col] = '주소'
                    mapped_fields.add(original_col)
                    print(f"✅ 주소 매핑: {original_col} → address")
            elif '이메일' in original_col or 'email' in original_col.lower():
                if 'email' not in processed_columns:  # 중복 방지
                    processed_columns['email'] = original_col
                    column_mapping[original_col] = '이메일'
                    mapped_fields.add(original_col)
                    print(f"✅ 이메일 매핑: {original_col} → email")
            else:
                # 동적 필드로 처리 (원본 헤더명 보존)
                if original_col and not original_col.startswith('컬럼_'):
                    processed_columns[original_col] = original_col
                    column_mapping[original_col] = original_col
                    mapped_fields.add(original_col)
                    print(f"📝 동적 필드: {original_col} → {original_col}")
        
        print(f"📋 최종 processed_columns: {processed_columns}")
        print(f"📋 최종 column_mapping: {column_mapping}")
        
        # 4. 데이터 변환
        processed_data = []
        for _, row in df.iterrows():
            client_data = {}
            dynamic_data = {}
            
            for field_key, original_col in processed_columns.items():
                value = row[original_col]
                
                # NaN 값 처리
                if pd.isna(value):
                    value = ''
                else:
                    value = str(value).strip()
                
                # 기본 필드와 동적 필드 분리
                if field_key in ['name', 'phone']:
                    client_data[field_key] = value
                else:
                    dynamic_data[field_key] = value
            
            # 클라이언트 데이터 구조 생성
            processed_data.append({
                'name': client_data.get('name', ''),
                'phone': client_data.get('phone', ''),
                'data': dynamic_data
            })
        
        # 5. 실제 데이터베이스 저장
        success_count = 0
        error_count = 0
        error_details = []
        
        for i, client_data in enumerate(processed_data):
            try:
                # 중복 확인 (이름 + 전화번호 기준)
                existing_client = None
                if client_data['name'] and client_data['phone']:
                    existing_client_qs = Client.objects.filter(
                        name=client_data['name'],
                        phone=client_data['phone']
                    )
                    if getattr(request.user, 'gallery_id', None):
                        existing_client_qs = existing_client_qs.filter(gallery_id=request.user.gallery_id)
                    existing_client = existing_client_qs.first()
                
                if existing_client:
                    # 기존 데이터 업데이트
                    existing_client.data.update(client_data['data'])
                    existing_client.save()
                    success_count += 1
                else:
                    # 새 데이터 생성
                    print(f"[PANDAS CREATE DEBUG] User: {request.user}")
                    print(f"[PANDAS CREATE DEBUG] User gallery: {getattr(request.user, 'gallery', None)}")
                    print(f"[PANDAS CREATE DEBUG] User gallery_id: {getattr(request.user, 'gallery_id', None)}")
                    Client.objects.create(gallery=getattr(request.user, 'gallery', None), **client_data)
                    success_count += 1
                    
            except Exception as e:
                error_count += 1
                error_details.append(f"행 {i+2}: {str(e)}")
        
        return Response({
            'success': True,
            'message': f'처리 완료: 성공 {success_count}건, 실패 {error_count}건',
            'total_rows': len(processed_data),
            'success_count': success_count,
            'error_count': error_count,
            'error_details': error_details[:5],  # 최대 5개만 표시
            'column_mapping': column_mapping,
            'detected_columns': list(df.columns)
        })
        
    except Exception as e:
        return Response({
            'error': f'파일 처리 실패: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)