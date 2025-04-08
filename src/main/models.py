from django.db import models
from django.urls import reverse
from slugify import slugify


class Category(models.Model):
    name = models.CharField(max_length=255, verbose_name="Название категории", db_index=True)
    image = models.ImageField(max_length=255, blank=True, null=True, verbose_name="Картинка категории")
    slug = models.SlugField(unique=True, verbose_name="Слаг", max_length=255)
    about = models.TextField(max_length=255, blank=True, null=True)
    parent = models.ForeignKey(
        'self',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='children',
        verbose_name="Родительская категория"
    )

    class Meta:
        verbose_name = "Категория"
        verbose_name_plural = "Категории"
        ordering = ['name']

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return reverse('main:category_detail', kwargs={'slug': self.slug})
    
    
    def get_ancestors(self):
        category = self
        ancestors = []
        while category:
            ancestors.insert(0, category)
            category = category.parent
        return ancestors


class Product(models.Model):
    name = models.CharField(max_length=255, verbose_name="Название продукта", db_index=True)
    image = models.ImageField(upload_to='products/', verbose_name="Фото продукта")
    external_url = models.URLField(max_length=500, null=True, blank=True)
    category = models.ForeignKey(
        Category,
        on_delete=models.CASCADE,
        related_name='products',
        verbose_name="Категория"
    )
    slug = models.SlugField(unique=True, verbose_name="Слаг", blank=True, null=True, max_length=255)
    description = models.TextField(blank=True, verbose_name="Описание")

    class Meta:
        verbose_name = "Продукт"
        verbose_name_plural = "Продукты"
        
        indexes = [
            models.Index(fields=['category']),
        ]

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            base_slug = slugify(self.name)
            slug = base_slug
            counter = 1

            while Product.objects.filter(slug=slug).exists():
                slug = f"{base_slug}-{counter}"
                counter += 1

            self.slug = slug

        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse('main:product_detail', kwargs={'slug': self.slug})
    
    
    

class Service(models.Model):
    name = models.CharField(max_length=255, blank=False, null=False)
    image = models.ImageField(max_length=255, blank=False, null=False, verbose_name="Картинка услуг")
    slug = models.SlugField(unique=True, verbose_name="Слаг", max_length=255, blank=True, null=True)
    description = models.TextField(blank=True, verbose_name="Описание")
    
    def save(self, *args, **kwargs):
        if not self.slug:
            base_slug = slugify(self.name)
            slug = base_slug
            counter = 1

            while Service.objects.filter(slug=slug).exists():  # Исправлено с Product на Service
                slug = f"{base_slug}-{counter}"
                counter += 1

            self.slug = slug

        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse('main:services_detail', kwargs={'slug': self.slug})
    
    class Meta:
        verbose_name = "Услуга"
        verbose_name_plural = "Услуги"

    def __str__(self):
        return self.name