import django_filters
from .models import Product
from django import forms

class ProductFilter(django_filters.FilterSet):
    search = django_filters.CharFilter(
        method='filter_by_name',
        label='Поиск',
        widget=forms.TextInput(attrs={
            'class': 'search__input filter-aside__search',  # Класс для стилизации
            'placeholder': '32х4.5 мм P460N EN 10216-3...',  # Placeholder
        })
    )

    class Meta:
        model = Product
        fields = ['search']

    def filter_by_name(self, queryset, name, value):
        """ Фильтрация по названию продукта (поиск по тексту) """
        return queryset.filter(name__icontains=value)