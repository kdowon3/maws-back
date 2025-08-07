from django.db import models
from clients.models import Client

# Create your models here.

class Artwork(models.Model):
    title_ko = models.CharField(max_length=100, null=True, blank=True)
    title_en = models.CharField(max_length=100, null=True, blank=True)
    artist_ko = models.CharField(max_length=50, null=True, blank=True)
    artist_en = models.CharField(max_length=50, null=True, blank=True)
    year = models.CharField(max_length=10, null=True, blank=True)
    # size = models.CharField(max_length=50, null=True, blank=True)  # dimensions → size (deprecated)
    height = models.FloatField(null=True, blank=True)  # 높이
    width = models.FloatField(null=True, blank=True)   # 너비
    depth = models.FloatField(null=True, blank=True)   # 깊이(입체만)
    size_unit = models.CharField(max_length=10, null=True, blank=True, default='cm')  # 단위
    medium = models.CharField(max_length=50, null=True, blank=True)
    price = models.PositiveIntegerField(null=True, blank=True)
    image = models.URLField(blank=True, null=True)
    buyer = models.ForeignKey(Client, on_delete=models.SET_NULL, null=True, blank=True)
    has_missing_fields = models.BooleanField(null=True, blank=True)
    note = models.TextField(null=True, blank=True)
    def __str__(self):
        return self.title_ko if self.title_ko else self.title_en if self.title_en else "(No Title)"
