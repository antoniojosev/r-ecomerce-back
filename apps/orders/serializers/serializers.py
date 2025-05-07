from rest_framework import serializers
from ..models import Order, OrderItem, Question
from apps.profiles.models import Address
from apps.products.models import Product
from decimal import Decimal
from ..services.OrdersBo import OrdersBo, ProductValidator, ObjectResultDTO
from apps.products.serializers.serializers import ProductCheckoutSerializer
from apps.profiles.serializers.serializers import AddressSerializer
from apps.users.serializers.token import UserSerializer

class QuestionSerializer(serializers.ModelSerializer):
    user = serializers.ReadOnlyField(source='user.username') # Show username, not ID
    replies = serializers.SerializerMethodField()

    class Meta:
        model = Question
        fields = ['id', 'product', 'user', 'parent', 'text', 'is_answered', 'answered_at', 'created_at', 'replies']
        read_only_fields = ['is_answered', 'answered_at', 'created_at', 'replies']

    def get_replies(self, obj):
        # Recursively serialize replies if needed, be cautious of depth
        if obj.replies.exists():
            return QuestionSerializer(obj.replies.all(), many=True, context=self.context).data
        return None

class OrderItemCreateSerializer(serializers.ModelSerializer):
    """
    Serializer for creating order items with proper validation
    """
    class Meta:
        model = OrderItem
        fields = ['product', 'quantity']

    def validate(self, data):
        """
        Validate that the product is available and has enough stock
        """
        user = self.context['request'].user
        product = data['product']
        quantity = data['quantity']
        ProductValidator.validate_product(
            {
                'product_id': product.id, 
                'quantity': quantity
            },
            user
        )

        return data

class GroupedOrderItemSerializer(serializers.Serializer):
    """
    Serializer para validar items en órdenes agrupadas.
    Usa product_id en lugar de un objeto producto completo.
    """
    product_id = serializers.UUIDField(required=True)
    quantity = serializers.IntegerField(min_value=1, required=True)
    
    def validate_product_id(self, product_id):
        """
        Validar que el producto exista
        """
        try:
            Product.objects.get(id=product_id)
            return product_id
        except Product.DoesNotExist:
            raise serializers.ValidationError(f"El producto con ID {product_id} no existe")
    
    def validate(self, data):
        """
        Validar que el producto esté disponible, tenga stock suficiente y no sea del propio usuario
        """
        product_id = data['product_id']
        quantity = data['quantity']
        user = self.context['request'].user
        
        product = Product.objects.get(id=product_id)
            
        # Validar que el producto no esté pausado
        if product.paused:
            raise serializers.ValidationError({
                'product_id': f"El producto {product.name} no está disponible actualmente"
            })
            
        # Validar que haya suficiente stock
        if quantity > product.stock:
            raise serializers.ValidationError({
                'quantity': f"Stock insuficiente para {product.name}. Disponible: {product.stock}"
            })
            
        # Validar que el comprador no sea el vendedor
        if product.seller == user:
            raise serializers.ValidationError({
                'product_id': f"No puedes comprar tu propio producto: {product.name}"
            })
            
        # Añadir el producto al objeto validado para usarlo después
        data['product'] = product
        return data

class OrderItemSerializer(serializers.ModelSerializer):
    product = ProductCheckoutSerializer()

    class Meta:
        model = OrderItem
        fields = [
            'id', 
            'product', 
            'quantity', 
            'price', 
            'original_price', 
            'discount'
        ]


class OrderCreateSerializer(serializers.ModelSerializer):
    """
    Serializer for creating orders with items and address handling
    """
    items = OrderItemCreateSerializer(many=True)
    address = serializers.PrimaryKeyRelatedField(
        queryset=Address.objects.all(),
        required=False,
        write_only=True,
        source='shipping_address'
    )
    new_address = AddressSerializer(required=False)
    
    class Meta:
        model = Order
        fields = ['items', 'address', 'new_address']
        
    def validate(self, data):
        # Validate shipping address information
        if 'shipping_address' not in data and 'new_address' not in data:
            raise serializers.ValidationError("Either an existing address ID or a new address must be provided")
            
        if 'shipping_address' in data and 'new_address' in data:
            raise serializers.ValidationError("Provide either an existing address ID or a new address, not both")
            
        # If using existing address, verify it belongs to the user
        if 'shipping_address' in data:
            user = self.context['request'].user
            address = data['shipping_address']
            if address.user != user:
                raise serializers.ValidationError("The specified address does not belong to you")
            
        # Ensure at least one item is included
        if 'items' not in data or not data['items']:
            raise serializers.ValidationError("At least one item is required")
            
        return data
        
    def create(self, validated_data):
        items_data = validated_data.pop('items')
        user = self.context['request'].user
        
        # Handle shipping address
        shipping_address = None
        if 'shipping_address' in validated_data:
            shipping_address = validated_data.pop('shipping_address')
        elif 'new_address' in validated_data:
            address_data = validated_data.pop('new_address')
            shipping_address = Address.objects.create(user=user, **address_data)
            
        # Create order
        order = Order.objects.create(
            user=user,
            shipping_address=shipping_address,
            total=0  # Will calculate after adding items
        )
        
        # Create order items and calculate totals
        total_amount = Decimal('0.00')
        for item_data in items_data:
            product = item_data['product']
            quantity = item_data['quantity']
            
            # Set price values from current product state
            price = product.price
            original_price = product.original_price if product.original_price else price
            discount = product.discount
            
            # Create order item
            order_item = OrderItem.objects.create(
                order=order,
                product=product,
                quantity=quantity,
                price=price,
                original_price=original_price,
                discount=discount
            )
            
            # Calculate item total and add to order total
            item_total = price * Decimal(quantity)
            total_amount += item_total
            
            # Update product stock
            product.stock -= quantity
            product.save()
        
        # Update order total
        order.total = total_amount
        order.save()
        
        return order


