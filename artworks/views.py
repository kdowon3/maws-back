from django.shortcuts import render
from rest_framework import viewsets, filters
from .models import Artwork
from .serializers import ArtworkSerializer
from clients.models import Client
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.conf import settings
from django.db.models import Q
import boto3

# Create your views here.

class ArtworkViewSet(viewsets.ModelViewSet):
    queryset = Artwork.objects.all()
    serializer_class = ArtworkSerializer
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['title_ko', 'title_en', 'artist_ko', 'artist_en']
    ordering_fields = ['id', 'price', 'year']
    ordering = ['-id']  # 기본 정렬: ID 역순 (최신 등록순)
    
    def get_queryset(self):
        queryset = super().get_queryset()
        
        try:
            # 작가 필터링
            artist = self.request.query_params.get('artist', None)
            if artist:
                queryset = queryset.filter(
                    Q(artist_ko__icontains=artist) | Q(artist_en__icontains=artist)
                )
            
            # 정렬 (기본 ordering은 클래스 레벨에서 설정됨)
            sort = self.request.query_params.get('sort', None)
            if sort == 'latest':
                queryset = queryset.order_by('-id')  # 최신 등록순
            elif sort == 'oldest':
                queryset = queryset.order_by('id')   # 오래된 등록순
            elif sort == 'price_high':
                queryset = queryset.order_by('-price')
            elif sort == 'price_low':
                queryset = queryset.order_by('price')
            
        except Exception as e:
            # 에러 발생시 기본 queryset 반환
            print(f"ArtworkViewSet get_queryset error: {e}")
            queryset = Artwork.objects.all().order_by('-id')
        
        return queryset

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
            data['image'] = instance.image
        serializer = self.get_serializer(instance, data=data, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        return Response(serializer.data)

class S3PresignedUrlView(APIView):
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
            ExpiresIn=300
        )
        file_url = f"https://{settings.AWS_STORAGE_BUCKET_NAME}.s3.{settings.AWS_S3_REGION_NAME}.amazonaws.com/{file_name}"
        return Response({
            'presigned_url': presigned_url,
            'file_url': file_url,
        })
