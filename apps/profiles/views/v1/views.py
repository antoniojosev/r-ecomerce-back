from django.shortcuts import render
from rest_framework import generics
from ...models import Profile
from ...serializers.serializers import ProfileSerializer

# Create your views here.

class ProfileListCreateView(generics.ListCreateAPIView):
    queryset = Profile.objects.all()
    serializer_class = ProfileSerializer
