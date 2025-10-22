from django.db import models
from django.utils import timezone
from utils.models import BaseModel
from django.contrib.auth import get_user_model
from apps.products.models import Product
from apps.profiles.models import Address # Correct import path for Address

User = get_user_model()
class Question(BaseModel):
    """
    Represents a question or a reply within a discussion thread about a product.
    Uses a self-referencing foreign key 'parent' to create threads.
    """
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='questions')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='questions')
    parent = models.ForeignKey('self', null=True, blank=True, on_delete=models.CASCADE, related_name='replies')
    text = models.TextField() # Renamed from 'question' for clarity
    is_answered = models.BooleanField(default=False) # Simplified answer tracking
    answered_at = models.DateTimeField(null=True, blank=True)

    def mark_as_answered(self):
        """Marks the question as answered."""
        if not self.is_answered:
            self.is_answered = True
            self.answered_at = timezone.now()
            self.save()

    def __str__(self):
        return f"Question by {self.user.username} on {self.product.name}" + (f" (Reply to {self.parent.id})" if self.parent else "")

class Order(BaseModel):
    """Represents a customer order."""
    STATUS_CHOICES = [
        ('pending', 'Pendiente'),
        ('processing', 'Procesando'),
        ('shipping', 'En camino'),
        ('delivered', 'Entregado'),
        ('cancelled', 'Cancelado')
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='orders')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    total = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    shipping_address = models.ForeignKey(
        Address, 
        on_delete=models.SET_NULL, 
        related_name='orders', 
        null=True, blank=True
    )

    def __str__(self):
        return f"Order {self.id} by {self.user.username} - Status: {self.get_status_display()}"

class OrderItem(BaseModel):
    """Represents an item within an order."""
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(
        Product, 
        on_delete=models.SET_NULL, 
        related_name='order_items',
        null=True, blank=True
    )
    quantity = models.PositiveIntegerField()
    price = models.DecimalField(max_digits=10, decimal_places=2) # Price at the time of order
    original_price = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True) # Original price before discount
    discount = models.IntegerField(default=0) # Discount percentage at the time of order

    def __str__(self):
        return f"{self.quantity} x {self.product.name} in Order {self.order.id}"

    class Meta:
        # Ensure a product only appears once per order? Or allow multiple lines for same product?
        # unique_together = ('order', 'product') # Optional: Uncomment if needed
        pass

    def get_total(self):
        discount = self.discount/100
        return (self.original_price * self.quantity) - ((self.original_price * self.quantity) * discount/100)
    
    @property
    def seller(self):
        return self.product.seller
        