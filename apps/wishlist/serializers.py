from rest_framework import serializers
from .models import WishlistItem
from apps.products.serializers.serializers import ProductSerializer # Assuming you have a ProductSerializer

class WishlistItemSerializer(serializers.ModelSerializer):
    product = ProductSerializer(read_only=True)
    product_id = serializers.UUIDField(write_only=True) # To add item by product ID
    user = serializers.ReadOnlyField(source='user.username')

    class Meta:
        model = WishlistItem
        fields = ['id', 'user', 'product', 'product_id', 'created_at']
        read_only_fields = ['id', 'user', 'product', 'created_at']