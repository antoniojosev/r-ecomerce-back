"""
Servicio de negocio para órdenes (Business Object).

Este módulo contiene la lógica de negocio relacionada con la creación,
gestión y procesamiento de órdenes, siguiendo principios SOLID.
"""

from collections import defaultdict
from decimal import Decimal
from typing import Dict, List, Set, Tuple, Optional, Any
from dataclasses import dataclass

from django.db import transaction
from django.db.models.query import QuerySet

from apps.orders.models import Order, OrderItem
from apps.products.models import Product
from apps.profiles.models import Address
from apps.cart.models import CartItem

from django.contrib.auth import get_user_model
User = get_user_model()


@dataclass
class OrderResultDTO:
    """DTO para los resultados de operaciones con órdenes."""
    success: bool
    orders: List[Order] = None
    error_message: str = None
    product_errors: List[Dict] = None
    
    def __post_init__(self):
        if self.orders is None:
            self.orders = []
        if self.product_errors is None:
            self.product_errors = []
        
    @property
    def count(self) -> int:
        """Retorna la cantidad de órdenes creadas."""
        return len(self.orders)

@dataclass
class ObjectResultDTO:
    """DTO para los resultados de operaciones con órdenes."""
    success: bool
    object: any = None
    error_message: str = None
    object_errors: Dict = None
    
    def __post_init__(self):
        if self.object is None:
            self.object = None
        if self.object_errors is None:
            self.object_errors = []


@dataclass
class OrderItemDTO:
    """DTO para representar un item de orden (producto y cantidad)."""
    product_id: str
    quantity: int
    product: Product = None


@dataclass
class OrderInputDTO:
    """DTO para los datos de entrada necesarios para crear órdenes."""
    user_id: str
    items: List[Dict]
    shipping_data: Dict


@dataclass
class ProductItemDTO:
    """DTO para representar un producto y su cantidad en una orden."""
    product: Product
    quantity: int


class ProductValidator:
    """
    Clase responsable de validar los productos para una orden.
    Implementa el principio de responsabilidad única.
    """
    
    @staticmethod
    def validate_products(items_data: List[Dict], user) -> Tuple[Dict[str, List[ProductItemDTO]], List[Dict]]:
        """
        Valida productos y los agrupa por vendedor.
        
        Args:
            items_data: Lista de diccionarios con datos de productos
            user: Usuario que realiza la compra
            
        Returns:
            Tuple con:
            - Diccionario de productos agrupados por vendedor
            - Lista de errores de productos
        """
        products_by_seller = defaultdict(list)
        product_errors = []
        processed_product_ids = set()  # Para evitar duplicados
        for item in items_data:

            product_id = item.get('product_id')
            quantity = item.get('quantity', 1)
            
            # Si ya procesamos este producto, lo saltamos
            if product_id in processed_product_ids:
                continue
                
            processed_product_ids.add(product_id)
            
            try:
                product = Product.objects.get(id=product_id)
                
                # Validar que el comprador no sea el vendedor
                if ProductValidator._is_own_product(product, user):
                    product_errors.append(
                        ProductValidator._create_error(product_id, product.name, 'own_product',
                                                        f"No puedes comprar tu propio producto: {product.name}")
                    )
                    continue
                
                # Validar disponibilidad (producto no pausado)
                if ProductValidator._is_paused(product):
                    product_errors.append(
                        ProductValidator._create_error(product_id, product.name, 'paused_product',
                                                        f"El producto {product.name} no está disponible actualmente")
                    )
                    continue
                    
                # Validar stock suficiente
                if ProductValidator._insufficient_stock(product, quantity):
                    product_errors.append(
                        ProductValidator._create_error(product_id, product.name, 'insufficient_stock',
                                                        f"Stock insuficiente para {product.name}. " +
                                                        f"Disponible: {product.stock}, Solicitado: {quantity}")
                    )
                    continue
                
                # Agrupar productos válidos por vendedor
                products_by_seller[product.seller.id].append(
                    ProductItemDTO(product, quantity)
                )
            except Product.DoesNotExist:
                product_errors.append(
                    ProductValidator._create_error(product_id, None, 'product_not_found',
                                                   f"El producto con ID {product_id} no existe")
                )
                continue
        
        return products_by_seller, product_errors
    
    @staticmethod
    def validate_product(item_data: Dict, user) -> ProductItemDTO:
        """
        Valida productos y los agrupa por vendedor.
        
        Args:
            items_data: Lista de diccionarios con datos de productos
            user: Usuario que realiza la compra
            
        Returns:
            - Producto
            - Error de producto
        """

        product_id = item_data.get('product_id')
        quantity = item_data.get('quantity', 1)
        
        try:
            product = Product.objects.get(id=product_id)
            
            # Validar que el comprador no sea el vendedor
            if ProductValidator._is_own_product(product, user):
                return ObjectResultDTO(
                    success=False, 
                    error_message="Hay productos que no pudieron ser procesados. Verifica los errores reportados.",
                    object_errors=ProductValidator._create_error(product_id, product.name, 'own_product',
                                                    f"No puedes comprar tu propio producto: {product.name}")
                )
            
            # Validar disponibilidad (producto no pausado)
            if ProductValidator._is_paused(product):
                return ObjectResultDTO(
                    success=False, 
                    error_message="Hay productos que no pudieron ser procesados. Verifica los errores reportados.",
                    object_errors=ProductValidator._create_error(product_id, product.name, 'paused_product',
                                                    f"El producto {product.name} no está disponible actualmente")
                 )
            
            # Validar stock suficiente
            if ProductValidator._insufficient_stock(product, quantity):
                return ObjectResultDTO(
                    success=False, 
                    error_message="Hay productos que no pudieron ser procesados. Verifica los errores reportados.",
                    object_errors= ProductValidator._create_error(product_id, product.name, 'insufficient_stock',
                                                    f"Stock insuficiente para {product.name}. " +
                                                    f"Disponible: {product.stock}, Solicitado: {quantity}")
                )
            
            # Agrupar productos válidos por vendedor
            product_by_seller = ProductItemDTO(product, quantity)
            
        except Product.DoesNotExist:
            return ObjectResultDTO(
                    success=False, 
                    error_message="Hay productos que no pudieron ser procesados. Verifica los errores reportados.",
                    object_errors=ProductValidator._create_error(product_id, None, 'product_not_found',
                                                f"El producto con ID {product_id} no existe")
            )
        
        return ObjectResultDTO(
            success=True,
            object=product_by_seller
        )
    @staticmethod
    def _is_own_product(product: Product, user) -> bool:
        """Verifica si el producto pertenece al usuario."""
        return product.seller == user
    
    @staticmethod
    def _is_paused(product: Product) -> bool:
        """Verifica si el producto está pausado."""
        return product.paused
    
    @staticmethod
    def _insufficient_stock(product: Product, quantity: int) -> bool:
        """Verifica si hay stock insuficiente."""
        return quantity > product.stock
    
    @staticmethod
    def _create_error(product_id, product_name, error_type, message) -> Dict:
        """Crea un diccionario de error estándar."""
        error = {
            'product_id': product_id,
            'error_type': error_type,
            'message': message
        }
        if product_name:
            error['product_name'] = product_name
        return error


