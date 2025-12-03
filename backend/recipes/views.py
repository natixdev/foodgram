from django.shortcuts import redirect


def short_link_redirect(request, pk):
    """Редирект по короткой ссылке."""
    return redirect(request.build_absolute_uri(
        f'/recipes/{pk}/'
    ))
