from django.db import models
from apps.users.models import User
from utils.models import BaseModel


class Profile(BaseModel):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    company_name = models.CharField(max_length=255, blank=True, null=True) # Added company_name field
    dni = models.CharField(max_length=20, blank=True, null=True, unique=True) # Added dni field
    rif = models.CharField(max_length=20, blank=True, null=True, unique=True)
    phone = models.CharField(max_length=20)
    description = models.TextField(blank=True, null=True)
    avatar = models.ImageField(upload_to='avatars/', blank=True, null=True) # Added avatar field
    is_seller = models.BooleanField(default=False) # Added is_seller field
    is_verified = models.BooleanField(default=False)
    logo = models.ImageField(upload_to='company_logos/', blank=True, null=True)

    def __str__(self):
        return self.company_name

class Address(BaseModel): # Changed to inherit from BaseModel
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='addresses') # Added related_name
    street = models.CharField(max_length=255)
    city = models.CharField(max_length=100)
    state = models.CharField(max_length=100)
    zip_code = models.CharField(max_length=10)
    shipping_agency = models.CharField(max_length=100, blank=True, null=True) # Added shipping_agency field
    default_account = models.BooleanField(default=False) # Added default_account field
    description = models.TextField(blank=True, null=True) # Added description field
    
    def __str__(self):
        return f"{self.street}, {self.city}, {self.state} {self.zip_code}"