class AddressService:
    """
    Clase responsable de gestionar las direcciones de envío.
    Implementa el principio de responsabilidad única.
    """
    
    @staticmethod
    def process_shipping_address(shipping_data: Dict, user) -> Optional[Address]:
        """
        Procesa los datos de dirección de envío.
        
        Args:
            shipping_data: Diccionario con datos de dirección
            user: Usuario actual
            
        Returns:
            Address: Objeto de dirección procesado o None si hay error
        """
        try:
            if  shipping_data.get('address_id', None) :
                address_id = shipping_data['address_id']
                return Address.objects.get(pk=address_id, user=user)
            elif shipping_data.get('new_address', None):
                address_data = shipping_data['new_address']
                return Address.objects.create(user=user, **address_data)
        except Exception as e:
            return None
        
        return None


class OrderCreator:
    """
    Clase responsable de crear órdenes en la base de datos.
    Implementa el principio de responsabilidad única.
    """
    
    @staticmethod
    @transaction.atomic
    def create_orders(products_by_seller: Dict, shipping_address: Address, user) -> List[Order]:
        """
        Crea órdenes agrupadas por vendedor.
        
        Args:
            products_by_seller: Productos agrupados por vendedor
            shipping_address: Dirección de envío
            user: Usuario que realiza la compra
            
        Returns:
            List[Order]: Lista de órdenes creadas
        """
        created_orders = []
        
        for _seller_id, items in products_by_seller.items():
            # Crear la orden con total inicial en cero
            order = Order.objects.create(
                user=user,
                shipping_address=shipping_address,
                total=Decimal('0.00')  # Se actualiza después
            )
            
            # Procesar los items de la orden y calcular total
            total_amount = OrderCreator._process_order_items(order, items)
            
            # Actualizar total de la orden
            order.total = total_amount
            order.save()
            
            created_orders.append(order)
        
        return created_orders
    
    @staticmethod
    def _process_order_items(order: Order, items: List[ProductItemDTO]) -> Decimal:
        """
        Procesa los items de una orden y calcula el total.
        
        Args:
            order: Orden a la que pertenecen los items
            items: Lista de productos y cantidades
            
        Returns:
            Decimal: Total calculado para la orden
        """
        total_amount = Decimal('0.00')
        
        for item in items:
            product = item.product
            quantity = item.quantity
            
            # Obtener valores de precio actuales
            discount_porcentaje = product.discount/100
            original_price = Decimal(product.original_price) * Decimal(quantity)
            discount_mount = original_price * Decimal(discount_porcentaje)
            price =  original_price - Decimal(discount_mount)
            discount = product.discount
            
            # Crear item de orden
            OrderItem.objects.create(
                order=order,
                product=product,
                quantity=quantity,
                price=price,
                original_price=original_price,
                discount=discount
            )
            
            # Calcular subtotal y actualizar total
            item_total = price
            total_amount += item_total
            
            # Actualizar stock del producto
            product.stock -= quantity
            product.save()
            
        return total_amount


