from rest_framework import permissions
from rest_framework.permissions import BasePermission, SAFE_METHODS
from .models import Cart, CartItem


class IsCartOwner(BasePermission):
    """
    Permiso personalizado que verifica si el usuario es el dueño del carrito.
    Solo permite a los usuarios acceder y modificar sus propios carritos e items.
    """
    def has_permission(self, request, view):
        # Permitir acceso solo a usuarios autenticados
        return bool(request.user and request.user.is_authenticated)
    
    def has_object_permission(self, request, view, obj):
        # Verificar si el usuario es dueño del carrito o del item del carrito
        if isinstance(obj, Cart):
            return obj.user == request.user
        elif isinstance(obj, CartItem):
            return obj.cart.user == request.user
        return False