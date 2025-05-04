from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.db import models

from utils.models import BaseModel


class CustomUserManager(BaseUserManager):

    def get_queryset(self):
        return super().get_queryset().filter(deleted_at__isnull=True)

    def _create_user(self, username, email, name, last_name, password, is_staff, is_superuser, **extra_fields):
        user = self.model(
            username=username,
            email=email,
            name=name,
            last_name=last_name,
            is_staff=is_staff,
            is_superuser=is_superuser,
            **extra_fields
        )
        user.set_password(password)
        user.save(using=self.db)
        return user

    def create_user(self, username, email, name, last_name, password=None, **extra_fields):
        return self._create_user(username, email, name, last_name, password, False, False, **extra_fields)

    def create_superuser(self, username, email, password=None, **extra_fields):
        name = ""
        last_name = ""
        return self._create_user(username, email, name, last_name, password, True, True, **extra_fields)


class User(BaseModel, AbstractUser):
    name = models.CharField(max_length=255, blank=True, null=True)
    last_name = models.CharField(max_length=255, blank=True, null=True)
    objects = CustomUserManager()
    all_objects = models.Manager()

    def __str__(self):
        return self.email