class OrderGroupedCreateSerializer(serializers.Serializer):
    """
    Serializer para crear órdenes agrupadas por vendedor
    """
    items = GroupedOrderItemSerializer(many=True, required=True)
    address = serializers.PrimaryKeyRelatedField(
        queryset=Address.objects.all(),
        required=False,
        write_only=True
    )
    new_address = AddressSerializer(required=False)
    
    def validate(self, data):
        """
        Valida los datos para la creación de órdenes agrupadas
        """
        # Validar información de dirección
        if 'address' not in data and 'new_address' not in data:
            raise serializers.ValidationError({
                "address": ["Se requiere información de dirección de envío (address o new_address)"]
            })
            
        if 'address' in data and 'new_address' in data:
            raise serializers.ValidationError({
                "address": ["Proporcione una dirección existente (address) o una nueva dirección (new_address), no ambas"]
            })
            
        # Validar que hay items
        if not data.get('items'):
            raise serializers.ValidationError({
                "items": ["Se requiere al menos un producto para crear un pedido"]
            })
        
        # Si usa una dirección existente, verificar que pertenezca al usuario
        if 'address' in data:
            user = self.context['request'].user
            address = data['address']
            if address.user != user:
                raise serializers.ValidationError({
                    "address": ["La dirección especificada no le pertenece"]
                })
                
        return data
    
    def create(self, validated_data):
        """
        Crea órdenes agrupadas por vendedor utilizando el servicio de negocio
        """
        # Preparar datos de dirección
        shipping_data = {}
        if 'address' in validated_data:
            shipping_data['address'] = validated_data['address'].id
        elif 'new_address' in validated_data:
            shipping_data['new_address'] = validated_data['new_address']
        
        # Obtener el usuario actual
        user = self.context['request'].user
        
        # Convertir los ítems validados al formato esperado por el servicio
        items_data = []
        for item in validated_data.get('items', []):
            items_data.append({
                'product': item['product_id'],
                'quantity': item['quantity']
            })
        
        # Crear órdenes agrupadas a través del servicio de negocio
        order_service = OrdersBo()
        result = order_service.create_orders_from_items(
            user_id=user.id,
            items_data=items_data,
            shipping_data=shipping_data
        )
        
        # Manejar errores de productos del servicio de negocio
        if not result.success:
            error_data = {'detail': result.error_message}
            if result.product_errors:
                error_data['product_errors'] = result.product_errors
            raise serializers.ValidationError(error_data)
            
        return result.orders
        
    

class OrderSerializer(serializers.ModelSerializer):
    user = UserSerializer()
    items = OrderItemSerializer(many=True, read_only=True)
    shipping_address = AddressSerializer(read_only=True)
    seller = serializers.SerializerMethodField()

    class Meta:
        model = Order
        fields = [
            'id', 
            'user', 
            'seller',
            'status', 
            'total', 
            'shipping_address', 
            'items',
            'created_at', 
        ]

    def get_seller(self, obj: Order):
        return UserSerializer(obj.items.first().seller).data

