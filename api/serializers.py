from rest_framework import serializers
from clients.models import ClientColumn
from clients.models import Client, Tag

class ClientColumnSerializer(serializers.ModelSerializer):
    class Meta:
        model = ClientColumn
        fields = '__all__'


class TagSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tag
        fields = ['id', 'name', 'color', 'created_at', 'updated_at']


class ClientSerializer(serializers.ModelSerializer):
    tags = TagSerializer(many=True, read_only=True)
    tag_ids = serializers.ListField(child=serializers.IntegerField(), write_only=True, required=False)
    
    class Meta:
        model = Client
        fields = ['id', 'name', 'phone', 'tags', 'tag_ids', 'data', 'created_at', 'updated_at']
    
    def create(self, validated_data):
        tag_ids = validated_data.pop('tag_ids', [])
        client = Client.objects.create(**validated_data)
        if tag_ids:
            client.tags.set(tag_ids)
        return client
    
    def update(self, instance, validated_data):
        tag_ids = validated_data.pop('tag_ids', None)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        if tag_ids is not None:
            instance.tags.set(tag_ids)
        return instance 