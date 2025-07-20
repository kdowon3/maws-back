from django.shortcuts import render
from rest_framework import generics, viewsets
from .models import Client, Artwork, ClientColumn
from .serializers import ClientSerializer, ArtworkSerializer, ClientColumnSerializer
from django.conf import settings
import boto3
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework import status

# Create your views here.

class ClientListView(generics.ListAPIView):
    queryset = Client.objects.all()
    serializer_class = ClientSerializer

class ClientDetailView(generics.RetrieveAPIView):
    queryset = Client.objects.all()
    serializer_class = ClientSerializer

class ClientCreateView(generics.CreateAPIView):
    queryset = Client.objects.all()
    serializer_class = ClientSerializer

class ClientUpdateView(generics.UpdateAPIView):
    queryset = Client.objects.all()
    serializer_class = ClientSerializer

class ClientDeleteView(generics.DestroyAPIView):
    queryset = Client.objects.all()
    serializer_class = ClientSerializer

# Artwork API (ModelViewSet으로 통합)
class ArtworkViewSet(viewsets.ModelViewSet):
    queryset = Artwork.objects.all()
    serializer_class = ArtworkSerializer

    def create(self, request, *args, **kwargs):
        data = request.data.copy()
        file = request.FILES.get('image')
        if file:
            s3_client = boto3.client(
                's3',
                aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
                aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
                region_name=settings.AWS_S3_REGION_NAME,
            )
            s3_key = f"artworks/{file.name}"
            s3_client.upload_fileobj(
                file,
                settings.AWS_STORAGE_BUCKET_NAME,
                s3_key,
                ExtraArgs={
                    'ContentType': file.content_type
                }
            )
            file_url = f"https://{settings.AWS_STORAGE_BUCKET_NAME}.s3.{settings.AWS_S3_REGION_NAME}.amazonaws.com/{s3_key}"
            data['image'] = file_url
        serializer = self.get_serializer(data=data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data, status=201, headers=headers)

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        data = request.data.copy()
        file = request.FILES.get('image')
        if file:
            s3_client = boto3.client(
                's3',
                aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
                aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
                region_name=settings.AWS_S3_REGION_NAME,
            )
            s3_key = f"artworks/{file.name}"
            s3_client.upload_fileobj(
                file,
                settings.AWS_STORAGE_BUCKET_NAME,
                s3_key,
                ExtraArgs={
                    'ContentType': file.content_type
                }
            )
            file_url = f"https://{settings.AWS_STORAGE_BUCKET_NAME}.s3.{settings.AWS_S3_REGION_NAME}.amazonaws.com/{s3_key}"
            data['image'] = file_url
        else:
            # 파일이 없으면 기존 image URL 유지
            data['image'] = instance.image
        serializer = self.get_serializer(instance, data=data, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        return Response(serializer.data)

class S3PresignedUrlView(APIView):
    # permission_classes = [IsAuthenticated]  # 임시로 인증 제거

    def post(self, request):
        file_name = request.data.get('file_name')
        file_type = request.data.get('file_type', 'image/jpeg')
        if not file_name:
            return Response({'error': 'file_name is required'}, status=400)

        s3_client = boto3.client(
            's3',
            aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
            region_name=settings.AWS_S3_REGION_NAME,
        )

        presigned_url = s3_client.generate_presigned_url(
            'put_object',
            Params={
                'Bucket': settings.AWS_STORAGE_BUCKET_NAME,
                'Key': file_name,
                'ContentType': file_type,
            },
            ExpiresIn=300  # 5분간 유효
        )

        file_url = f"https://{settings.AWS_STORAGE_BUCKET_NAME}.s3.{settings.AWS_S3_REGION_NAME}.amazonaws.com/{file_name}"

        return Response({
            'presigned_url': presigned_url,
            'file_url': file_url,
        })

class ClientColumnViewSet(viewsets.ModelViewSet):
    queryset = ClientColumn.objects.all().order_by('order')
    serializer_class = ClientColumnSerializer

class SyncClientColumnsAPIView(APIView):
    def post(self, request):
        columns = request.data.get('columns', [])
        created_or_updated = []
        for idx, col in enumerate(columns):
            accessor = col.get('accessor')
            header = col.get('header')
            col_type = col.get('type', 'text')
            if not accessor or not header:
                continue
            obj, created = ClientColumn.objects.update_or_create(
                accessor=accessor,
                defaults={'header': header, 'type': col_type, 'order': idx}
            )
            created_or_updated.append(ClientColumnSerializer(obj).data)
        return Response({'columns': created_or_updated}, status=status.HTTP_200_OK)
