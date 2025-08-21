from django.db import models

# Create your models here.

class ClientColumn(models.Model):
    gallery = models.ForeignKey('accounts.Gallery', on_delete=models.CASCADE, null=True, blank=True)
    header = models.CharField(max_length=100)
    accessor = models.CharField(max_length=100)
    type = models.CharField(max_length=20, default='text')
    order = models.PositiveIntegerField(default=0)
    
    class Meta:
        unique_together = ['gallery', 'accessor']
