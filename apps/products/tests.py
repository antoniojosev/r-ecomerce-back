from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from decimal import Decimal
from rest_framework import status
from rest_framework.test import APITestCase
from utils.tests import BaseTestCase

from apps.profiles.models import Profile
from apps.users.models import User
from apps.products.models import Product, Brand, Category, ProductFeature, ProductSpecification, ProductImage

class ProductModelTests(TestCase):
    """Test cases for Product model and related models."""
    
    def setUp(self):
        # Create test user
        self.user = User.objects.create_user(
            username='seller',
            email='seller@example.com',
            name='Seller',
            last_name='User',
            password='password123'
        )
        
        # Create profile for seller
        Profile.objects.create(
            user=self.user,
            company_name="Seller Company",
            dni="87654321",
            rif="J-87654321-9",
            phone="+58987654321",
            is_seller=True
        )
        
        # Create test category and brand
        self.category = Category.objects.create(name="Electronics")
        self.brand = Brand.objects.create(name="Test Brand")
        
        # Create test product
        self.product = Product.objects.create(
            name="Test Product",
            brand=self.brand,
            category=self.category,
            sku="TST-12345",
            price=Decimal("99.99"),
            original_price=Decimal("129.99"),
            discount=20,
            seller=self.user,
            stock=100
        )
    
    def test_category_slug_generation(self):
        """Test that slug is automatically created for Category"""
        category = Category.objects.get(name="Electronics")
        self.assertEqual(category.slug, "electronics")
        
        # Test with special characters and spaces
        special_category = Category.objects.create(name="Home & Kitchen Appliances")
        self.assertEqual(special_category.slug, "home-kitchen-appliances")
    
    def test_brand_slug_generation(self):
        """Test that slug is automatically created for Brand"""
        brand = Brand.objects.get(name="Test Brand")
        self.assertEqual(brand.slug, "test-brand")
        
        # Test with special characters
        special_brand = Brand.objects.create(name="Apple & Co.")
        self.assertEqual(special_brand.slug, "apple-co")
    
    def test_product_str_representation(self):
        """Test the string representation of a Product"""
        self.assertEqual(str(self.product), "Test Product")
    
    def test_product_toggle_pause(self):
        """Test the toggle_pause method of a Product"""
        # Initially product should not be paused
        self.assertFalse(self.product.paused)
        self.assertIsNone(self.product.paused_date)
        
        # Pause the product
        is_paused = self.product.toggle_pause()
        self.assertTrue(is_paused)
        self.assertTrue(self.product.paused)
        self.assertIsNotNone(self.product.paused_date)
        
        # Store the pause date for comparison
        first_pause_date = self.product.paused_date
        
        # Unpause the product
        is_paused = self.product.toggle_pause()
        self.assertFalse(is_paused)
        self.assertFalse(self.product.paused)
        self.assertIsNone(self.product.paused_date)
        
        # Pause again and check that date is updated
        self.product.toggle_pause()
        self.assertTrue(self.product.paused)
        self.assertIsNotNone(self.product.paused_date)
    
    def test_product_relations(self):
        """Test creating related objects for a product"""
        # Add features
        feature = ProductFeature.objects.create(
            product=self.product,
            feature="Waterproof"
        )
        self.assertEqual(feature.feature, "Waterproof")
        self.assertEqual(feature.product, self.product)
        
        # Add specifications
        spec = ProductSpecification.objects.create(
            product=self.product,
            name="Battery Life",
            value="10 hours"
        )
        self.assertEqual(spec.name, "Battery Life")
        self.assertEqual(spec.value, "10 hours")
        self.assertEqual(spec.product, self.product)
        
        # Check that related objects are accessible through relations
        self.assertEqual(self.product.features.count(), 1)
        self.assertEqual(self.product.specifications.count(), 1)


