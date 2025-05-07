from django.db import models
from utils.models import BaseModel
from apps.users.models import User
from apps.products.models import Product

class WishlistItem(BaseModel):
    user: models.ForeignKey[User] = models.ForeignKey(User, on_delete=models.CASCADE, related_name='wishlist_items')
    product: models.ForeignKey[Product] = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='wishlisted_by')
    # added_at is essentially created_at from BaseModel

    def __str__(self):
        # Access the related User object to get the email
        # Access the related Product object to get the name
        return f"{self.product.name} in wishlist of {self.user.email}"

    class Meta:
        unique_together = ('user', 'product') # Prevent duplicate products in the same wishlist
