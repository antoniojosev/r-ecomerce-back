# serializers/serializers.py

from rest_framework import serializers
from apps.profiles.models import Profile, Address


class AddressSerializer(serializers.ModelSerializer): # Create AddressSerializer
    class Meta:
        model = Address
        fields = [
            'id',
            'street',
            'city',
            'state',
            'zip_code',
            'shipping_agency',
            'description',
        ]


class ProfileSerializer(serializers.ModelSerializer):
    address = serializers.SerializerMethodField()

    class Meta:
        model = Profile
        fields = (
            'id',
            'user',
            'company_name',
            'dni',
            'rif',
            'phone',
            'description',
            'avatar',
            'is_seller',
            'is_verified',
            'logo',
            'created_at',
            'updated_at',
            'address',
        )
        read_only_fields = ('user', 'is_verified') # Make certain fields read-only

    def get_address(self, obj):
        """
        Return the addresses associated with the profile.
        """
        address = obj.user.addresses.filter(default_account=True).first()  # Get the first address marked as default
        if address is None:  # Check if address is None instead of using exists()
            return None
        return AddressSerializer(address).data
