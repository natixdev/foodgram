from rest_framework.pagination import PageNumberPagination

from core.constants import MAX_PAGE_SIZE, PAGE_SIZE


class FgPagination(PageNumberPagination):
    """Пагинация рецептов/пользователей."""

    page_size = PAGE_SIZE
    page_size_query_param = 'limit'
    max_page_size = MAX_PAGE_SIZE
