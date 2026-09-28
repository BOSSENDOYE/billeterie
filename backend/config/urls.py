from django.contrib import admin
from django.urls import include, path

admin.site.site_header = 'Billetterie — Administration'
admin.site.site_title = 'Billetterie'

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', include('billetterie.urls')),
]
