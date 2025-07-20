from rest_framework import serializers
from .models import Client, ClientStatus, Artwork, ClientColumn

class ClientStatusSerializer(serializers.ModelSerializer):
    class Meta:
        model = ClientStatus
        fields = '__all__'

class ClientSerializer(serializers.ModelSerializer):
    status = ClientStatusSerializer(many=True, read_only=True)
    class Meta:
        model = Client
        fields = '__all__'

class ArtworkSerializer(serializers.ModelSerializer):
    buyer = serializers.PrimaryKeyRelatedField(queryset=Client.objects.all(), allow_null=True, required=False)
    buyer_detail = ClientSerializer(source='buyer', read_only=True)
    class Meta:
        model = Artwork
        fields = '__all__'
        extra_kwargs = {field: {'required': False, 'allow_null': True} for field in fields}
    def to_representation(self, instance):
        rep = super().to_representation(instance)
        rep['buyer_detail'] = ClientSerializer(instance.buyer).data if instance.buyer else None
        return rep 

class ClientColumnSerializer(serializers.ModelSerializer):
    class Meta:
        model = ClientColumn
        fields = '__all__' 