class OrderFromCartSerializer(serializers.Serializer):
    """
    Serializer para crear órdenes a partir del carrito
    """
    address = serializers.PrimaryKeyRelatedField(
        queryset=Address.objects.all(),
        required=False,
        write_only=True
    )
    new_address = AddressSerializer(required=False)
    
    def validate(self, data):
        """
        Valida los datos para la creación de órdenes desde el carrito
        """
        # Validar información de dirección
        if 'address' not in data and 'new_address' not in data:
            raise serializers.ValidationError({
                "address": ["Se requiere información de dirección de envío (address o new_address)"]
            })
            
        if 'address' in data and 'new_address' in data:
            raise serializers.ValidationError({
                "address": ["Proporcione una dirección existente (address) o una nueva dirección (new_address), no ambas"]
            })
        
        # Si usa una dirección existente, verificar que pertenezca al usuario
        if 'address' in data:
            user = self.context['request'].user
            address = data['address']
            if address.user != user:
                raise serializers.ValidationError({
                    "address": ["La dirección especificada no le pertenece"]
                })
                
        return data
    
    def create(self, validated_data):
        """
        Crea órdenes a partir del carrito utilizando el servicio de negocio
        """
        # Preparar datos de dirección
        shipping_data = {}
        if 'address' in validated_data:
            shipping_data['address'] = validated_data['address'].id
        elif 'new_address' in validated_data:
            shipping_data['new_address'] = validated_data['new_address']
        
        # Obtener el usuario actual
        user = self.context['request'].user
        
        # Crear órdenes a través del servicio de negocio
        order_service = OrdersBo()
        result = order_service.create_orders_from_cart(
            user_id=user.id,
            shipping_data=shipping_data
        )
        
        # Manejar errores de productos del servicio de negocio
        if not result.success:
            error_data = {'detail': result.error_message}
            if result.product_errors:
                error_data['product_errors'] = result.product_errors
            raise serializers.ValidationError(error_data)
            
        return result.orders

    def to_representation(self, instance):
        # Use OrderSerializer to convert each order into its representation
        return OrderSerializer(instance, many=True, context=self.context).data

class OrderInputItemSerializer(serializers.Serializer):
    """
    Serializer para validar los ítems de entrada en la creación de órdenes.
    """
    product_id = serializers.UUIDField(required=True)
    quantity = serializers.IntegerField(min_value=1, required=True)

    def validate(self, data):
        """Valida que el producto exista"""

        user = self.context['request'].user
        product_id = data['product_id']
        quantity = data['quantity']
        validation : ObjectResultDTO = ProductValidator.validate_product(
            {
                'product_id': product_id, 
                'quantity': quantity
            },
            user
        )
        if(validation.success is False):
            raise serializers.ValidationError({
                'product_id': validation.object_errors
            })
        return data


class OrderInputSerializer(serializers.Serializer):
    """
    Serializer principal para la creación de órdenes.
    Recibe una lista de productos con sus cantidades y datos de dirección.
    """
    items = OrderInputItemSerializer(many=True, required=True)
    address_id = serializers.UUIDField(required=False, write_only=True)
    new_address = AddressSerializer(required=False)
    
    def validate(self, data):
        """
        Validación principal para la creación de órdenes
        """
        # Validar que existe información de dirección
        if 'address_id' not in data and 'new_address' not in data:
            raise serializers.ValidationError({
                "address_error": "Se requiere información de dirección (address_id o new_address)"
            })
            
        if 'address_id' in data and 'new_address' in data:
            raise serializers.ValidationError({
                "address_error": "Proporcione una dirección existente o una nueva dirección, no ambas"
            })
        
        # Validar que haya al menos un ítem
        if not data.get('items'):
            raise serializers.ValidationError({
                "items": "Se requiere al menos un producto para crear un pedido"
            })
            
        # Si es dirección existente, validar que pertenezca al usuario
        if 'address_id' in data:
            user = self.context['request'].user
            try:
                address = Address.objects.get(id=data['address_id'])
                if address.user != user:
                    raise serializers.ValidationError({
                        "address_error": "La dirección especificada no le pertenece"
                    })
            except Address.DoesNotExist:
                raise serializers.ValidationError({
                    "address_error": "La dirección especificada no existe"
                })
            
        return data
    
    #def create(self, validated_data) -> List[Order]:
        """
        Prepara los datos y utiliza el servicio de negocio para crear las órdenes
        """
        # Obtener usuario actual
        """user = self.context['request'].user
        
        # Preparar datos de productos
        items_data = []
        for item in validated_data.get('items', []):
            items_data.append({
                'product_id': item['product_id'],
                'quantity': item['quantity']
            })
            
        # Preparar datos de dirección
        shipping_data = {}
        if 'address_id' in validated_data:
            shipping_data['address_id'] = validated_data['address_id']
        elif 'new_address' in validated_data:
            shipping_data['new_address'] = validated_data['new_address']
            
        # Crear DTO de entrada para el servicio
        order_input = OrderInputDTO(
            user_id=user.id,
            items=items_data,
            shipping_data=shipping_data
        )
        
        # Utilizar el servicio para crear las órdenes
        order_service = OrdersBo()
        result = order_service.create_orders(order_input)
        
        # Manejar errores
        if not result.success:
            error_data = {'detail': result.error_message}
            if result.product_errors:
                error_data['product_errors'] = result.product_errors
            raise serializers.ValidationError(error_data)
            
        # Guardar las órdenes para el to_representation
        self.orders = result.orders
        return result.orders"""
