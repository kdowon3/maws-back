from django.db import models

# Create your models here.

class ClientStatus(models.Model):
    name = models.CharField(max_length=20, unique=True, null=True, blank=True)

    def __str__(self):
        return self.name

class Client(models.Model):
    name = models.CharField(max_length=50, null=True, blank=True)
    phone = models.CharField(max_length=20, null=True, blank=True)
    address = models.CharField(max_length=200, null=True, blank=True)
    buy_artist = models.CharField(max_length=50, null=True, blank=True)
    favorite_artist = models.CharField(max_length=50, null=True, blank=True)
    note = models.TextField(null=True, blank=True)
    email = models.EmailField(null=True, blank=True)
    last_visit = models.DateTimeField(null=True, blank=True)
    registration_date = models.DateField(null=True, blank=True)
    status = models.ManyToManyField(ClientStatus, blank=True)

    def __str__(self):
        return self.name if self.name else "(No Name)"

class ClientColumn(models.Model):
    header = models.CharField(max_length=100)  # 컬럼명(한글 등)
    accessor = models.CharField(max_length=100, unique=True)  # 내부 필드명(영문 등)
    type = models.CharField(max_length=20, default='text')  # 데이터 타입
    order = models.PositiveIntegerField(default=0)  # 컬럼 순서

    def __str__(self):
        return self.header

class Artwork(models.Model):
    title = models.CharField(max_length=100, null=True, blank=True)
    artist = models.CharField(max_length=50, null=True, blank=True)
    year = models.CharField(max_length=10, null=True, blank=True)
    dimensions = models.CharField(max_length=50, null=True, blank=True)
    medium = models.CharField(max_length=50, null=True, blank=True)
    price = models.PositiveIntegerField(null=True, blank=True)
    image = models.URLField(blank=True, null=True)
    buyer = models.ForeignKey(Client, on_delete=models.SET_NULL, null=True, blank=True)
    has_missing_fields = models.BooleanField(null=True, blank=True)

    def __str__(self):
        return self.title if self.title else "(No Title)"
