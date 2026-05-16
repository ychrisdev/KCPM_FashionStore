from django.urls import path
from rest_framework.routers import DefaultRouter
from .views import DiscountCodeViewSet, OrderItemViewSet, OrderViewSet, ReturnRequestViewSet

router = DefaultRouter()
router.register(r'orders', OrderViewSet, basename='order')
router.register(r'order-items', OrderItemViewSet, basename='orderitem')
router.register(r'discount-codes', DiscountCodeViewSet, basename='discountcode')
router.register(r'returns', ReturnRequestViewSet, basename='returnrequest')

urlpatterns = router.urls