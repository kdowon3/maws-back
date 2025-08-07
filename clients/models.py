from django.db import models

# Create your models here.

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

class Client(models.Model):
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
