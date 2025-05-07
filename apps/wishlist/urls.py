from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import WishlistItemViewSet

# Create a router and register our viewsets with it.
router = DefaultRouter()
# The 'items' endpoint manages WishlistItems for the user.
router.register(r'items', WishlistItemViewSet, basename='wishlist-item')

# The API URLs are now determined automatically by the router.
urlpatterns = [
    path('', include(router.urls)),
]