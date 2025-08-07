from django.urls import path
from rest_framework.routers import DefaultRouter
from .views import ArtworkViewSet, S3PresignedUrlView

router = DefaultRouter()
router.register(r'artworks', ArtworkViewSet, basename='artwork')

urlpatterns = [
    path('presigned-url/', S3PresignedUrlView.as_view(), name='s3-presigned-url'),
]
urlpatterns += router.urls 