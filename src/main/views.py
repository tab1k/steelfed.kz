from datetime import datetime
import random
import re
from collections import defaultdict

from django.core.cache import cache
from django.core.paginator import Paginator
from django.db.models import Q, Prefetch, Count
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect
from django.template.loader import render_to_string
from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_page
from django.views import View
from django.views.generic import TemplateView, ListView, DetailView
from django_filters.views import FilterView

from .models import Product, Category, Service
from .filters import ProductFilter


        
class IndexPageView(TemplateView):
    template_name = 'website/index.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['services'] = Service.objects.only('name', 'image')
        
        # Передаем категории и их продукты (оптимизировано)
        context['categories'] = (
            Category.objects.filter(parent__isnull=True)
            .order_by('id')
            .prefetch_related('children', 'children__products')
        )

        # Попробуем получить случайные товары из кеша
        random_products = cache.get('random_products')
        
        if not random_products:
            # Получаем 5 случайных товаров с использованием SQL
            random_products = Product.objects.order_by('?')[:5]

            # Кешируем случайные товары на 24 часа
            cache.set('random_products', random_products, timeout=86400)  # timeout = 86400 секунд (24 часа)

        context['random_products'] = random_products
        return context
    
    
class ProcheeCategoryView(TemplateView):
    template_name = 'category/news_container.html'  # Убедитесь, что путь правильный

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['categories'] = Category.objects.filter(parent__slug='prochee').prefetch_related('products')
        return context


class AjaxableTemplateView(TemplateView):
    """
    Базовое представление, которое обрабатывает AJAX-запросы
    и рендерит только часть страницы (если запрос AJAX).
    """

    def render_to_response(self, context, **kwargs):
        if self.request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            html = render_to_string(self.get_template_names(), context)

            new_content = self.extract_content(html)
            return JsonResponse({'html': new_content})
        else:
            return super().render_to_response(context, **kwargs)

    def extract_content(self, html):
        # Берем только содержимое внутри элемента с id="content"
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(html, 'html.parser')
        content = soup.find(id="content")
        return str(content) if content else ""

class ServiceViewPage(AjaxableTemplateView):
    template_name = 'website/services.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['services'] = Service.objects.only('name', 'image')
        
        return context


class AboutViewPage(AjaxableTemplateView):
    template_name = 'website/about.html'


class DeliveryViewPage(AjaxableTemplateView):
    template_name = 'buyers/delivery.html'


class PaymentViewPage(AjaxableTemplateView):
    template_name = 'buyers/payment.html'


class RefundViewPage(AjaxableTemplateView):
    template_name = 'buyers/refund.html'


class ContactViewPage(AjaxableTemplateView):
    template_name = 'website/contacts.html'


class CategoryViewPage(TemplateView):
    template_name = 'category/index.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Передаем категории и их продукты
        context['categories'] = (
            Category.objects.filter(parent__isnull=True)
            .order_by('id')
            .only('id', 'name', 'slug')  # Загрузите только нужные поля
            .prefetch_related(
                Prefetch(
                    'children',
                    queryset=Category.objects.only('id', 'name', 'slug')
                ),
                Prefetch(
                    'children__children',
                    queryset=Category.objects.only('id', 'name', 'slug')
                ),
                Prefetch(
                    'products',
                    queryset=Product.objects.only('id', 'name', 'slug')
                )
            )
        )

        return context
    
class ServicesDetailView(DetailView):
    model = Service
    template_name = 'website/service_detail.html'
    context_object_name = 'service'



