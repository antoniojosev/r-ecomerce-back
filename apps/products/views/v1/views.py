from rest_framework import viewsets, filters, status
from rest_framework.permissions import IsAuthenticated, AllowAny, BasePermission
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from django.db.models import Q
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
    
    @action(detail=True, methods=['get'], url_path='related')
    def related(self, request, pk=None):
        """
        Get related products for a given product.
        Returns up to 6 products with a maximum of 3 from the same brand 
        and 3 from the same category. If there are fewer products from 
        either criteria, the remaining slots are filled with random products.
        """
        product = self.get_object()
        related_products = self._get_related_products(product)
        
        serializer = ProductListSerializer(
            related_products, 
            many=True, 
            context={'request': request}
        )
        return Response(serializer.data, status=status.HTTP_200_OK)
    
    def _get_related_products(self, product):
        """
        Business logic to retrieve related products.
        """
        MAX_RESULTS = 6
        MAX_PER_CRITERIA = 3
        
        base_filter = Q(paused=False) & ~Q(id=product.id)
        
        # Get products by brand
        by_brand = list(
            Product.objects.filter(
                base_filter & Q(brand=product.brand)
            ).select_related('category', 'brand', 'seller')
            .prefetch_related('images')
            .order_by('?')[:MAX_PER_CRITERIA]
        )
        
        # Get products by category (excluding already selected by brand)
        brand_ids = [p.id for p in by_brand]
        by_category = list(
            Product.objects.filter(
                base_filter & 
                Q(category=product.category) & 
                ~Q(id__in=brand_ids)
            ).select_related('category', 'brand', 'seller')
            .prefetch_related('images')
            .order_by('?')[:MAX_PER_CRITERIA]
        )
        
        # Combine results
        related_products = by_brand + by_category
        
        # Fill remaining slots with random products if needed
        if len(related_products) < MAX_RESULTS:
            excluded_ids = [p.id for p in related_products] + [product.id]
            remaining_slots = MAX_RESULTS - len(related_products)
            
            random_products = list(
                Product.objects.filter(
                    base_filter & ~Q(id__in=excluded_ids)
                ).select_related('category', 'brand', 'seller')
                .prefetch_related('images')
                .order_by('?')[:remaining_slots]
            )
            
            related_products.extend(random_products)
        
        return related_products[:MAX_RESULTS]
