from django.urls import path
from rest_framework.routers import DefaultRouter
from .views import ClientColumnViewSet, ClientViewSet, TagViewSet
from .views import ClientColumnSyncView

router = DefaultRouter()
router.register(r'client-columns', ClientColumnViewSet, basename='clientcolumn')
router.register(r'clients', ClientViewSet, basename='client')
router.register(r'tags', TagViewSet, basename='tag')

urlpatterns = router.urls 
urlpatterns += [
    path('client-columns-sync/', ClientColumnSyncView.as_view(), name='clientcolumn-sync'),
] 