from django.contrib import admin
from django.urls import include, path

urlpatterns = [path("finances/", include("apps.finances.urls_admin")), path("", admin.site.urls)]
