from rest_framework import status, viewsets
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.exceptions import ValidationError
from rest_framework.decorators import action
from .permissions import IsCartOwner
from .models import Cart, CartItem
from .serializers import (
    CartSerializer, 
    CartItemSerializer, 
    CartAddItemSerializer,
    CartItemUpdateSerializer,
)


class CartViewSet(viewsets.ModelViewSet):
    """
    ViewSet para gestionar el carrito de compras del usuario.
    
    Proporciona operaciones estándar para el carrito y acciones personalizadas
    para agregar, actualizar y quitar items:
    - GET: obtener el carrito actual del usuario
    - /items/: listar todos los items en el carrito
    - /{id}/add_item/: agregar uno o múltiples productos al carrito específico
    - /update_item/: modificar la cantidad de un producto
    - /remove_item/: eliminar un producto del carrito
    """
    serializer_class = CartSerializer
    permission_classes = [IsAuthenticated, IsCartOwner]
    
    def get_queryset(self):
        # Obtener o crear el carrito para el usuario autenticado
        cart, _created = Cart.objects.get_or_create(user=self.request.user)
        return Cart.objects.filter(pk=cart.pk)
    
    def list(self, request, *args, **kwargs):
        """Devuelve el carrito único del usuario."""
        instance = self.get_queryset().first()
        if not instance:
            return Response({"detail": "Carrito no encontrado."}, status=status.HTTP_404_NOT_FOUND)
        serializer = self.get_serializer(instance)
        return Response(serializer.data)
    
    def retrieve(self, request, *args, **kwargs):
        """Obtiene el carrito por su ID (si coincide con el del usuario)."""
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def items(self, request):
        """Lista todos los items en el carrito del usuario."""
        cart, _created = Cart.objects.get_or_create(user=request.user)
        cart_items = CartItem.objects.filter(cart=cart)
        serializer = CartItemSerializer(cart_items, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['post'])
    def add_item(self, request):
        """
        Agrega uno o múltiples productos al carrito especificado en la URL.
        
        URL: /api/cart/add_item/
        
        Para agregar un solo producto:
        {
            "product_id": "UUID-del-producto",
            "quantity": 1
        }
        
        Para agregar múltiples productos en una sola operación:
        [
            {"product_id": "UUID-producto-1", "quantity": 1},
            {"product_id": "UUID-producto-2", "quantity": 3},
            ...
        ]
        """
        cart = request.user.cart

        # Determinar si es una lista de items o un solo item
        is_many = isinstance(request.data, list)
        
        # Crear una copia mutable de los datos
        if is_many:
            # Es una lista de items
            data = []
            for item in request.data:
                item_copy = item.copy() if isinstance(item, dict) else {}
                item_copy['cart_id'] = cart.id  # Agregar el cart_id a cada item
                data.append(item_copy)
        else:
            # Es un solo item
            data = request.data.copy()
            data['cart_id'] = cart.id  # Agregar el cart_id al request.data
        
        # Usar el serializer con many=True si es una lista
        serializer = CartAddItemSerializer(data=data, many=is_many)
        serializer.is_valid(raise_exception=True)
        cart_items = serializer.save()
        
        # Preparar la respuesta (que será un solo item o una lista de items)
        response_serializer = CartItemSerializer(cart_items, many=is_many)
        
        return Response(response_serializer.data, status=status.HTTP_200_OK)
    
    @action(detail=False, methods=['post'])
    def update_item(self, request):
        """
        Actualiza la cantidad de uno o múltiples productos en el carrito.
        Si la cantidad es 0, se elimina el item del carrito.
        
        Para actualizar un solo item:
        {
            "item_id": "UUID-del-item",
            "quantity": 3
        }
        
        Para actualizar múltiples items (enviar una lista):
        [
            {"item_id": "UUID-item-1", "quantity": 2},
            {"item_id": "UUID-item-2", "quantity": 0},
            {"item_id": "UUID-item-3", "quantity": 5}
        ]
        
        Retorna la lista de items en el carrito después de la actualización.
        """
        # Determinar si es una lista de items o un solo item
        is_many = isinstance(request.data, list)
        
        # Usar el serializador con many=True si es una lista
        serializer = CartItemUpdateSerializer(data=request.data, many=is_many, context={'request': request})
        serializer.is_valid(raise_exception=True)
        
        # Procesar la actualización
        if not is_many:
            # Para un solo item, usar el método update directamente
            serializer.update()
        else:
            # Para múltiples items, procesar cada uno individualmente
            for item_data in serializer.validated_data:
                # Crear un serializador individual para cada item
                item_serializer = CartItemUpdateSerializer(data=item_data, context={'request': request})
                item_serializer.is_valid()  # Ya validamos antes, así que debe ser válido
                # Actualizar el item
                item_serializer.update()
        
        # Después de todas las actualizaciones, obtener los items actuales del carrito
        cart = Cart.objects.get(user=request.user)
        cart_items = CartItem.objects.filter(cart=cart)
        
        # Retornar la lista de items actualizada
        response_serializer = CartItemSerializer(cart_items, many=True)
        return Response(response_serializer.data)
    
    @action(detail=False, methods=['post'])
    def remove_item(self, request):
        """
        Elimina un item específico del carrito.
        
        Parámetros:
        - item_id: UUID del item del carrito a eliminar
        """
        item_id = request.data.get('item_id')
        if not item_id:
            raise ValidationError({"item_id": "Este campo es obligatorio."})
        
        # Obtener carrito del usuario
        cart, _created = Cart.objects.get_or_create(user=request.user)
        
        try:
            cart_item = CartItem.objects.get(pk=item_id, cart=cart)
        except CartItem.DoesNotExist:
            return Response(
                {"detail": "Item no encontrado en su carrito."},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Eliminar el item
        cart_item.delete()
        return Response(
            {"detail": "Item eliminado del carrito correctamente."},
            status=status.HTTP_204_NO_CONTENT
        )
