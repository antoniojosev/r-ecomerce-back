from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from rest_framework_simplejwt.tokens import RefreshToken
from apps.users.serializers.registration import RegistrationSerializer
from apps.profiles.serializers.serializers import ProfileSerializer


class RegistrationView(generics.CreateAPIView):
    """
    Endpoint for user registration with automatic wallet creation.
    """
    serializer_class = RegistrationSerializer
    permission_classes = [AllowAny]
    
    def create(self, request, *args, **kwargs):
        """
        Create a new user and their associated wallet, return JWT tokens.
        """
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        
        # Generate tokens for the new user
        refresh = RefreshToken.for_user(user)
        tokens = {
            'refresh': str(refresh),
            'access': str(refresh.access_token),
        }

        data = {
            'user': ProfileSerializer(user.profile).data,
            'tokens': tokens,
            'message': 'Usuario registrado exitosamente'
        }
        
        return Response(data, status=status.HTTP_201_CREATED)