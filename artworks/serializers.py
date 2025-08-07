from rest_framework import serializers
from .models import Artwork
from clients.models import Client

class ClientDetailSerializer(serializers.ModelSerializer):
    class Meta:
        model = Client
        fields = ['id', 'name', 'phone']

class ArtworkSerializer(serializers.ModelSerializer):
    buyer = serializers.PrimaryKeyRelatedField(queryset=Client.objects.all(), allow_null=True, required=False)
    buyer_detail = ClientDetailSerializer(source='buyer', read_only=True)
    
    class Meta:
        model = Artwork
        fields = [
            'id',
            'title_ko', 'title_en',
            'artist_ko', 'artist_en',
            'year', 'height', 'width', 'depth', 'size_unit', 'medium', 'price', 'image',
            'buyer', 'buyer_detail', 'has_missing_fields', 'note',
        ]
        extra_kwargs = {field: {'required': False, 'allow_null': True} for field in fields} 