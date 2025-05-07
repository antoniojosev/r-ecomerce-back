from django.urls import path
from .views.v1.views import ProductViewSet
from rest_framework.routers import DefaultRouter
from django.urls import path, include

v1_router = DefaultRouter()
v1_router.register(r'', ProductViewSet, basename='product')

urlpatterns = [
    path('', include(v1_router.urls)),
]