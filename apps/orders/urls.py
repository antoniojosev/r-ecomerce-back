from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views.v1 import views as v1_views

# Create a router for v1 API endpoints
v1_router = DefaultRouter()
v1_router.register(r'questions', v1_views.QuestionViewSet, basename='question')
v1_router.register(r'', v1_views.OrderViewSet, basename='order')

# Main urlpatterns for the app
urlpatterns = [
    path('', include(v1_router.urls)),
]
