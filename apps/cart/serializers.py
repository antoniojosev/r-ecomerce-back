from rest_framework import serializers
from apps.products.serializers.serializers import ProductSerializer
from apps.products.models import Product
from .models import Cart, CartItem


class CartItemSerializer(serializers.ModelSerializer):
    cart_id = serializers.PrimaryKeyRelatedField(
        queryset=Cart.objects.all(),
        required=True,
        write_only=True,
        source='cart'
    )
    product = ProductSerializer(read_only=True)
    product_id = serializers.PrimaryKeyRelatedField(
        queryset=Product.objects.all(),
        required=True,
        write_only=True,
        source='product'
    )

    class Meta:
        model = CartItem
        fields = [
            'id', 
            'product', 
            'product_id', 
            'quantity',
            'cart_id',
        ]
        read_only_fields = ['id', 'product']

    def create(self, validated_data):
        product = validated_data.get('product')
        quantity = validated_data.get('quantity')
        cart = validated_data.get('cart')
        
        # Buscar o crear el item del carrito
        cart_item, created = CartItem.objects.get_or_create(
            cart=cart,
            product=product,
            defaults={'quantity': quantity}
        )
        
        # Si ya existía, actualizamos la cantidad
        if not created:
            cart_item.quantity = quantity
            cart_item.save()

        return cart_item


class CartAddItemSerializer(serializers.ModelSerializer):
    """
    Serializer para agregar productos al carrito.
    Soporta procesar tanto un solo item como múltiples items con many=True.
    """
    product_id = serializers.PrimaryKeyRelatedField(
        queryset=Product.objects.all(),
        required=True,
        write_only=True,
        source='product'
    )
    product = ProductSerializer(read_only=True)
    cart_id = serializers.PrimaryKeyRelatedField(
        queryset=Cart.objects.all(),
        required=True,
        write_only=True,
        source='cart'
    )

    class Meta:
        model = CartItem
        fields = [
            'id',
            'product',
            'product_id',
            'quantity',
            'cart_id',
        ]
        read_only_fields = ['id', 'product']
    
    def validate_quantity(self, value):
        """Validar que la cantidad sea un número positivo."""
        if value <= 0:
            raise serializers.ValidationError("La cantidad debe ser mayor que cero.")
        return value
    
    def create(self, validated_data):
        """
        Crear o actualizar un item del carrito.
        Si el producto ya existe en el carrito, incrementa la cantidad.
        """
        product = validated_data.get('product')
        quantity = validated_data.get('quantity', 1)
        cart = validated_data.get('cart')
        
        # Busca si existe un item para este carrito y producto
        try:
            cart_item = CartItem.objects.get(cart=cart, product=product)
            # Si existe, incrementa la cantidad
            cart_item.quantity += quantity
            cart_item.save()
        except CartItem.DoesNotExist:
            # Si no existe, crea uno nuevo
            cart_item = CartItem.objects.create(
                cart=cart,
                product=product,
                quantity=quantity
            )

        return cart_item


class CartItemUpdateSerializer(serializers.Serializer):
    """
    Serializer para actualizar la cantidad de uno o varios productos en el carrito o eliminarlos.
    """
    item_id = serializers.UUIDField(required=True)
    quantity = serializers.IntegerField(required=True)

    def validate_quantity(self, value):
        """Validar que la cantidad sea un número no negativo."""
        if value < 0:
            raise serializers.ValidationError("La cantidad no puede ser negativa.")
        return value
    
    def validate(self, data):
        """Validar que el item exista y pertenezca al carrito del usuario."""
        request = self.context.get('request')
        item_id = data.get('item_id')
        
        try:
            # Obtenemos el carrito del usuario y verificamos que el item le pertenezca
            cart = Cart.objects.get(user=request.user)
            try:
                self.cart_item = CartItem.objects.get(pk=item_id, cart=cart)
            except CartItem.DoesNotExist:
                raise serializers.ValidationError({"item_id": "Item no encontrado en su carrito."})
        except Cart.DoesNotExist:
            raise serializers.ValidationError({"detail": "El usuario no tiene un carrito."})
            
        return data
    
    def update(self):
        """Actualiza o elimina el item según la cantidad."""
        quantity = self.validated_data.get('quantity')
        
        if quantity == 0:
            # Si la cantidad es 0, eliminar el item
            self.cart_item.delete()
            return None
        else:
            # Actualizar la cantidad
            self.cart_item.quantity = quantity
            self.cart_item.save()
            return self.cart_item


class CartItemsBulkUpdateSerializer(serializers.Serializer):
    """
    Serializer para actualizar la cantidad de múltiples productos en el carrito en una sola operación.
    """
    items = serializers.ListField(
        child=CartItemUpdateSerializer(),
        required=True,
        allow_empty=False
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.updated_items = []
        self.deleted_items = []

    def validate(self, data):
        """Valida que todos los items pertenezcan al carrito del usuario."""
        request = self.context.get('request')
        
        try:
            self.cart = Cart.objects.get(user=request.user)
        except Cart.DoesNotExist:
            raise serializers.ValidationError({"detail": "El usuario no tiene un carrito."})
            
        return data

    def update(self):
        """Actualiza o elimina los items según las cantidades proporcionadas."""
        self.updated_items = []
        self.deleted_items = []
        
        for item_data in self.validated_data['items']:
            item_id = item_data['item_id']
            quantity = item_data['quantity']
            
            try:
                cart_item = CartItem.objects.get(pk=item_id, cart=self.cart)
                
                if quantity == 0:
                    # Si la cantidad es 0, eliminar el item
                    self.deleted_items.append(item_id)
                    cart_item.delete()
                else:
                    # Actualizar la cantidad
                    cart_item.quantity = quantity
                    cart_item.save()
                    self.updated_items.append(cart_item)
            except CartItem.DoesNotExist:
                # Este error no debería ocurrir ya que validamos los items en validate()
                # pero lo manejamos por si acaso
                pass
        
        return {
            'updated_items': self.updated_items,
            'deleted_items': self.deleted_items
        }


class CartSerializer(serializers.ModelSerializer):
    items = CartItemSerializer(many=True, read_only=True)
    user = serializers.ReadOnlyField(source='user.username')
    total_items = serializers.SerializerMethodField()

    class Meta:
        model = Cart
        fields = ['id', 'user', 'items', 'total_items', 'created_at', 'updated_at']
        read_only_fields = ['id', 'user', 'items', 'total_items', 'created_at', 'updated_at']

    def get_total_items(self, obj):
        return obj.items.count() # Or sum quantities: sum(item.quantity for item in obj.items.all())