from django.contrib import admin
from .models import ClientColumn

class ClientColumnAdmin(admin.ModelAdmin):
    list_display = ['id', 'header', 'accessor', 'type', 'order']
    list_filter = ['type']
    search_fields = ['header', 'accessor']
    ordering = ['order', 'id']

admin.site.register(ClientColumn, ClientColumnAdmin)
