from django.urls import path
from rest_framework.routers import DefaultRouter

from .views import ReviewViewSet, CommentViewSet

router = DefaultRouter()
router.register(r'reviews', ReviewViewSet, basename='review')
router.register(r'comments', CommentViewSet, basename='comment')

urlpatterns = router.urls
