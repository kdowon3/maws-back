from django.contrib import admin
from .models import ClientStatus, Client, Artwork, ClientColumn

admin.site.register(ClientStatus)
admin.site.register(Client)
admin.site.register(Artwork)
admin.site.register(ClientColumn)
