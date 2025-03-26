from django.contrib import admin
from .models import *

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'parent')  # Показываем название и родительскую категорию
    prepopulated_fields = {'slug': ('name',)}  # Автозаполнение slug
    autocomplete_fields = ['parent']  # Добавляем автодополнение для выбора родительской категории
    search_fields = ('name', 'parent__name')  # Поиск по имени категории и родительской категории
    ordering = ('name',)  # Сортировка категорий по имени в алфавитном порядке

    # Добавляем фильтрацию категорий без родителя
    list_filter = ('parent',)

    # Переопределяем список категорий для показа
    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        # Если нужен фильтр для категорий без родителя:
        if request.GET.get('parent__isnull', None):
            return queryset.filter(parent__isnull=True)
        return queryset


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ('name', 'category', 'slug')
    prepopulated_fields = {'slug': ('name',)}
    autocomplete_fields = ['category']
    search_fields = ('name', 'category__name')
    ordering = ('name',)
    

admin.site.register(Service)