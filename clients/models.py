from django.db import models
from accounts.models import Gallery

# Create your models here.

class Tag(models.Model):
    """사용자 정의 태그 마스터 (갤러리별)"""
    gallery = models.ForeignKey(
        Gallery,
        on_delete=models.CASCADE,
        related_name="tags",
        null=True,
        blank=True,
        verbose_name="소속 갤러리",
    )
    name = models.CharField(max_length=50, verbose_name="태그명")
    color = models.CharField(max_length=7, default="#3B82F6", verbose_name="색상")  # 헥스 색상
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "태그"
        verbose_name_plural = "태그들"
        ordering = ['name']
        unique_together = (("gallery", "name"),)
    
    def __str__(self):
        return self.name

class Client(models.Model):
    # 갤러리 스코프
    gallery = models.ForeignKey(
        Gallery,
        on_delete=models.CASCADE,
        related_name="clients",
        null=True,
        blank=True,
        verbose_name="소속 갤러리",
    )
    # 기본 필드 (고정)
    name = models.CharField(max_length=100, blank=True, null=True, verbose_name="고객명")
    phone = models.CharField(max_length=20, blank=True, null=True, verbose_name="연락처")
    
    # 태그 필드 (ManyToMany 관계)
    tags = models.ManyToManyField(Tag, blank=True, verbose_name="태그")
    
    # 동적 필드 (기존 data JSONField)
    data = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def save(self, *args, **kwargs):
        is_new = self.pk is None  # 새로 생성되는 객체인지 확인
        super().save(*args, **kwargs)
        
        # 새로 생성된 객체이고 태그가 없으면 기본 태그 할당
        if is_new and not self.tags.exists():
            try:
                default_tag, created = Tag.objects.get_or_create(
                    gallery=self.gallery,
                    name='일반고객',
                    defaults={'color': '#6B7280'}
                )
                self.tags.add(default_tag)
                
                if created:
                    print(f"✅ '일반고객' 태그가 생성되었습니다: {default_tag}")
                print(f"✅ {self.name}에게 기본 태그 '{default_tag.name}'가 할당되었습니다.")
                
            except Exception as e:
                print(f"⚠️ 기본 태그 할당 실패: {e}")
                # 태그 할당이 실패해도 Client 생성은 계속 진행
                pass
    
    def __str__(self):
        return self.name or f"Client {self.id}"
    
    class Meta:
        verbose_name = "고객"
        verbose_name_plural = "고객들"


class ClientColumn(models.Model):
    """고객 동적 컬럼 정의"""
    gallery = models.ForeignKey(
        Gallery,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        verbose_name="소속 갤러리"
    )
    header = models.CharField(max_length=100, verbose_name="헤더명")
    accessor = models.CharField(max_length=100, verbose_name="접근자")
    type = models.CharField(max_length=20, default='text', verbose_name="필드 타입")
    order = models.PositiveIntegerField(default=0, verbose_name="순서")
    
    class Meta:
        verbose_name = "고객 컬럼"
        verbose_name_plural = "고객 컬럼들"
        unique_together = ['gallery', 'accessor']
        ordering = ['order', 'id']
    
    def __str__(self):
        return f"{self.header} ({self.gallery.name if self.gallery else 'No Gallery'})"
