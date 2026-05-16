from django.urls import path
from rest_framework.routers import DefaultRouter

from .views import ContactMetaView, ContactViewSet, FeedbackViewSet, PolicyViewSet

router = DefaultRouter()
router.register(r'contacts', ContactViewSet, basename='contact')
router.register(r'feedbacks', FeedbackViewSet, basename='feedback')
router.register(r'policies', PolicyViewSet, basename='policy')

urlpatterns = [
    path('meta/', ContactMetaView.as_view(), name='contact-meta'),
] + router.urls
