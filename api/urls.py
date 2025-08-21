from django.urls import path
from rest_framework.routers import DefaultRouter
from .views import ClientColumnViewSet, ClientViewSet, TagViewSet
from .views import ClientColumnSyncView

router = DefaultRouter()
router.register(r'client-columns', ClientColumnViewSet, basename='clientcolumn')
router.register(r'legacy-clients', ClientViewSet, basename='legacy-client')  # 레거시 API
router.register(r'legacy-tags', TagViewSet, basename='legacy-tag')  # 레거시 API

urlpatterns = router.urls 
urlpatterns += [
    path('client-columns-sync/', ClientColumnSyncView.as_view(), name='clientcolumn-sync'),
] 