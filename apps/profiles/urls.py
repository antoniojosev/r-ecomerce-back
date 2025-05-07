from django.urls import path
from .views.v1.views import UserProfileViewSet

urlpatterns = [
    path('me/', UserProfileViewSet.as_view({'get': 'me'}), name='user-profile-me'),
]