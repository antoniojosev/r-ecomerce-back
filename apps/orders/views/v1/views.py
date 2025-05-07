from rest_framework import viewsets, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend

from apps.orders.models import Order, Question
from apps.orders.serializers.serializers import (
    OrderSerializer, 
    QuestionSerializer, 
    OrderGroupedCreateSerializer,
    OrderFromCartSerializer,
    OrderInputSerializer
)
from apps.orders.permissions import OrderPermission, QuestionPermission
from apps.orders.services.OrdersBo import OrdersBo, OrderInputDTO


class OrderViewSet(viewsets.ModelViewSet):
    """
    ModelViewSet para gestionar órdenes con lógica mejorada de agrupación por vendedor.
    
    Este viewset se encarga de:
    - Crear órdenes agrupadas por vendedor (una orden por vendedor)
    - Eliminar productos duplicados
    - Validar direcciones y productos
    - Proteger la compra de productos propios
    - Calcular correctamente los totales
    """
    permission_classes = [OrderPermission]
    order_service = OrdersBo()
    
    def get_queryset(self):
        """Retorna las órdenes del usuario actual"""
        if self.request.user.is_staff:
            # Los administradores pueden ver todas las órdenes
            return Order.objects.all().order_by('-created_at')
        # El resto de usuarios solo ven sus propias órdenes
        return self.order_service.get_user_orders(self.request.user.id)
    
    def get_serializer_class(self):
        """Retorna el serializador apropiado según la acción"""
        if self.action == 'create':
            return OrderInputSerializer  # Ahora usamos el nuevo serializer unificado
        elif self.action == 'create_from_cart':
            return OrderFromCartSerializer
        return OrderSerializer

    def create(self, request, *args, **kwargs):
        """
        Crea órdenes agrupadas por vendedor.
        Utiliza el nuevo OrderInputSerializer para validar y procesar los datos.
        """
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        shipping_data = {
            "address_id": serializer.data.get('address_id', None), 
            "new_address": serializer.data.get('new_address', None) 
        }
        
        orders_input = OrderInputDTO(
            user_id = str(request.user.id),
            items = serializer.data['items'],
            shipping_data = shipping_data
        )

        order_service = OrdersBo()
        result = order_service.create_orders(orders_input)


        #orders = serializer.save()
        return Response(OrderSerializer(result.orders,many=True).data, status=status.HTTP_201_CREATED)
    
    @action(detail=False, methods=['post'], url_path='from-cart')
    def create_from_cart(self, request):
        """Crea órdenes agrupadas por vendedor a partir del carrito"""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class QuestionViewSet(viewsets.ModelViewSet):
    """
    ViewSet para gestionar preguntas y respuestas de productos.
    
    Implementa manejo apropiado de permisos con:
    - Operaciones de lectura disponibles para todos los usuarios autenticados
    - Operaciones de escritura restringidas según el rol (vendedor, creador de la pregunta)
    """
    permission_classes = [QuestionPermission]
    serializer_class = QuestionSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields = ['product', 'is_answered']
    search_fields = ['text']
    
    def get_queryset(self):
        """
        Retorna preguntas con filtrado apropiado:
        - Por defecto, retorna solo preguntas de nivel superior (no respuestas)
        - Aplica filtrado por producto si se proporciona product_id
        """
        queryset = Question.objects.filter(parent__isnull=True)
        
        # Soporte para filtrado por product_id desde params de consulta
        product_id = self.request.query_params.get('product_id')
        if product_id:
            queryset = queryset.filter(product_id=product_id)
            
        return queryset
    
    def perform_create(self, serializer):
        """Asocia la pregunta con el usuario actual"""
        serializer.save(user=self.request.user)
    
    @action(detail=True, methods=['post'])
    def mark_answered(self, request, pk=None):
        """Acción personalizada para marcar una pregunta como respondida"""
        question = self.get_object()
        question.mark_as_answered()
        serializer = self.get_serializer(question)
        return Response(serializer.data)
