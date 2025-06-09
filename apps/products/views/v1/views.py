from rest_framework import viewsets, filters, status
from rest_framework.permissions import IsAuthenticated, AllowAny, BasePermission
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from apps.products.models import Product
from apps.products.serializers.serializers import ProductSerializer, ProductCreateSerializer, ProductUpdateSerializer, ProductListSerializer


class IsSellerOrAdmin(BasePermission):
    """
    Permite acceso solo a vendedores o administradores.
    """
    
    def has_permission(self, request, view):
        return bool(
            request.user and 
            request.user.is_authenticated and 
            (hasattr(request.user.profile, 'is_seller') and request.user.profile.is_seller or request.user.is_staff)
        )
    
    def has_object_permission(self, request, view, obj):
        return bool(
            request.user and 
            request.user.is_authenticated and 
            (hasattr(obj, 'seller') and obj.seller == request.user or request.user.is_staff)
        )


class ProductViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing products with different permissions based on action.
    - List and retrieve are open to all users
    - Create, update, delete, and toggle_pause restricted to sellers and admins
    """
    queryset = Product.objects.all()
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['category', 'brand', 'seller', 'paused']
    search_fields = ['name', 'description', 'category__name', 'brand__name']
    ordering_fields = ['price', 'rating', 'paused', 'created_at']

    def get_serializer_class(self):
        if self.action in ['create']:
            return ProductSerializer
        if self.action in ['update', 'partial_update']:
            return ProductUpdateSerializer
        if self.action in ['list']:
            return ProductListSerializer
        if self.action in ['retrieve']: 
            return ProductSerializer
        return ProductSerializer    

    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update', 'destroy', 'toggle_pause']:
            return [IsAuthenticated(), IsSellerOrAdmin()]
        return [AllowAny()]
    
    def get_queryset(self):
        queryset = Product.objects.select_related('category', 'brand', 'seller').prefetch_related('images')
        return queryset
    
    @action(detail=True, methods=['post'])
    def toggle_pause(self, request, pk=None):
        """
        Toggle the pause state of a product.
        If paused, it will be unpaused; if not paused, it will be paused.
        Only the product owner (seller) or admin can toggle the pause state.
        """
        product = self.get_object()
        is_paused = product.toggle_pause()
        
        status_message = "paused" if is_paused else "unpaused"
        return Response({
            'status': 'success',
            'detail': f'Product {status_message} successfully',
            'paused': is_paused,
            'paused_date': product.paused_date
        }, status=status.HTTP_200_OK)
    
    @action(detail=False, methods=['get'], url_path='my')
    def my(self, request):
        """
        List all products belonging to the logged-in user (seller).
        """
        user = request.user
        queryset = self.get_queryset().filter(seller=user).order_by('-created_at')
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = ProductListSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        serializer = ProductListSerializer(queryset, many=True, context={'request': request})
        return Response(serializer.data)
