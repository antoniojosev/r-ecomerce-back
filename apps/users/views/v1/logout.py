from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from rest_framework import status
from rest_framework_simplejwt.token_blacklist.models import BlacklistedToken, OutstandingToken
from rest_framework_simplejwt.utils import aware_utcnow


class LogoutView(APIView):
    """
    API endpoint that allows users to logout by blacklisting their token.
    """
    permission_classes = [AllowAny]

    def post(self, request):
        """
        Logout the authenticated user by blacklisting their token.
        """
        try:
            # Get the refresh token
            refresh_token = request.data.get('refresh_token')
            
            if refresh_token:
                # Blacklist the refresh token
                token = OutstandingToken.objects.get(token=refresh_token)
                BlacklistedToken.objects.create(token=token, blacklisted_at=aware_utcnow())
                
            return Response({"detail": "Logout exitoso"}, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({"detail": f"Error en el logout: {str(e)}"}, status=status.HTTP_400_BAD_REQUEST)