from rest_framework import permissions
from rest_framework.permissions import BasePermission, SAFE_METHODS


class OrderPermission(BasePermission):
    """
    Permisos específicos para órdenes.
    - Cualquier usuario autenticado puede crear órdenes
    - Los usuarios solo pueden ver/modificar/eliminar sus propias órdenes
    - El staff puede ver todas las órdenes pero no modificarlas
    """
    
    def has_permission(self, request, view):
        # Todos los usuarios autenticados pueden listar sus órdenes o crear nuevas
        return bool(request.user and request.user.is_authenticated)
    
    def has_object_permission(self, request, view, obj):
        # Solo el propietario puede acceder a la orden
        # El staff puede ver pero no modificar
        if request.method in SAFE_METHODS and request.user.is_staff:
            return True
        return obj.user == request.user


class QuestionPermission(BasePermission):
    """
    Permisos para el sistema de preguntas y respuestas:
    - Cualquier usuario autenticado puede ver preguntas
    - Cualquier usuario autenticado puede crear preguntas en productos
    - Solo el autor de la pregunta puede editarla o eliminarla
    - El vendedor del producto y staff pueden responder cualquier pregunta
    """
    
    def has_permission(self, request, view):
        # Todos los usuarios autenticados pueden ver preguntas o crear nuevas
        return bool(request.user and request.user.is_authenticated)
    
    def has_object_permission(self, request, view, obj):
        # Lectura: permitida para todos los usuarios autenticados
        if request.method in SAFE_METHODS:
            return True
            
        # Para responder: el vendedor del producto o staff
        if hasattr(view, 'action') and view.action == 'mark_answered':
            if request.user.is_staff:
                return True
            if hasattr(obj.product, 'seller'):
                return obj.product.seller == request.user
                
        # Para editar/eliminar: solo el autor de la pregunta
        return obj.user == request.user


class IsSellerForProduct(BasePermission):
    """
    Permiso específico para operaciones que requieren ser vendedor del producto.
    """
    
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated)
    
    def has_object_permission(self, request, view, obj):
        # Verificar si el usuario es el vendedor del producto
        if hasattr(obj, 'product') and hasattr(obj.product, 'seller'):
            return obj.product.seller == request.user
        return False


class IsStaffUser(BasePermission):
    """
    Permiso para acciones exclusivas de administradores.
    """
    
    def has_permission(self, request, view):
        return bool(
            request.user and
            request.user.is_authenticated and
            request.user.is_staff
        )