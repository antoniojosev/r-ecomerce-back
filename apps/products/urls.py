from django.urls import path
from .views.v1.views import ProductListCreateView

urlpatterns = [
    path('', ProductListCreateView.as_view(), name='product-list-create'),
]