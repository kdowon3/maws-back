from rest_framework import serializers
from .models import Client, Tag
from django.db import transaction

class TagSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tag
        fields = ['id', 'name', 'color', 'created_at', 'updated_at']

# 태그 관련 재귀 정리 함수 제거됨 (불필요한 복잡성)

class DynamicClientSerializer(serializers.ModelSerializer):
    tags = TagSerializer(many=True, read_only=True)
    tag_ids = serializers.ListField(child=serializers.IntegerField(), write_only=True, required=False)
    
    class Meta:
        model = Client
        fields = ['id', 'gallery_id', 'name', 'phone', 'tags', 'tag_ids', 'data', 'created_at', 'updated_at']
        read_only_fields = []
    
    @transaction.atomic
    def update(self, instance, validated_data):
        print(f"DynamicClientSerializer.update called")
        print(f"   - instance.id: {instance.id}")
        print(f"   - validated_data: {validated_data}")
        
        # tag_ids가 명시적으로 전송된 경우에만 처리
        tag_ids = None
        if 'tag_ids' in validated_data:
            tag_ids = validated_data.pop('tag_ids')
            print(f"   - 추출된 tag_ids: {tag_ids}")
            print(f"   - 태그 업데이트 실행됨")
        else:
            print(f"   - tag_ids 필드 없음 - 기존 태그 보존")
        
        instance = super().update(instance, validated_data)
        
        if tag_ids is not None:
            print(f"   - 태그 업데이트 진행: {tag_ids}")
            # 현재 갤러리 내 태그만 허용
            request = self.context.get('request') if hasattr(self, 'context') else None
            gallery_id = getattr(getattr(request, 'user', None), 'gallery_id', None)
            tag_qs = Tag.objects.filter(id__in=tag_ids)
            if gallery_id:
                tag_qs = tag_qs.filter(gallery_id=gallery_id)
            tags = tag_qs
            instance.tags.set(tags)
            instance.refresh_from_db()
        else:
            print(f"   - 태그 업데이트 건너뜀 (기존 태그 보존)")
        
        return instance
    
    @transaction.atomic
    def create(self, validated_data):
        # 갤러리 설정 강제
        request = self.context.get('request') if hasattr(self, 'context') else None
        gallery_id = getattr(getattr(request, 'user', None), 'gallery_id', None)
        tag_ids = validated_data.pop('tag_ids', [])
        if gallery_id and not validated_data.get('gallery_id'):
            validated_data['gallery_id'] = gallery_id
        instance = super().create(validated_data)
        
        if tag_ids:
            tag_qs = Tag.objects.filter(id__in=tag_ids)
            if gallery_id:
                tag_qs = tag_qs.filter(gallery_id=gallery_id)
            tags = tag_qs
            instance.tags.set(tags)
        
        return instance

    def to_representation(self, instance):
        print(f"DynamicClientSerializer.to_representation called")
        print(f"   - instance.id: {instance.id}")
        print(f"   - instance.name: {instance.name}")
        print(f"   - instance.gallery_id: {getattr(instance, 'gallery_id', None)}")
        print(f"   - instance.tags.count(): {instance.tags.count()}")
        print(f"   - instance.tags.all(): {[tag.name for tag in instance.tags.all()]}")
        
        # 태그를 다시 한번 확인
        tags_check = instance.tags.all()
        print(f"   - 태그 재확인: {[(tag.id, tag.name, tag.gallery_id) for tag in tags_check]}")
        
        rep = super().to_representation(instance)
        print(f"   - basic rep tags: {rep.get('tags', 'NO_TAGS_KEY')}")
        print(f"   - rep keys: {list(rep.keys())}")
        
        # 기본 필드가 비어있으면 data 필드에서 찾아서 채우기
        if instance.data:
            # name 필드가 비어있으면 data에서 찾기
            if not rep.get('name') and instance.data:
                name_candidates = ['고객명', 'customer_name', 'name']
                for candidate in name_candidates:
                    if candidate in instance.data and instance.data[candidate]:
                        rep['name'] = str(instance.data[candidate]).strip()
                        print(f"   - name 필드를 data에서 복원: {rep['name']} (from {candidate})")
                        break
            
            # phone 필드가 비어있으면 data에서 찾기
            if not rep.get('phone') and instance.data:
                phone_candidates = ['연락처', '전화번호', '휴대폰', '핸드폰', 'phone']
                for candidate in phone_candidates:
                    if candidate in instance.data and instance.data[candidate]:
                        rep['phone'] = str(instance.data[candidate]).strip()
                        print(f"   - phone 필드를 data에서 복원: {rep['phone']} (from {candidate})")
                        break
        
        # data 필드의 내용을 최상위로 병합 (기본 필드는 덮어쓰지 않음)
        if instance.data:
            for key, value in instance.data.items():
                # 기본 필드들과 이미 복원된 필드들은 제외하고 병합
                excluded_fields = ['name', 'phone', 'tags', '고객명', '연락처', '전화번호', '휴대폰', '핸드폰', 'customer_name']
                if key not in excluded_fields:
                    rep[key] = value
        
        print(f"   - 최종 rep: {rep}")
        return rep

    def to_internal_value(self, data):
        # AI 매핑 시스템으로 이미 올바른 구조로 전송되므로 간단히 처리하되, 갤러리 주입
        validated_data = {
            'name': data.get('name', ''),
            'phone': data.get('phone', ''),
            'data': data.get('data', {})
        }
        
        # tag_ids는 명시적으로 전송된 경우에만 포함 (기본값 설정 안함)
        if 'tag_ids' in data:
            validated_data['tag_ids'] = data['tag_ids']
            print(f"🏷️ [SERIALIZER] tag_ids 명시적 포함: {data['tag_ids']}")
        else:
            print(f"🏷️ [SERIALIZER] tag_ids 필드 없음 - 태그 업데이트 건너뜀")
        ret = super().to_internal_value(validated_data)
        request = self.context.get('request') if hasattr(self, 'context') else None
        gallery_id = getattr(getattr(request, 'user', None), 'gallery_id', None)
        print(f"[SERIALIZER DEBUG] Gallery ID from user: {gallery_id}")
        
        if gallery_id is not None:
            ret['gallery_id'] = gallery_id  # gallery_id 필드로 일관되게 할당
            print(f"[SERIALIZER DEBUG] Setting gallery_id to: {gallery_id}")
        else:
            print(f"❌ [SERIALIZER ERROR] 갤러리 정보 없음 - 사용자: {getattr(request, 'user', 'Unknown')}")
            from rest_framework.exceptions import ValidationError
            raise ValidationError("갤러리 정보가 필요합니다.")
        
        return ret