class CategoryDetailView(DetailView):
    model = Category
    template_name = 'category/category_detail.html'
    context_object_name = 'category'

    @method_decorator(cache_page(60 * 15))  # Кэшируем страницу на 15 минут
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)

    def get_queryset(self):
        return Category.objects.prefetch_related(
            'children',
            'products'  # Используем prefetch_related для множественных связей
        ).select_related('parent').order_by('id')

    def get(self, request, *args, **kwargs):
        self.object = self.get_object()

        # Редиректим, если нет потомков
        if not self.object.children.exists():
            return redirect('main:product_list', slug=self.object.slug)

        return super().get(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        category = self.object
        
        subcategories = category.children.all()

        # Получаем все категории
        all_categories = Category.objects.only('id', 'parent_id')

        # Строим дерево в памяти с использованием defaultdict
        children_map = defaultdict(list)
        for cat in all_categories:
            children_map[cat.parent_id].append(cat.id)

        # Собираем все id категорий и их потомков
        category_ids = set()
        stack = [category.id]

        while stack:
            current_id = stack.pop()
            category_ids.add(current_id)
            stack.extend(children_map.get(current_id, []))

        # Используем кэш для списка продуктов
        cache_key = f'category_{category.id}_products'
        products = cache.get(cache_key)

        if not products:
            # Получаем продукты одним запросом по всем нужным категориям и сортируем их случайным образом
            products = Product.objects.filter(category_id__in=category_ids).select_related('category').distinct()
            products = products.order_by('?')  # Сортируем случайным образом

            # Кэшируем результат на 15 минут
            cache.set(cache_key, products, timeout=60 * 15)

        # Пагинация
        paginator = Paginator(products, 15)
        page_number = self.request.GET.get('page')
        page_obj = paginator.get_page(page_number)

        # Получаем количество продуктов через пагинатор
        total_products = page_obj.paginator.count

        # Главные категории для меню
        top_categories = Category.objects.filter(parent__isnull=True).only('id', 'name')

        # Передаем данные в шаблон
        context.update({
            'page_obj': page_obj,
            'categories': top_categories,
            'total_products': total_products,
            'subcategories': subcategories,
        })
        return context


class ProductListView(FilterView, ListView):
    model = Product
    template_name = 'product/product_list.html'
    context_object_name = 'products'
    paginate_by = 10  # Показываем по 10 товаров на странице
    filterset_class = ProductFilter  # Подключаем фильтры

    def get_queryset(self):
        """ Фильтруем товары только по текущей категории и запросу поиска """
        slug = self.kwargs.get('slug')
        category = get_object_or_404(Category, slug=slug)
        queryset = category.products.all().order_by('id')  # Добавляем сортировку
        return ProductFilter(self.request.GET, queryset=queryset).qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        slug = self.kwargs.get('slug')
        category = get_object_or_404(Category, slug=slug)
        context['category'] = category

        # Формируем список "похожих" категорий
        similar_categories = Category.objects.filter(parent=category.parent).exclude(id=category.id)
        
        if not similar_categories.exists() and category.parent:
            # Если нет категорий с таким же родителем, берем подкатегории родителя
            similar_categories = Category.objects.filter(parent=category.parent.parent).exclude(id=category.id) if category.parent.parent else None

        context['similar_categories'] = similar_categories

        # Фильтр товаров
        context['filter'] = ProductFilter(self.request.GET, queryset=self.get_queryset())

        # Пагинация
        paginator = context['paginator']
        page_obj = context['page_obj']
        current_page = page_obj.number
        total_pages = paginator.num_pages

        if total_pages <= 5:
            page_range = range(1, total_pages + 1)
        else:
            if current_page <= 3:
                page_range = range(1, 6)
            elif current_page >= total_pages - 2:
                page_range = range(total_pages - 4, total_pages + 1)
            else:
                page_range = range(current_page - 2, current_page + 3)

        context['page_range'] = page_range
        context['current_page'] = current_page
        context['ancestors'] = category.get_ancestors()
        return context


class ProductDetailView(DetailView):
    model = Product
    template_name = 'product/product_detail.html'
    context_object_name = 'product'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        product = self.object

        # Распарсенные данные из названия
        context['parsed_data'] = self.parse_product_name(product.name)

        # Категория товара
        category = product.category
        context['category'] = category

        # Получаем цепочку родительских категорий
        context['category_ancestors'] = category.get_ancestors()

        return context

    @staticmethod
    def parse_product_name(product_name):
        thickness = next(iter(re.findall(r"(\d+(\.\d+)?)\s*мм", product_name)), ("Не указано",))[0] + " мм"
        mark = next(iter(re.findall(r"(Ст\d+[пс|кп]?)", product_name)), "Не указано")
        gost = next(iter(re.findall(r"(ГОСТ\s*\d+-\d+)", product_name)), "Не указано")
        product_type = "горячекатаная" if "горячекатаная" in product_name else \
                       "холоднокатаная" if "холоднокатаная" in product_name else "Не указано"

        return {
            "thickness": thickness,
            "mark": mark,
            "gost": gost,
            "product_type": product_type,
        }



def search_products(request):
    query = request.GET.get('query', '').strip()  # Получаем запрос из GET-параметра
    results = []

    if query:
        # Поиск продуктов по названию
        products = Product.objects.filter(name__icontains=query).select_related('category')
        product_results = [
            {
                'name': product.name,
                'slug': product.slug,
                'type': 'product',
                'category': product.category.name,
                'image': product.image.url if product.image else None
            }
            for product in products
        ]

        # Поиск категорий по названию
        categories = Category.objects.filter(name__icontains=query)
        category_results = [
            {
                'name': category.name,
                'slug': category.slug,
                'type': 'category',
                'parent': category.parent.name if category.parent else None,
                'image': category.image.url if category.image else None
            }
            for category in categories
        ]

        # Объединяем результаты
        results = product_results + category_results

    # Если ничего не найдено
    if not results:
        results = [{'name': 'Ничего не найдено', 'type': 'none'}]

    return JsonResponse({'results': results})



from django.shortcuts import render

def custom_404(request, exception):
    return render(request, '404.html', status=404)