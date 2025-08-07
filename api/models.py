from django.db import models

# Create your models here.

class ClientColumn(models.Model):
    header = models.CharField(max_length=100)
    accessor = models.CharField(max_length=100, unique=True)
    type = models.CharField(max_length=20, default='text')
    order = models.PositiveIntegerField(default=0)
