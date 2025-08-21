from rest_framework import viewsets, permissions
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .models import ClientColumn
from clients.models import Client, Tag
from .serializers import ClientColumnSerializer, ClientSerializer, TagSerializer

class ClientColumnViewSet(viewsets.ModelViewSet):
    queryset = ClientColumn.objects.all().order_by('order', 'id')
    serializer_class = ClientColumnSerializer
    pagination_class = None  # 페이지네이션 비활성화 - 모든 컬럼을 한번에 가져오기
    http_method_names = ['get', 'post', 'put', 'patch', 'delete', 'head', 'options']  # PATCH 명시적 허용
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        """갤러리별 데이터 필터링 적용"""
        user = getattr(self.request, 'user', None)
        if user and getattr(user, 'gallery_id', None):
            return ClientColumn.objects.filter(gallery_id=user.gallery_id).order_by('order', 'id')
        return ClientColumn.objects.none()
    
    def perform_create(self, serializer):
        """컬럼 생성 시 현재 사용자의 갤러리 자동 할당"""
        gallery = getattr(self.request.user, 'gallery', None)
        serializer.save(gallery=gallery)
    
    def update(self, request, *args, **kwargs):
        """컬럼 수정 시 데이터 마이그레이션 포함"""
        print(f"🔧 컬럼 수정 요청 시작: {kwargs}")
        print(f"🔧 수정할 데이터: {request.data}")
        
        try:
            instance = self.get_object()
            old_accessor = instance.accessor
            print(f"🔧 수정할 컬럼 찾음: {instance.header} (ID: {instance.id})")
            print(f"🔧 기존 데이터: header={instance.header}, accessor={old_accessor}, type={instance.type}")
            
            # 새로운 accessor 값 확인
            new_accessor = request.data.get('accessor')
            
            # accessor가 변경되는 경우 클라이언트 데이터 마이그레이션
            if new_accessor and new_accessor != old_accessor:
                print(f"🔄 accessor 변경 감지: {old_accessor} → {new_accessor}")
                print(f"🔄 클라이언트 데이터 마이그레이션 시작...")
                
                # 현재 갤러리의 클라이언트만 대상으로 data 필드에서 키 변경
                from clients.models import Client
                user = getattr(self.request, 'user', None)
                if user and getattr(user, 'gallery_id', None):
                    clients = Client.objects.filter(gallery_id=user.gallery_id)
                else:
                    clients = Client.objects.none()
                updated_count = 0
                
                for client in clients:
                    if client.data and old_accessor in client.data:
                        # 기존 값 백업
                        old_value = client.data[old_accessor]
                        
                        # 새 키로 값 복사
                        client.data[new_accessor] = old_value
                        
                        # 기존 키 제거
                        del client.data[old_accessor]
                        
                        # 저장
                        client.save(update_fields=['data'])
                        updated_count += 1
                        
                        print(f"🔄 클라이언트 {client.id}({client.name}) 데이터 마이그레이션: {old_accessor} → {new_accessor}")
                
                print(f"✅ 데이터 마이그레이션 완료: {updated_count}개 클라이언트 업데이트")
            
            # 컬럼 수정 수행
            result = super().update(request, *args, **kwargs)
            
            # 업데이트된 인스턴스 다시 로드
            instance.refresh_from_db()
            print(f"🔧 컬럼 수정 완료: {instance.header} (ID: {instance.id})")
            print(f"🔧 수정된 데이터: header={instance.header}, accessor={instance.accessor}, type={instance.type}")
            
            return result
        except Exception as e:
            print(f"❌ 컬럼 수정 실패: {e}")
            print(f"❌ 에러 상세: {type(e).__name__}: {str(e)}")
            raise
    
    def destroy(self, request, *args, **kwargs):
        """컬럼 삭제 시 더 확실한 처리"""
        try:
            print(f"🗑️ 컬럼 삭제 요청 시작: {kwargs}")
            
            instance = self.get_object()
            column_id = instance.id
            column_header = instance.header
            
            print(f"🗑️ 삭제할 컬럼 찾음: {column_header} (ID: {column_id})")
            
            # 실제 삭제 수행
            instance.delete()
            
            print(f"🗑️ 컬럼 삭제 완료: {column_header} (ID: {column_id})")
            
            return Response({
                'message': f'컬럼 "{column_header}"이(가) 삭제되었습니다.',
                'deleted_id': column_id,
                'deleted_header': column_header,
                'success': True
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            print(f"❌ 컬럼 삭제 실패: {e}")
            print(f"❌ 에러 상세: {type(e).__name__}: {str(e)}")
            return Response({
                'error': f'컬럼 삭제 실패: {str(e)}',
                'success': False
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class ClientColumnSyncView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    
    def post(self, request):
        columns = request.data
        if not isinstance(columns, list):
            return Response({'detail': '컬럼 배열을 보내야 합니다.'}, status=400)
        
        user = getattr(request, 'user', None)
        gallery = getattr(user, 'gallery', None) if user else None
        
        if not gallery:
            return Response({'detail': '갤러리 정보가 필요합니다.'}, status=400)
        
        # 현재 갤러리의 컬럼만 삭제
        ClientColumn.objects.filter(gallery=gallery).delete()
        
        # bulk create with gallery
        objs = []
        for col in columns:
            col['gallery'] = gallery
            objs.append(ClientColumn(**col))
        ClientColumn.objects.bulk_create(objs)
        return Response({'status': 'ok', 'count': len(objs)}, status=status.HTTP_201_CREATED)


class TagViewSet(viewsets.ModelViewSet):
    queryset = Tag.objects.all().order_by('name')
    serializer_class = TagSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        """갤러리별 데이터 필터링 적용"""
        user = getattr(self.request, 'user', None)
        if user and getattr(user, 'gallery_id', None):
            return Tag.objects.filter(gallery_id=user.gallery_id).order_by('name')
        return Tag.objects.none()


class ClientViewSet(viewsets.ModelViewSet):
    queryset = Client.objects.all().order_by('-created_at')
    serializer_class = ClientSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        """갤러리별 데이터 필터링 적용"""
        user = getattr(self.request, 'user', None)
        if user and getattr(user, 'gallery_id', None):
            return Client.objects.filter(gallery_id=user.gallery_id).order_by('-created_at')
        return Client.objects.none()
