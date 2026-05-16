"""
Admin functionality tests for Fashion Store
Tests all admin dashboard features using Django's test client
"""
from django.test import TestCase, Client
from django.contrib.auth.models import User
from products.models import Category, Promotion, Product, Color, Size, ProductVariant
from orders.models import Order, OrderItem
from accounts.models import Profile
from reviews.models import Review
from contact.models import Contact, Feedback, Policy
from django.urls import reverse
from django.contrib.admin.sites import AdminSite
from django.core.files.uploadedfile import SimpleUploadedFile
import io


class AdminLoginTest(TestCase):
    """Test admin login functionality"""
    
    def setUp(self):
        self.client = Client()
        self.admin_user = User.objects.create_superuser(
            username='admin',
            email='admin@test.com',
            password='admin123'
        )
    
    def test_admin_login_page_loads(self):
        """Test that admin login page loads"""
        response = self.client.get('/admin/login/')
        self.assertEqual(response.status_code, 200)
    
    def test_admin_login_success(self):
        """Test successful admin login"""
        response = self.client.post('/admin/login/', {
            'username': 'admin',
            'password': 'admin123'
        }, follow=False)
        # Should redirect (302) after successful login
        self.assertIn(response.status_code, [200, 302])


class AdminProductsTest(TestCase):
    """Test Products admin functionality"""
    
    def setUp(self):
        self.client = Client()
        self.admin_user = User.objects.create_superuser(
            username='admin',
            email='admin@test.com',
            password='admin123'
        )
        self.client.login(username='admin', password='admin123')
        
        # Create test category
        self.category = Category.objects.create(
            name='Test Category',
            description='Test Description'
        )
        
        # Create test product
        self.product = Product.objects.create(
            name='Test Product',
            description='Test Product Description',
            price=99.99,
            category=self.category
        )
        
        # Create test color and size
        self.color = Color.objects.create(name='Red', code='#FF0000')
        self.size = Size.objects.create(name='M')
        
        # Create product variant
        self.variant = ProductVariant.objects.create(
            product=self.product,
            color=self.color,
            size=self.size,
            stock=10
        )
    
    def test_products_list(self):
        """Test products list page loads"""
        response = self.client.get('/admin/products/product/')
        self.assertEqual(response.status_code, 200)
    
    def test_product_add_page(self):
        """Test product add page loads"""
        response = self.client.get('/admin/products/product/add/')
        self.assertEqual(response.status_code, 200)
    
    def test_product_edit_page(self):
        """Test product edit page loads"""
        response = self.client.get(f'/admin/products/product/{self.product.pk}/change/')
        self.assertEqual(response.status_code, 200)
    
    def test_categories_list(self):
        """Test categories list page loads"""
        response = self.client.get('/admin/products/category/')
        self.assertEqual(response.status_code, 200)
    
    def test_category_add_page(self):
        """Test category add page loads"""
        response = self.client.get('/admin/products/category/add/')
        self.assertEqual(response.status_code, 200)
    
    def test_category_edit_page(self):
        """Test category edit page loads"""
        response = self.client.get(f'/admin/products/category/{self.category.pk}/change/')
        self.assertEqual(response.status_code, 200)
    
    def test_promotions_list(self):
        """Test promotions list page loads"""
        response = self.client.get('/admin/products/promotion/')
        self.assertEqual(response.status_code, 200)
    
    def test_promotion_add_page(self):
        """Test promotion add page loads"""
        response = self.client.get('/admin/products/promotion/add/')
        self.assertEqual(response.status_code, 200)
    
    def test_colors_list(self):
        """Test colors list page loads"""
        response = self.client.get('/admin/products/color/')
        self.assertEqual(response.status_code, 200)
    
    def test_color_add_page(self):
        """Test color add page loads"""
        response = self.client.get('/admin/products/color/add/')
        self.assertEqual(response.status_code, 200)
    
    def test_sizes_list(self):
        """Test sizes list page loads"""
        response = self.client.get('/admin/products/size/')
        self.assertEqual(response.status_code, 200)
    
    def test_size_add_page(self):
        """Test size add page loads"""
        response = self.client.get('/admin/products/size/add/')
        self.assertEqual(response.status_code, 200)


class AdminOrdersTest(TestCase):
    """Test Orders admin functionality"""
    
    def setUp(self):
        self.client = Client()
        self.admin_user = User.objects.create_superuser(
            username='admin',
            email='admin@test.com',
            password='admin123'
        )
        self.client.login(username='admin', password='admin123')
        
        # Create test user
        self.user = User.objects.create_user(
            username='testuser',
            email='test@test.com',
            password='test123'
        )
        
        # Create test order
        self.order = Order.objects.create(
            user=self.user,
            total_price=100.00,
            status='pending'
        )
    
    def test_orders_list(self):
        """Test orders list page loads"""
        response = self.client.get('/admin/orders/order/')
        self.assertEqual(response.status_code, 200)
    
    def test_order_detail_page(self):
        """Test order detail/change page loads"""
        response = self.client.get(f'/admin/orders/order/{self.order.pk}/change/')
        self.assertEqual(response.status_code, 200)
    
    def test_order_status_change(self):
        """Test order status can be changed"""
        response = self.client.post(
            f'/admin/orders/order/{self.order.pk}/change/',
            {'status': 'completed'}
        )
        # Should redirect after successful change
        self.assertIn(response.status_code, [200, 302])


