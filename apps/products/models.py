from django.db import models
from django.db.models import SlugField
from django.utils.text import slugify
from django.utils import timezone
from utils.models import BaseModel
from apps.users.models import User

class Category(BaseModel):
    name = models.CharField(max_length=100)
    slug = SlugField(unique=True, blank=True)

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name

class Brand(BaseModel):
    name = models.CharField(max_length=100)
    slug = SlugField(unique=True, blank=True)

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name

class Product(BaseModel):
    name = models.CharField(max_length=255)
    brand = models.ForeignKey(
        Brand, 
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name='products'
    )
    description = models.TextField(blank=True, null=True)
    category = models.ForeignKey(
        Category, 
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name='products'
    )
    sku = models.CharField(max_length=50, unique=True)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    original_price = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    discount = models.IntegerField(default=0)
    seller = models.ForeignKey(User, on_delete=models.CASCADE, related_name='products')
    stock = models.PositiveIntegerField(default=0)
    paused = models.BooleanField(default=False)
    paused_date = models.DateTimeField(blank=True, null=True)

    def __str__(self):
        return self.name
    
    def toggle_pause(self):
        """
        Toggle the pause state of the product.
        If paused, unpause it; if not paused, pause it.
        """
        self.paused = not self.paused
        if self.paused:
            self.paused_date = timezone.now()
        else:
            self.paused_date = None
        self.save(update_fields=['paused', 'paused_date', 'updated_at'])
        return self.paused

class ProductImage(BaseModel):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='images')
    image = models.ImageField(upload_to='product_images/')
    order = models.IntegerField(default=0)

class ProductFeature(BaseModel):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='features')
    feature = models.CharField(max_length=255)

class ProductSpecification(BaseModel):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='specifications')
    name = models.CharField(max_length=100)
    value = models.CharField(max_length=255)

class ProductVariant(BaseModel):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='variants')
    name = models.CharField(max_length=100)
    value = models.CharField(max_length=100)
    stock = models.PositiveIntegerField(default=0)
    price = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)

