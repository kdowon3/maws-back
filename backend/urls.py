"""
URL configuration for backend project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
import logging

@csrf_exempt
def log_error(request):
    if request.method == 'POST':
        import json
        data = json.loads(request.body)
        print('FRONT ERROR:', data)  # 터미널에 출력
        logging.error(f"FRONT ERROR: {data}")
        return JsonResponse({'status': 'ok'})

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/log-error/', log_error),
    path('api/accounts/', include('accounts.urls')),
    path('api/', include('api.urls')),
    path('api/', include('clients.urls')),
    path('api/', include('artworks.urls')),
]
