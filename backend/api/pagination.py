from rest_framework.pagination import PageNumberPagination


class FgPagination(PageNumberPagination):
    page_size = 6 #Вынести в конст
    page_size_query_param = 'limit'
    max_page_size = 50
