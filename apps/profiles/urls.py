from django.urls import path
from .views.v1.views import ProfileListCreateView

urlpatterns = [
    path('', ProfileListCreateView.as_view(), name='profile-list-create'),
]