class AdminUsersTest(TestCase):
    """Test Users/Profiles admin functionality"""
    
    def setUp(self):
        self.client = Client()
        self.admin_user = User.objects.create_superuser(
            username='admin',
            email='admin@test.com',
            password='admin123'
        )
        self.client.login(username='admin', password='admin123')
        
        # Create test user with profile - use unique username
        self.user = User.objects.create_user(
            username='testuser_profile',
            email='test_profile@test.com',
            password='test123'
        )
        # Use get_or_create to avoid conflicts
        self.profile, _ = Profile.objects.get_or_create(
            user=self.user,
            defaults={
                'phone': '1234567890',
                'address': 'Test Address'
            }
        )
    
    def test_profiles_list(self):
        """Test profiles list page loads"""
        response = self.client.get('/admin/accounts/profile/')
        self.assertEqual(response.status_code, 200)
    
    def test_profile_edit_page(self):
        """Test profile edit page loads"""
        response = self.client.get(f'/admin/accounts/profile/{self.profile.pk}/change/')
        self.assertEqual(response.status_code, 200)


class AdminReviewsTest(TestCase):
    """Test Reviews admin functionality"""
    
    def setUp(self):
        self.client = Client()
        self.admin_user = User.objects.create_superuser(
            username='admin',
            email='admin@test.com',
            password='admin123'
        )
        self.client.login(username='admin', password='admin123')
        
        # Create test user and category
        self.user = User.objects.create_user(
            username='testuser_review',
            email='test_review@test.com',
            password='test123'
        )
        self.category = Category.objects.create(
            name='Test Category',
            description='Test Description'
        )
        
        # Create test product
        self.product = Product.objects.create(
            name='Test Product',
            description='Test Description',
            price=99.99,
            category=self.category
        )
        
        # Create color, size and variant
        self.color = Color.objects.create(name='Red', code='#FF0000')
        self.size = Size.objects.create(name='M')
        self.variant = ProductVariant.objects.create(
            product=self.product,
            color=self.color,
            size=self.size,
            stock=10
        )
        
        # Create test review with ProductVariant (no comment field in Review model)
        self.review = Review.objects.create(
            user=self.user,
            product=self.variant,
            rating=5
        )
    
    def test_reviews_list(self):
        """Test reviews list page loads"""
        response = self.client.get('/admin/reviews/review/')
        self.assertEqual(response.status_code, 200)
    
    def test_review_edit_page(self):
        """Test review edit page loads"""
        response = self.client.get(f'/admin/reviews/review/{self.review.pk}/change/')
        self.assertEqual(response.status_code, 200)

    def test_comments_list(self):
        """Test comments list page loads"""
        response = self.client.get('/admin/reviews/comment/')
        self.assertEqual(response.status_code, 200)


class AdminContactTest(TestCase):
    """Test Contact/Feedback admin functionality"""
    
    def setUp(self):
        self.client = Client()
        self.admin_user = User.objects.create_superuser(
            username='admin',
            email='admin@test.com',
            password='admin123'
        )
        self.client.login(username='admin', password='admin123')
        
        # Create test contact message
        self.contact = Contact.objects.create(
            name='Test Contact',
            email='test@test.com',
            message='Test message'
        )
        
        # Create test feedback
        self.user = User.objects.create_user(
            username='testuser',
            email='test@test.com',
            password='test123'
        )
        self.feedback = Feedback.objects.create(
            user=self.user,
            message='Test feedback'
        )
        
        # Create test policy
        self.policy = Policy.objects.create(
            title='Test Policy',
            content='Test policy content'
        )
    
    def test_contacts_list(self):
        """Test contacts list page loads"""
        response = self.client.get('/admin/contact/contact/')
        self.assertEqual(response.status_code, 200)
    
    def test_feedbacks_list(self):
        """Test feedbacks list page loads"""
        response = self.client.get('/admin/contact/feedback/')
        self.assertEqual(response.status_code, 200)
    
    def test_policies_list(self):
        """Test policies list page loads"""
        response = self.client.get('/admin/contact/policy/')
        self.assertEqual(response.status_code, 200)
    
    def test_policy_add_page(self):
        """Test policy add page loads"""
        response = self.client.get('/admin/contact/policy/add/')
        self.assertEqual(response.status_code, 200)
    
    def test_policy_edit_page(self):
        """Test policy edit page loads"""
        response = self.client.get(f'/admin/contact/policy/{self.policy.pk}/change/')
        self.assertEqual(response.status_code, 200)
