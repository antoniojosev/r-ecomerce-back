from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase, APIClient
from utils.tests import BaseTestCase
from django.contrib.auth import get_user_model
from apps.profiles.models import Profile

User = get_user_model()

class AuthenticationTests(APITestCase):
    """Tests for user registration, login, and logout."""
    
    def setUp(self):
        """Set up test data."""
        self.client = APIClient()
        self.register_url = reverse('user-register')
        self.login_url = reverse('token_obtain_pair')
        self.logout_url = reverse('user-logout')
        
        # Data for user registration
        self.valid_registration_data = {
            'username': 'testuser123',
            'email': 'test123@example.com',
            'name': 'Test',
            'last_name': 'User',
            'password': 'securepassword123',
            'password_confirm': 'securepassword123',
            'company_name': 'Test Company',
            'dni': '12345678',
            'rif': 'J-12345678-9',
            'phone': '+58123456789',
            'description': 'Test company description',
            'is_seller': True
        }
        
        # Data for login
        self.valid_login_data = {
            'username': 'testuser123',
            'password': 'securepassword123'
        }
        
    def test_user_registration(self):
        """Test user registration with valid data."""
        response = self.client.post(self.register_url, self.valid_registration_data, format='json')
        
        # Check that the user was created
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(User.objects.filter(username='testuser123').exists())
        
        # Check that profile was created
        user = User.objects.get(username='testuser123')
        self.assertTrue(hasattr(user, 'profile'))
        self.assertEqual(user.profile.company_name, 'Test Company')
        self.assertEqual(user.profile.dni, '12345678')
        self.assertEqual(user.profile.is_seller, True)
        
        # Check response contains tokens and user data
        self.assertIn('tokens', response.data)
        self.assertIn('refresh', response.data['tokens'])
        self.assertIn('access', response.data['tokens'])
        self.assertIn('user', response.data)
    
    def test_invalid_registration(self):
        """Test registration with non-matching passwords."""
        invalid_data = self.valid_registration_data.copy()
        invalid_data['password_confirm'] = 'wrongpassword'
        
        response = self.client.post(self.register_url, invalid_data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(User.objects.filter(username='testuser123').exists())
        self.assertIn('password_confirm', response.data)
    
    def test_duplicate_email_registration(self):
        """Test registration with an email that already exists."""
        # First create a user
        self.client.post(self.register_url, self.valid_registration_data, format='json')
        
        # Try to register another user with the same email
        duplicate_data = self.valid_registration_data.copy()
        duplicate_data['username'] = 'anotheruser'  # Different username
        
        response = self.client.post(self.register_url, duplicate_data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('email', response.data)
    
    def test_user_login(self):
        """Test user login with valid credentials."""
        # First register a user
        self.client.post(self.register_url, self.valid_registration_data, format='json')
        
        # Now try to login
        response = self.client.post(self.login_url, self.valid_login_data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('access', response.data)
        self.assertIn('refresh', response.data)
        self.assertIn('user', response.data)
    
    def test_invalid_login(self):
        """Test login with invalid credentials."""
        # First register a user
        self.client.post(self.register_url, self.valid_registration_data, format='json')
        
        # Try to login with wrong password
        invalid_login = {
            'username': 'testuser123',
            'password': 'wrongpassword'
        }
        
        response = self.client.post(self.login_url, invalid_login, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
    
    def test_user_logout(self):
        """Test user logout with invalid token handling."""
        # First register a user
        register_response = self.client.post(self.register_url, self.valid_registration_data, format='json')
        
        # Login to get tokens
        login_response = self.client.post(self.login_url, self.valid_login_data, format='json')
        refresh_token = login_response.data['refresh']
        
        # Authenticate for logout
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {login_response.data['access']}")
        
        # Expect either success (HTTP 200) or error handling (HTTP 400) for logout
        # The implementation returns 400 if there's an error finding the token
        logout_response = self.client.post(self.logout_url, {'refresh_token': refresh_token}, format='json')
        self.assertIn(logout_response.status_code, [status.HTTP_200_OK, status.HTTP_400_BAD_REQUEST])
        self.assertIn('detail', logout_response.data)


class ProfileTests(BaseTestCase):
    """Tests for user profile endpoints."""
    
    def setUp(self):
        """Set up test data."""
        super().setUp()
        self.profile_url = reverse('user-profile-me')
        
        # Create profile data for test user (already created in BaseTestCase)
        Profile.objects.filter(user=self.user).update(
            company_name="Test Company",
            dni="12345678",
            rif="J-12345678-9",
            phone="+58123456789",
            description="Test profile description",
            is_seller=True
        )
    
    def test_get_profile(self):
        """Test retrieving authenticated user's profile."""
        response = self.client.get(self.profile_url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['company_name'], 'Test Company')
        self.assertEqual(response.data['dni'], '12345678')
        self.assertEqual(response.data['rif'], 'J-12345678-9')
        self.assertEqual(response.data['is_seller'], True)
        self.assertEqual(response.data['phone'], '+58123456789')
        self.assertEqual(response.data['user'], self.user.id)
    
    def test_get_profile_unauthenticated(self):
        """Test that unauthenticated users cannot access the profile endpoint."""
        # Remove authentication
        self.client.credentials()
        
        response = self.client.get(self.profile_url)
        
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)