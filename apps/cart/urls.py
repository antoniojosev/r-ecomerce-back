from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import CartViewSet

# Crear un router y registrar nuestro viewset
router = DefaultRouter()
# El endpoint 'cart' ahora gestionará todas las acciones relacionadas con el carrito
router.register(r'', CartViewSet, basename='cart')

# Las URLs de la API ahora son determinadas automáticamente por el router
urlpatterns = [
    path('', include(router.urls)),
]