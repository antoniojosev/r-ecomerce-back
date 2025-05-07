from rest_framework import serializers
from django.contrib.auth import get_user_model
from django.db import transaction
from apps.profiles.models import Profile

User = get_user_model()


class RegistrationSerializer(serializers.ModelSerializer):
    """
    Serializer for registering new users with password confirmation and profile data.
    """
    password = serializers.CharField(write_only=True, required=True, style={'input_type': 'password'})
    password_confirm = serializers.CharField(write_only=True, required=True, style={'input_type': 'password'})
    
    # Campos de perfil
    company_name = serializers.CharField(max_length=255, required=True)
    dni = serializers.CharField(max_length=20, required=False, allow_blank=True, allow_null=True)
    rif = serializers.CharField(max_length=20, required=True)
    phone = serializers.CharField(max_length=20, required=True)
    description = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    is_seller = serializers.BooleanField(default=False)
    
    class Meta:
        model = User
        fields = [
            'username', 'email', 'name', 'last_name', 'password', 'password_confirm',
            'company_name', 'dni', 'rif', 'phone', 'description', 'is_seller'
        ]
        
    def validate(self, attrs):
        """
        Validate that passwords match and the email is unique.
        """
        if attrs.get('password') != attrs.get('password_confirm'):
            raise serializers.ValidationError({'password_confirm': "Las contraseñas no coinciden"})
            
        if User.objects.filter(email=attrs.get('email')).exists():
            raise serializers.ValidationError({'email': "Un usuario con este email ya existe."})
            
        return attrs
    
    @transaction.atomic
    def create(self, validated_data):
        """
        Create the user and profile in a single transaction.
        """
        # Extraer los campos del perfil de los datos validados
        profile_data = {
            'company_name': validated_data.pop('company_name'),
            'dni': validated_data.pop('dni', None),
            'rif': validated_data.pop('rif'),
            'phone': validated_data.pop('phone'),
            'description': validated_data.pop('description', None),
            'is_seller': validated_data.pop('is_seller', False)
        }
        
        # Eliminar el campo password_confirm ya que no es parte del modelo User
        validated_data.pop('password_confirm', None)
        
        # Crear el usuario
        user = User.objects.create_user(
            username=validated_data['username'],
            email=validated_data['email'],
            name=validated_data.get('name', ''),
            last_name=validated_data.get('last_name', ''),
            password=validated_data['password'],
        )
        
        # Crear el perfil asociado al usuario
        Profile.objects.create(user=user, **profile_data)
        
        return user