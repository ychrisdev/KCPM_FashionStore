from django.urls import path
from rest_framework.routers import DefaultRouter

from .views import CategoryViewSet, PromotionViewSet, ProductViewSet, ColorViewSet, SizeViewSet, ProductVariantViewSet, ProductImageViewSet

router = DefaultRouter()
router.register(r'categories', CategoryViewSet, basename='category')
router.register(r'promotions', PromotionViewSet, basename='promotion')
router.register(r'colors', ColorViewSet, basename='color')
router.register(r'sizes', SizeViewSet, basename='size')
router.register(r'variants', ProductVariantViewSet, basename='productvariant')
router.register(r'images', ProductImageViewSet, basename='productimage')
# Register products at root so /api/products/ returns product list
router.register(r'', ProductViewSet, basename='product')

urlpatterns = router.urls
