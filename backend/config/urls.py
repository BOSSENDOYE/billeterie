from django.contrib import admin
from django.urls import include, path

admin.site.site_header = 'Billetterie — Administration'
admin.site.site_title = 'Billetterie'

urlpatterns = [
    # /admin est la page React du tableau de bord : l'admin Django vit sur /django-admin/
    path('django-admin/', admin.site.urls),
    path('api/', include('billetterie.urls')),
]
