from django.urls import path
from apps.users.views.v1.registration import RegistrationView
from apps.users.views.v1.logout import LogoutView

urlpatterns = [
    path('register/', RegistrationView.as_view(), name='user-register'),
    path('logout/', LogoutView.as_view(), name='user-logout'),
]
