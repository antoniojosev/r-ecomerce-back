from rest_framework.permissions import BasePermission, SAFE_METHODS
from .models import WishlistItem


class IsWishlistOwner(BasePermission):
    """
    Custom permission to check if the user is the owner of the wishlist item.
    Only allows users to access and modify their own wishlist items.
    """
    def has_permission(self, request, view):
        # Allow access only to authenticated users
        return bool(request.user and request.user.is_authenticated)
    
    def has_object_permission(self, request, view, obj):
        # Check if the user is the owner of the wishlist item
        return obj.user == request.user