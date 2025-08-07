from django.db import models

class Tag(models.Model):
    """사용자 정의 태그 마스터"""
    name = models.CharField(max_length=50, unique=True, verbose_name="태그명")
    color = models.CharField(max_length=7, default="#3B82F6", verbose_name="색상")  # 헥스 색상
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "태그"
        verbose_name_plural = "태그들"
        ordering = ['name']
    
    def __str__(self):
        return self.name