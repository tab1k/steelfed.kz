import json
import os
import django

# Установите настройки Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'website.settings')
django.setup()

from main.models import Category, Product

# Функция для создания категорий
def create_categories(categories, parent=None):
    for category in categories:
        cat_obj, created = Category.objects.get_or_create(
            name=category['name_plural'],
            slug=category['slug'],
            parent=parent
        )
        if created:
            print(f"Создана категория: {cat_obj.name}")

        # Рекурсивно обрабатываем вложенные категории
        if 'children' in category and category['children']:
            create_categories(category['children'], parent=cat_obj)

# Функция для создания продуктов
def create_products(products):
    for product in products:
        category = Category.objects.filter(slug=product['category_slug']).first()
        if category:
            prod_obj, created = Product.objects.get_or_create(
                name=product['name'],
                slug=product['slug'],
                description=product.get('description', ''),
                category=category
            )
            if created:
                print(f"Создан продукт: {prod_obj.name}")

# Основной блок выполнения
if __name__ == "__main__":
    # Чтение JSON-файла
    try:
        with open('response.txt', 'r', encoding='utf-8') as file:
            data = json.load(file)
    except FileNotFoundError:
        print("Файл response.txt не найден")
        exit()
    except json.JSONDecodeError:
        print("Ошибка декодирования JSON")
        exit()

    # Импорт категорий
    main_categories = data.get('main', [])
    create_categories(main_categories)

    # Если в JSON есть данные продуктов
    products_data = data.get('products', [])
    create_products(products_data)

    print("Импорт данных завершён.")