class OrdersBo:
    """
    Clase de servicio de negocio para gestionar órdenes.
    
    Coordina el proceso completo de creación de órdenes utilizando
    las clases especializadas para cada responsabilidad.
    """
    
    @transaction.atomic
    def create_orders(self, order_input: OrderInputDTO) -> OrderResultDTO:
        """
        Método principal para crear órdenes a partir de datos de entrada.
        
        Args:
            order_input: DTO con datos necesarios para crear órdenes
            
        Returns:
            OrderResultDTO: Resultado de la operación
        """        
        try:
            user = User.objects.get(id=order_input.user_id)
        except User.DoesNotExist:
            return OrderResultDTO(success=False, error_message="Usuario no válido")
        
        # Validar que hay productos en la solicitud
        if not order_input.items:
            return OrderResultDTO(False, error_message="Se requiere al menos un producto para crear un pedido#")
            
        # Validar productos y agrupar por vendedor
        products_by_seller, product_errors = ProductValidator.validate_products(order_input.items, user)
        
        # Verificar si hay errores de productos
        if product_errors:
            return OrderResultDTO(
                success=False, 
                error_message="Hay productos que no pudieron ser procesados. Verifica los errores reportados.",
                product_errors=product_errors
            )
            
        # Verificar que haya productos válidos
        if not products_by_seller:
            return OrderResultDTO(
                success=False, 
                error_message="No hay productos válidos para ordenar."
            )
        # Procesar dirección de envío
        shipping_address = AddressService.process_shipping_address(order_input.shipping_data, user)
        if not shipping_address:
            return OrderResultDTO(success=False, error_message="No se pudo procesar la dirección de envío")
            
        # Crear órdenes
        orders = OrderCreator.create_orders(products_by_seller, shipping_address, user)
        
        return OrderResultDTO(success=True, orders=orders)
    
    @transaction.atomic
    def create_orders_from_items(self, user_id: int, items_data: List[Dict], 
                                shipping_data: Dict) -> OrderResultDTO:
        """
        Crea órdenes agrupadas por vendedor a partir de una lista de productos.
        Método de compatibilidad con la versión anterior.
        
        Args:
            user_id: ID del usuario que realiza la compra
            items_data: Lista de diccionarios con producto y cantidad
            shipping_data: Datos de dirección de envío
            
        Returns:
            OrderResultDTO: Resultado de la operación con las órdenes creadas
        """        
        # Convertir al formato esperado por el nuevo método
        converted_items = [{'product_id': item['product'], 'quantity': item['quantity']} for item in items_data]
        
        # Utilizar el nuevo método centralizado
        order_input = OrderInputDTO(user_id=user_id, items=converted_items, shipping_data=shipping_data)
        return self.create_orders(order_input)
    
    @transaction.atomic
    def create_orders_from_cart(self, user_id: int, shipping_data: Dict) -> OrderResultDTO:
        """
        Crea órdenes agrupadas por vendedor a partir del carrito del usuario.
        
        Args:
            user_id: ID del usuario que realiza la compra
            shipping_data: Datos de dirección de envío
            
        Returns:
            OrderResultDTO: Resultado de la operación con las órdenes creadas
        """
        try:
            user = User.objects.get(id=user_id)
        except User.DoesNotExist:
            return OrderResultDTO(False, error_message="Usuario no válido")
        
        # Obtener productos del carrito
        cart_items = CartItem.objects.filter(cart__user=user).select_related('product')
        
        # Verificar si el carrito está vacío
        if not cart_items.exists():
            return OrderResultDTO(False, error_message="Tu carrito está vacío")
        
        # Convertir items del carrito al formato esperado por el nuevo método
        items_data = [{'product_id': str(item.product.id), 'quantity': item.quantity} for item in cart_items]
        
        # Utilizar el método centralizado
        order_input = OrderInputDTO(user_id=user_id, items=items_data, shipping_data=shipping_data)
        result = self.create_orders(order_input)
        
        # Si se crearon órdenes exitosamente, limpiar el carrito
        if result.success and result.count > 0:
            cart_items.delete()
            
        return result
    
    def get_user_orders(self, user_id: str) -> QuerySet:
        """
        Obtiene las órdenes de un usuario ordenadas por fecha de creación.
        
        Args:
            user_id: ID del usuario
            
        Returns:
            QuerySet: Órdenes del usuario
        """
        return Order.objects.filter(user_id=user_id).order_by('-created_at')