from rest_framework import serializers
from .models import Artwork
from clients.models import Client

class ClientDetailSerializer(serializers.ModelSerializer):
    class Meta:
        model = Client
        fields = ['id', 'name', 'phone']

class ArtworkSerializer(serializers.ModelSerializer):
    # 현재 요청 컨텍스트의 갤러리로 제한된 buyer 선택
    buyer = serializers.PrimaryKeyRelatedField(queryset=Client.objects.none(), allow_null=True, required=False)
    buyer_detail = ClientDetailSerializer(source='buyer', read_only=True)
    
    class Meta:
        model = Artwork
        fields = [
            'id', 'gallery',
            'title_ko', 'title_en',
            'artist_ko', 'artist_en',
            'year', 'height', 'width', 'depth', 'size_unit', 'medium', 'price', 'image',
            'buyer', 'buyer_detail', 'has_missing_fields', 'note',
        ]
        extra_kwargs = {field: {'required': False, 'allow_null': True} for field in fields} 

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        request = self.context.get('request') if hasattr(self, 'context') else None
        if request and getattr(request.user, 'gallery_id', None):
            self.fields['buyer'].queryset = Client.objects.filter(gallery_id=request.user.gallery_id)
        else:
            self.fields['buyer'].queryset = Client.objects.none()