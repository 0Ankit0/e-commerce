from django.urls import include, path
from rest_framework.routers import DefaultRouter

from . import views

router = DefaultRouter()
router.register(r"vendors", views.VendorViewSet)
router.register(r"documents", views.VendorDocumentViewSet)
router.register(r"bank-accounts", views.BankAccountViewSet)

urlpatterns = [
    path("", include(router.urls)),
]
