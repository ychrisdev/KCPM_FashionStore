from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework import status
from .models import WishlistItem
from products.models import Product
# Import Wallet từ app wallets để lấy dữ liệu thực
from wallets.models import Wallet, WalletTransaction

class WishlistProductIdsView(APIView):
    permission_classes = [IsAuthenticated]
    def get(self, request):
        ids = list(WishlistItem.objects.filter(user=request.user).values_list('product_id', flat=True))
        return Response({"product_ids": ids})

class WishlistToggleView(APIView):
    permission_classes = [IsAuthenticated]
    def post(self, request):
        product_id = request.data.get('product_id')
        if not product_id:
            return Response({"error": "product_id is required"}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            product = Product.objects.get(id=product_id)
        except Product.DoesNotExist:
            return Response({"error": "Product not found"}, status=status.HTTP_404_NOT_FOUND)
        
        wishlist_item = WishlistItem.objects.filter(user=request.user, product_id=product_id)
        if wishlist_item.exists():
            wishlist_item.delete()
            in_wishlist = False
        else:
            WishlistItem.objects.create(user=request.user, product=product)
            in_wishlist = True
        
        # Trả về danh sách product_ids hiện tại
        product_ids = list(WishlistItem.objects.filter(user=request.user).values_list('product_id', flat=True))
        return Response({
            "in_wishlist": in_wishlist,
            "product_ids": product_ids
        }, status=status.HTTP_200_OK)

class WishlistSyncView(APIView):
    permission_classes = [IsAuthenticated]
    def post(self, request):
        incoming_ids = request.data.get('product_ids', [])
        if not isinstance(incoming_ids, list):
            return Response({"error": "product_ids must be a list"}, status=status.HTTP_400_BAD_REQUEST)
        
        # Xóa tất cả wishlist hiện tại
        WishlistItem.objects.filter(user=request.user).delete()
        
        # Thêm các sản phẩm mới (chỉ những sản phẩm tồn tại)
        valid_products = Product.objects.filter(id__in=incoming_ids)
        wishlist_items = [WishlistItem(user=request.user, product=product) for product in valid_products]
        WishlistItem.objects.bulk_create(wishlist_items, ignore_conflicts=True)
        
        # Trả về danh sách product_ids sau khi sync
        product_ids = list(WishlistItem.objects.filter(user=request.user).values_list('product_id', flat=True))
        return Response({"product_ids": product_ids})