class ProductAPITests(BaseTestCase):
    """Test cases for Product API endpoints."""
    
    def setUp(self):
        """Set up test data."""
        super().setUp()
        
        # Set user as a seller
        self.user.profile.is_seller = True
        self.user.profile.save()
        
        # Create test category and brand
        self.category = Category.objects.create(name="Electronics")
        self.brand = Brand.objects.create(name="Test Brand")
        
        # Create test product
        self.product = Product.objects.create(
            name="Test Product",
            brand=self.brand,
            category=self.category,
            sku="TST-12345",
            price=Decimal("99.99"),
            original_price=Decimal("129.99"),
            discount=20,
            seller=self.user,
            stock=100
        )
        
        # URLs
        self.products_list_url = reverse('product-list')
        self.product_detail_url = reverse('product-detail', kwargs={'pk': self.product.id})
        self.toggle_pause_url = reverse('product-toggle-pause', kwargs={'pk': self.product.id})
        
        # Create another user (non-seller)
        self.non_seller = User.objects.create_user(
            username='customer',
            email='customer@example.com',
            name='Customer',
            last_name='User',
            password='password123'
        )
        
        # Create profile for non-seller
        Profile.objects.create(
            user=self.non_seller,
            company_name="Customer Company",
            dni="11112222",
            rif="J-11112222-3",
            phone="+58111122223",
            is_seller=False
        )
    
    def test_list_products(self):
        """Test retrieving a list of products."""
        response = self.client.get(self.products_list_url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)  # There should be 1 product
        self.assertEqual(response.data[0]['name'], "Test Product")
    
    def test_retrieve_product(self):
        """Test retrieving a single product."""
        response = self.client.get(self.product_detail_url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['name'], "Test Product")
        self.assertEqual(response.data['price'], "99.99")
        self.assertEqual(response.data['discount'], 20)
    
    def test_create_product_as_seller(self):
        """Test that a seller can create a product."""
        new_product_data = {
            'name': 'New Product',
            'brand_id': str(self.brand.id),
            'category_id': str(self.category.id),
            'sku': 'NEW-12345',
            'price': '149.99',
            'original_price': '199.99',
            'discount': 25,
            'stock': 50,
            'description': 'A new test product',
            'features': [{'feature': 'Wireless'}],
            'specifications': [{'name': 'Weight', 'value': '2.5 kg'}]
        }
        
        response = self.client.post(self.products_list_url, new_product_data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Product.objects.count(), 2)  # Now we should have 2 products
        
        # Check that the product has been created with correct data
        created_product = Product.objects.get(sku='NEW-12345')
        self.assertEqual(created_product.name, 'New Product')
        self.assertEqual(created_product.price, Decimal('149.99'))
        self.assertEqual(created_product.discount, 25)
        
        # Check that features and specifications were created
        self.assertEqual(created_product.features.count(), 1)
        self.assertEqual(created_product.specifications.count(), 1)
    
    def test_create_product_as_non_seller(self):
        """Test that a non-seller cannot create a product."""
        # Switch to the non-seller user
        self.client.logout()
        non_seller_token = self.get_tokens_for_user(self.non_seller)
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {non_seller_token["access"]}')
        
        new_product_data = {
            'name': 'New Product',
            'brand_id': str(self.brand.id),
            'category_id': str(self.category.id),
            'sku': 'NEW-12345',
            'price': '149.99',
            'stock': 50,
        }
        
        response = self.client.post(self.products_list_url, new_product_data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(Product.objects.count(), 1)  # Still only one product
    
    def test_update_product(self):
        """Test updating a product as its seller."""
        update_data = {
            'name': 'Updated Product',
            'price': '129.99',
            'stock': 75
        }
        
        response = self.client.patch(self.product_detail_url, update_data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Refresh from database
        self.product.refresh_from_db()
        
        # Check that fields were updated
        self.assertEqual(self.product.name, 'Updated Product')
        self.assertEqual(self.product.price, Decimal('129.99'))
        self.assertEqual(self.product.stock, 75)
    
    def test_update_product_as_different_seller(self):
        """Test that a seller cannot update another seller's product."""
        # Create another seller
        other_seller = User.objects.create_user(
            username='other_seller',
            email='other@example.com',
            name='Other',
            last_name='Seller',
            password='password123'
        )
        Profile.objects.create(
            user=other_seller,
            company_name="Other Company",
            dni="33334444",
            rif="J-33334444-5",
            phone="+58333344445",
            is_seller=True
        )
        
        # Switch to the other seller
        self.client.logout()
        other_seller_token = self.get_tokens_for_user(other_seller)
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {other_seller_token["access"]}')
        
        update_data = {
            'name': 'Hijacked Product',
            'price': '9.99'
        }
        
        response = self.client.patch(self.product_detail_url, update_data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        
        # Refresh from database and check nothing changed
        self.product.refresh_from_db()
        self.assertEqual(self.product.name, 'Test Product')
        self.assertEqual(self.product.price, Decimal('99.99'))
    
    def test_toggle_pause_product(self):
        """Test toggling pause state of a product."""
        # Initially product should not be paused
        self.assertFalse(self.product.paused)
        
        # Asegurar que estamos autenticados como el vendedor del producto
        # Primero configuramos explícitamente las credenciales ya que podrían haber sido cambiadas por otros tests
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.token["access"]}')
        
        # Pause the product
        response = self.client.post(self.toggle_pause_url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['status'], 'success')
        self.assertTrue(response.data['paused'])
        
        # Refresh from database
        self.product.refresh_from_db()
        self.assertTrue(self.product.paused)
        
        # Unpause the product
        response = self.client.post(self.toggle_pause_url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['status'], 'success')
        self.assertFalse(response.data['paused'])
        
        # Refresh from database
        self.product.refresh_from_db()
        self.assertFalse(self.product.paused)
    
    def test_delete_product(self):
        """Test deleting a product as its seller."""
        response = self.client.delete(self.product_detail_url)
        
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        
        # Product should be soft deleted (not actually removed from DB)
        self.assertEqual(Product.objects.count(), 0)  # 0 from regular manager
        self.assertEqual(Product.all_objects.count(), 1)  # 1 from all_objects manager
        
        # Check that the product is marked as deleted
        product = Product.all_objects.get(pk=self.product.pk)
        self.assertIsNotNone(product.deleted_at)
    
    def test_filter_products(self):
        """Test filtering products by category, brand, and seller."""
        # Create more test data
        other_category = Category.objects.create(name="Clothing")
        other_brand = Brand.objects.create(name="Fashion Brand")
        
        # Create a product in a different category and brand
        Product.objects.create(
            name="T-Shirt",
            brand=other_brand,
            category=other_category,
            sku="TSH-12345",
            price=Decimal("19.99"),
            seller=self.user,
            stock=200
        )
        
        # Filter by original category
        response = self.client.get(f"{self.products_list_url}?category={self.category.id}")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['name'], "Test Product")
        
        # Filter by other category
        response = self.client.get(f"{self.products_list_url}?category={other_category.id}")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['name'], "T-Shirt")
        
        # Filter by brand
        response = self.client.get(f"{self.products_list_url}?brand={other_brand.id}")
        self.assertEqual(response.status_code, status.HTTP_200_OK) 
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['name'], "T-Shirt")
    
    def test_search_products(self):
        """Test searching products by name and description."""
        # Create products with different names/descriptions
        Product.objects.create(
            name="Gaming Laptop",
            description="High performance gaming laptop",
            brand=self.brand,
            category=self.category,
            sku="GAME-12345",
            price=Decimal("1299.99"),
            seller=self.user,
            stock=10
        )
        
        Product.objects.create(
            name="Business Laptop",
            description="Professional laptop for work",
            brand=self.brand,
            category=self.category,
            sku="WORK-12345",
            price=Decimal("999.99"),
            seller=self.user,
            stock=15
        )
        
        # Search by name
        response = self.client.get(f"{self.products_list_url}?search=gaming")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['name'], "Gaming Laptop")
        
        # Search by description
        response = self.client.get(f"{self.products_list_url}?search=professional")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['name'], "Business Laptop")
        
        # Search for "laptop" should return all laptops
        response = self.client.get(f"{self.products_list_url}?search=laptop")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)
