from django.urls import path
from .views import (
    ClientListView, ClientDetailView,
    ClientCreateView, ClientUpdateView, ClientDeleteView,
    ArtworkViewSet,
    S3PresignedUrlView,
    ClientColumnViewSet, SyncClientColumnsAPIView
)
from rest_framework.routers import DefaultRouter

router = DefaultRouter()
router.register(r'artworks', ArtworkViewSet, basename='artwork')
router.register(r'client-columns', ClientColumnViewSet, basename='clientcolumn')

urlpatterns = [
    path('clients/', ClientListView.as_view(), name='client-list'),
    path('clients/<int:pk>/', ClientDetailView.as_view(), name='client-detail'),
    path('clients/create/', ClientCreateView.as_view(), name='client-create'),
    path('clients/<int:pk>/update/', ClientUpdateView.as_view(), name='client-update'),
    path('clients/<int:pk>/delete/', ClientDeleteView.as_view(), name='client-delete'),
    path('presigned-url/', S3PresignedUrlView.as_view(), name='s3-presigned-url'),
    path('client-columns/sync/', SyncClientColumnsAPIView.as_view(), name='sync-client-columns'),
]

urlpatterns += router.urls 