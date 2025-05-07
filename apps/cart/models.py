from django.db import models
from utils.models import BaseModel
from apps.users.models import User
from apps.products.models import Product

class Cart(BaseModel):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='cart')
    # created_at and updated_at are inherited from BaseModel

    def __str__(self):
        # Access the related User object to get the email
        return f"Cart for {self.user.email}" # type: ignore

class CartItem(BaseModel):
    cart = models.ForeignKey("Cart", on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='cart_items')
    quantity = models.PositiveIntegerField(default=1)

    def __str__(self):
        # Access related objects for name/representation
        product_name = self.product.name # type: ignore
        cart_repr = str(self.cart) # type: ignore
        return f"{self.quantity} x {product_name} in {cart_repr}"

    class Meta:
        unique_together = ('cart', 'product') # Prevent duplicate products in the same cart
