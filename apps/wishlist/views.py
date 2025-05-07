from django.shortcuts import get_object_or_404
from rest_framework import viewsets, status, filters
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.exceptions import ValidationError
from django_filters.rest_framework import DjangoFilterBackend
from .models import WishlistItem
from .serializers import WishlistItemSerializer
from .permissions import IsWishlistOwner
from apps.products.models import Product


class WishlistItemViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing wishlist items.
    
    Provides standard operations:
    - GET: list all items in the user's wishlist
    - POST: add a product to the wishlist (create)
    - DELETE: remove a product from the wishlist
    """
    serializer_class = WishlistItemSerializer
    permission_classes = [IsAuthenticated, IsWishlistOwner]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    search_fields = ['product__name']
    
    def get_queryset(self):
        """Return only wishlist items owned by the current user."""
        return WishlistItem.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        """Create a new wishlist item, validating that it doesn't already exist."""
        product_id = serializer.validated_data.get('product_id')
        product = get_object_or_404(Product, pk=product_id)

        # Prevent duplicates
        if WishlistItem.objects.filter(user=self.request.user, product=product).exists():
            raise ValidationError({"product_id": "This item is already in your wishlist."})

        # Associate with the current user and product
        serializer.save(user=self.request.user, product=product)


