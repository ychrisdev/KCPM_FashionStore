from rest_framework import permissions, viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.utils import timezone
from django.db.models import Q

from core.permissions import IsAdminOrStaff, is_admin, is_staff
from orders.models import Order, OrderItem
from products.serializers import normalize_size_name
from .models import Review, Comment
from .serializers import ReviewSerializer, CommentSerializer
from django.db.models import Avg
from products.models import ProductVariant, Product

def _recalc_product_rating(product_variant: ProductVariant) -> None:
    product = product_variant.product
    avg = (
        Review.objects
        .filter(product__product=product, is_visible=True)
        .aggregate(avg=Avg("rating"))["avg"]
    )
    # ✅ Luôn lưu vào product.rating — đây là nguồn duy nhất
    product.rating = round(avg, 2) if avg is not None else 0
    product.save(update_fields=["rating"])
    
class ReviewViewSet(viewsets.ModelViewSet):
    queryset = Review.objects.all()
    serializer_class = ReviewSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]
    filterset_fields = ["product", "rating", "feedback_type"]

    def get_permissions(self):
        if self.action in ("update", "partial_update"):
            return [permissions.IsAuthenticated(), IsAdminOrStaff()]
        return [permissions.IsAuthenticatedOrReadOnly()]

    def get_queryset(self):
        qs = (
            Review.objects.select_related(
                "user", "user__profile", "product", "product__product", "product__color", "product__size"
            )
            .all()
            .order_by("-created_at")
        )
        user = self.request.user
        if user.is_authenticated and is_staff(user):
            return qs
        if user.is_authenticated:
            return qs.filter(Q(is_visible=True) | Q(user=user))
        return qs.filter(is_visible=True)

    def perform_create(self, serializer):
        review = serializer.save(user=self.request.user)
        _recalc_product_rating(review.product)
        
    def perform_update(self, serializer):
        review = serializer.save()
        _recalc_product_rating(review.product)

    def destroy(self, request, *args, **kwargs):
        """Allow admin to delete any review, others can only delete their own"""
        instance = self.get_object()
        if is_admin(request.user) or instance.user == request.user:
            return super().destroy(request, *args, **kwargs)
        return Response(
            {"detail": "You do not have permission to delete this review."},
            status=status.HTTP_403_FORBIDDEN
        )

    @action(detail=False, methods=["get"], url_path="my_reviews")
    def my_reviews(self, request):
        """Get reviews by current user"""
        if not request.user.is_authenticated:
            return Response({"detail": "Authentication required"}, status=status.HTTP_401_UNAUTHORIZED)
        reviews = Review.objects.filter(user=request.user).select_related(
            "user__profile", "product", "product__product", "product__color", "product__size"
        ).order_by("-created_at")
        serializer = self.get_serializer(reviews, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=["get"], url_path="purchasable")
    def purchasable(self, request):
        """Get products that the current user has purchased and can review"""
        if not request.user.is_authenticated:
            return Response({"detail": "Authentication required"}, status=status.HTTP_401_UNAUTHORIZED)

        # Get completed orders
        completed_order_items = OrderItem.objects.filter(
            order__user=request.user,
            order__status='completed'
        ).select_related(
            "product", "product__product", "product__color", "product__size"
        )

        # Get items already reviewed
        reviewed_variant_ids = Review.objects.filter(user=request.user).values_list('product_id', flat=True)

        purchasable_items = []
        for item in completed_order_items:
            days_since = (timezone.now() - item.order.created_at).days
            if days_since <= 14 and item.product_id not in reviewed_variant_ids:
                purchasable_items.append({
                    'order_id': item.order.id,
                    'variant_id': item.product.id,
                    'product_name': item.product.product.name,
                    'variant_info': {
                        'color': {'id': item.product.color.id, 'name': item.product.color.name, 'code': item.product.color.code},
                        'size': {'id': item.product.size.id, 'name': normalize_size_name(item.product.size.name)}
                    },
                    'price': str(item.price),
                    'purchased_at': item.order.created_at.isoformat(),
                    'days_remaining': 14 - days_since
                })

        return Response(purchasable_items)

    @action(detail=False, methods=["get"], url_path="by_product/(?P<product_id>[^/.]+)")
    def by_product(self, request, product_id=None):
        reviews = (
            self.get_queryset()
            .filter(product__product_id=product_id)
            .select_related("user", "user__profile", "product", "product__color", "product__size")
        )
        
        # Filter by rating if provided
        rating = request.query_params.get("rating")
        if rating and rating.isdigit():
            reviews = reviews.filter(rating=int(rating))
        
        # Pagination
        page = int(request.query_params.get("page", 1))
        page_size = int(request.query_params.get("page_size", 4))
        start = (page - 1) * page_size
        end = start + page_size
        
        total_count = reviews.count()
        total_pages = (total_count + page_size - 1) // page_size
        
        paginated_reviews = reviews[start:end]
        serializer = self.get_serializer(paginated_reviews, many=True)
        
        return Response({
            "results": serializer.data,
            "count": total_count,
            "total_pages": total_pages,
            "current_page": page,
            "page_size": page_size,
        })


class CommentViewSet(viewsets.ModelViewSet):
    queryset = Comment.objects.all()
    serializer_class = CommentSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]
    filterset_fields = ["product"]

    def get_queryset(self):
        return Comment.objects.select_related("user", "product").all().order_by("-created_at")

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    def destroy(self, request, *args, **kwargs):
        """Allow admin to delete any comment, others can only delete their own"""
        instance = self.get_object()
        if is_admin(request.user) or instance.user == request.user:
            return super().destroy(request, *args, **kwargs)
        return Response(
            {"detail": "You do not have permission to delete this comment."},
            status=status.HTTP_403_FORBIDDEN
        )
