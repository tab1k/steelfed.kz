from django.db.models import Prefetch
from django.views import View
from django.views.generic import TemplateView
from .models import *
from django.shortcuts import redirect
from django.http import JsonResponse
from django.views.generic import DetailView, ListView
from django.core.paginator import Paginator
from django.http import JsonResponse
from django.template.loader import render_to_string
from django.views.generic import TemplateView
from django.views.generic import ListView
from django.shortcuts import get_object_or_404
from django_filters.views import FilterView
from .models import Product, Category, Service
from .filters import ProductFilter
import re
from django.views.generic import DetailView
from django.views.generic import TemplateView


        
class IndexPageView(TemplateView):
    template_name = 'website/index.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['services'] = Service.objects.only('name', 'image')
        # Передаем категории и их продукты
        context['categories'] = (
            Category.objects.filter(parent__isnull=True)
            .order_by('id')
            .prefetch_related('children__children__children', 'products')  # Предзагрузка продуктов
        )
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


class CategoryDetailView(DetailView):
    model = Category
    template_name = 'category/category_detail.html'
    context_object_name = 'category'

    def get_queryset(self):
        # Загружаем связанные данные только один раз
        return Category.objects.prefetch_related(
            'children',  # Предзагрузка подкатегорий
            'products'  # Предзагрузка продуктов
        ).select_related('parent').order_by('id')  # Сохраняем порядок категорий

    def get(self, request, *args, **kwargs):
        # Получение текущего объекта категории
        self.object = self.get_object()

        # Проверка: если подкатегорий нет, перенаправить на страницу списка продуктов
        if not self.object.children.exists():
            return redirect('main:product_list', slug=self.object.slug)

        # Если подкатегории существуют, отображаем стандартный шаблон
        return super().get(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        category = self.get_object()

        # Проверим содержимое продуктов для категории
        context['products'] = category.products.all()
        print(context['products'])  # Выведет список продуктов в консоль, если это нужно

        context['categories'] = Category.objects.filter(
            parent__isnull=True
        ).order_by('id').only('id', 'name')

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

        # Передаем форму фильтра в шаблон
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
        return context


class ProductDetailView(DetailView):
    model = Product
    template_name = 'product/product_detail.html'
    context_object_name = 'product'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        product = self.object  # Сохраняем объект, чтобы не делать повторные запросы к БД
        context['parsed_data'] = self.parse_product_name(product.name)
        return context

    @staticmethod
    def parse_product_name(product_name):
        # Извлекаем толщину стенки
        thickness = next(iter(re.findall(r"(\d+(\.\d+)?)\s*мм", product_name)), ("Не указано",))[0] + " мм"

        # Извлекаем марку стали
        mark = next(iter(re.findall(r"(Ст\d+[пс|кп]?)", product_name)), "Не указано")

        # Извлекаем ГОСТ
        gost = next(iter(re.findall(r"(ГОСТ\s*\d+-\d+)", product_name)), "Не указано")

        # Определяем тип проката
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