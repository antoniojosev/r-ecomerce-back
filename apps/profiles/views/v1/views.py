from rest_framework import viewsets, mixins
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import action
from apps.profiles.serializers.serializers import ProfileSerializer

# Create your views here.

class UserProfileViewSet(mixins.RetrieveModelMixin, viewsets.GenericViewSet):
    """
    Read-only ViewSet for retrieving the current authenticated user's profile.
    """
    serializer_class = ProfileSerializer
    permission_classes = [IsAuthenticated]

    def get_object(self):
        """
        Return the authenticated user.
        """
        return self.request.user.profile

    @action(detail=False, methods=['get'])
    def me(self, request):
        """
        Endpoint for retrieving the current authenticated user's profile.
        """
        serializer = self.get_serializer(self.get_object())
        return Response(serializer.data)
