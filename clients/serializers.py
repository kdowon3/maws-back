from rest_framework import serializers
from .models import Client, Tag
from django.db import transaction

class TagSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tag
        fields = ['id', 'name', 'color', 'created_at', 'updated_at']

def remove_tag_keys_recursively(obj):
    """data 내부의 태그 관련 키를 재귀적으로 완전히 삭제하는 함수"""
    if isinstance(obj, dict):
        tag_related_keys = ['tags', 'tag', '고객분류', 'customer_tags']
        for key in tag_related_keys:
            if key in obj:
                del obj[key]
        for v in obj.values():
            remove_tag_keys_recursively(v)
    elif isinstance(obj, list):
        for item in obj:
            remove_tag_keys_recursively(item)

class DynamicClientSerializer(serializers.ModelSerializer):
    tags = TagSerializer(many=True, read_only=True)
    tag_ids = serializers.ListField(child=serializers.IntegerField(), write_only=True, required=False)
    
    class Meta:
        model = Client
        fields = ['id', 'name', 'phone', 'tags', 'tag_ids', 'data', 'created_at', 'updated_at']
    
    @transaction.atomic
    def update(self, instance, validated_data):
        print(f"🔧 DynamicClientSerializer.update 호출됨")
        print(f"   - instance.id: {instance.id}")
        print(f"   - validated_data: {validated_data}")
        
        tag_ids = validated_data.pop('tag_ids', None)
        print(f"   - 추출된 tag_ids: {tag_ids}")
        
        instance = super().update(instance, validated_data)
        
        if tag_ids is not None:
            tags = Tag.objects.filter(id__in=tag_ids)
            print(f"   - 찾은 태그들: {[tag.name for tag in tags]}")
            instance.tags.set(tags)
            print(f"   - 태그 설정 완료: {[tag.name for tag in instance.tags.all()]}")
            # 데이터베이스에서 최신 정보를 다시 가져와서 캐싱 문제 해결
            instance.refresh_from_db()
        else:
            print(f"   - tag_ids가 None이므로 태그 설정 건너뜀")
        
        return instance
    
    @transaction.atomic
    def create(self, validated_data):
        tag_ids = validated_data.pop('tag_ids', [])
        instance = super().create(validated_data)
        
        if tag_ids:
            tags = Tag.objects.filter(id__in=tag_ids)
            instance.tags.set(tags)
        
        return instance

    def to_representation(self, instance):
        print(f"📋 DynamicClientSerializer.to_representation 호출됨")
        print(f"   - instance.id: {instance.id}")
        print(f"   - instance.name: {instance.name}")
        print(f"   - instance.tags.count(): {instance.tags.count()}")
        print(f"   - instance.tags.all(): {[tag.name for tag in instance.tags.all()]}")
        
        rep = super().to_representation(instance)
        print(f"   - 기본 rep: {rep}")
        
        # data 필드의 내용을 최상위로 병합 (기존 기본 필드와 태그 관련 필드는 덮어쓰지 않음)
        if instance.data:
            for key, value in instance.data.items():
                # 기본 필드와 태그 관련 필드들을 제외
                excluded_fields = ['name', 'phone', 'tags', 'tag', '고객분류', 'customer_tags']
                if key not in excluded_fields:
                    rep[key] = value
        
        # tags 필드를 고객분류로 매핑 (항상 최신 상태 반영)
        if instance.tags.exists():
            rep['고객분류'] = [{'id': tag.id, 'name': tag.name, 'color': tag.color} for tag in instance.tags.all()]
            print(f"   - 고객분류 매핑 완료: {rep['고객분류']}")
        else:
            rep['고객분류'] = []
            print(f"   - 고객분류 빈 배열로 설정")
        
        # data 필드에서 태그 관련 정보 재귀적으로 완전히 제거 (중복 방지)
        if 'data' in rep and isinstance(rep['data'], dict):
            remove_tag_keys_recursively(rep['data'])
            print(f"🗑️ data 필드에서 태그 관련 키 재귀적으로 제거 완료")
        
        print(f"   - 최종 rep: {rep}")
        return rep

    def to_internal_value(self, data):
        # AI 매핑 시스템으로 이미 올바른 구조로 전송되므로 간단히 처리
        validated_data = {
            'name': data.get('name', ''),
            'phone': data.get('phone', ''),
            'tag_ids': data.get('tag_ids', []),
            'data': data.get('data', {})
        }
        
        return super().to_internal_value(validated_data) 