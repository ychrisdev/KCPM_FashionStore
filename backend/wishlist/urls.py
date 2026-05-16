from django.urls import path
from .views import WishlistProductIdsView, WishlistToggleView, WishlistSyncView

urlpatterns = [
    path('items/', WishlistProductIdsView.as_view(), name='wishlist-items'),
    path('toggle/', WishlistToggleView.as_view(), name='wishlist-toggle'),
    path('sync/', WishlistSyncView.as_view(), name='wishlist-sync'),
]