from django.db import models
from apps.users.models import User
from utils.models import BaseModel

class Profile(BaseModel):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    company_name = models.CharField(max_length=255)
    rif = models.CharField(max_length=20)
    email = models.EmailField()
    phone = models.CharField(max_length=20)
    description = models.TextField(blank=True, null=True)
    address = models.CharField(max_length=255)
    city = models.CharField(max_length=100)
    state = models.CharField(max_length=100)
    postal_code = models.CharField(max_length=20)
    is_verified = models.BooleanField(default=False)
    logo = models.ImageField(upload_to='company_logos/', blank=True, null=True)

    def __str__(self):
        return self.company_name
