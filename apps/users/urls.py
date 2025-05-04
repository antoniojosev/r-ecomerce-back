from django.urls import path
from .views.v1 import RegisterView, LoginView

urlpatterns = [
    path('api/v1/users/register/', RegisterView.as_view(), name='user-register'),
    path('api/v1/users/login/', LoginView.as_view(), name='user-login'),
]
