from rest_framework.viewsets import ModelViewSet
from rest_framework import permissions
from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import action
from rest_framework.response import Response
from datetime import date

from .models import Category, Tag, Expense, userSetting
from .serializers import (
    CategorySerializer,
    TagSerializer,
    ExpenseSerializer,
    UserSettingSerializer,
)
from .ai.client import suggest_category, generate_insights
from .services import get_date_range, get_expense_summary

# ---- BASE VIEWSET ----
class BaseClerkViewSet(ModelViewSet):
    """Base ViewSet that handles Clerk user ID retrieval"""
    permission_classes = [IsAuthenticated]

    def get_clerk_id(self):
        user_obj = getattr(self.request, 'clerk_user', None)
        if user_obj:
            return user_obj.id
        return None

    def get_queryset(self):
        clerk_id = self.get_clerk_id()
        if not clerk_id:
            return self.queryset.none() # Return empty if no user
        return self.queryset.filter(user_id=clerk_id)

    def perform_create(self, serializer):
        clerk_id = self.get_clerk_id()
        if not clerk_id:
            from rest_framework.exceptions import NotAuthenticated
            raise NotAuthenticated("User identification failed.")
        serializer.save(user_id=clerk_id)


# ---- CATEGORY ----
class CategoryViewSet(BaseClerkViewSet):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer


# ---- TAG ----
class TagViewSet(BaseClerkViewSet):
    queryset = Tag.objects.all()
    serializer_class = TagSerializer


# ---- EXPENSE ----
class ExpenseViewSet(BaseClerkViewSet):
    queryset = Expense.objects.all()
    serializer_class = ExpenseSerializer

    def get_queryset(self):
        clerk_id = self.get_clerk_id()
        if not clerk_id:
            return Expense.objects.none()
            
        queryset = Expense.objects.filter(user_id=clerk_id)

        # GET parameters for filtering
        start = self.request.query_params.get("start")
        end = self.request.query_params.get("end")
        category = self.request.query_params.get("category")
        tag = self.request.query_params.get("tag")
        search = self.request.query_params.get("search")

        if start:
            queryset = queryset.filter(date__gte=start)
        if end:
            queryset = queryset.filter(date__lte=end)
        if category:
            queryset = queryset.filter(category__id=category)
        if tag:
            queryset = queryset.filter(tag__id=tag)
        if search:
            queryset = queryset.filter(description__icontains=search)

        return queryset.order_by('-date', '-created_at')

    def perform_create(self, serializer):
        clerk_id = self.get_clerk_id()
        if not clerk_id:
            from rest_framework.exceptions import NotAuthenticated
            raise NotAuthenticated("User identification failed.")
    
        # Save the expense
        expense = serializer.save(user_id=clerk_id)

        #Handle manual category assignment
        category_name = self.request.data.get('category_name')
        if category_name and category_name.strip():
            category, _ = Category.objects.get_or_create(
                user_id=clerk_id,
                name=category_name.strip()
            )
            expense.category = category
            expense.category_name = category.name
            expense.save(update_fields=["category"]) # Not strictly needed if we save again, but good for clarity of intent

        # AI Auto-categorization
        elif expense.description and not expense.category:
            try:
                suggestion = suggest_category(
                    description=expense.description,
                    amount=float(expense.amount),
                    model_name="gemini-2.5-flash"
                )

                if suggestion and isinstance(suggestion, dict):
                    cat_name = suggestion.get("category")
                    if cat_name:
                        category_obj, _ = Category.objects.get_or_create(
                            user_id=clerk_id,
                            name=cat_name.strip()
                        )
                        expense.category = category_obj
                        # expense.category_name = category_obj.name # Computed field / not on model usually, but harmless
                        expense.save(update_fields=["category"])
            except Exception as e:
                print(f"AI Auto-categorization failed: {e}")

    def perform_update(self, serializer):
        clerk_id = self.get_clerk_id()
        expense = serializer.save()
        
        # Handle manual category assignment
        category_name = self.request.data.get('category_name')
        if category_name and category_name.strip():
            category, _ = Category.objects.get_or_create(
                user_id=clerk_id,
                name=category_name.strip()
            )
            expense.category = category
            expense.save(update_fields=["category"])
        
        elif expense.description and not expense.category:
            # AI Suggestion if no manual category and no existing category
            try:
                suggestion = suggest_category(
                    description=expense.description,
                    amount=float(expense.amount),
                )
                if suggestion:
                    cat_name = suggestion.get("category")
                    if cat_name:
                        category, _ = Category.objects.get_or_create(
                            user_id=clerk_id,
                            name=cat_name.strip()
                        )
                        expense.category = category
                        expense.save(update_fields=["category"])
            except Exception as e:
                print(f"AI Update categorization failed: {e}")

    @action(detail=False, methods=["get"])
    def summary(self, request):
        clerk_id = self.get_clerk_id()
        if not clerk_id:
            return Response({"error": "No user found"}, status=401)
        
        period = request.query_params.get("period", "monthly")
        today_str = request.query_params.get("date")
        start_param = request.query_params.get("start")
        end_param = request.query_params.get("end")

        if today_str:
            try:
                ref_date = date.fromisoformat(today_str)
            except ValueError:
                return Response({"detail": "Invalid date format."}, status=400)
        else:
            ref_date = date.today()

        # Use Service to get range
        start, end, _, _ = get_date_range(clerk_id, period, ref_date, start_param, end_param)

        qs = Expense.objects.filter(user_id=clerk_id)
        if start and end:
            qs = qs.filter(date__gte=start, date__lte=end)
        
        # Use Service to get summary
        total, count, by_category = get_expense_summary(qs)

        return Response({
            "period": period, 
            "start": start.isoformat() if start else None, 
            "end": end.isoformat() if end else None,
            "total": total, 
            "count": count,
            "by_category": by_category,
        })

    @action(detail=False, methods=["get"])
    def insights(self, request):
        clerk_id = self.get_clerk_id()
        if not clerk_id:
            return Response({"error": "No user found"}, status=401)
        
        period = request.query_params.get("period", "monthly")
        today_str = request.query_params.get("date")
        start_param = request.query_params.get("start")
        end_param = request.query_params.get("end")

        if today_str:
            try:
                ref_date = date.fromisoformat(today_str)
            except ValueError:
                return Response({"detail": "Invalid date format."}, status=400)
        else:
            ref_date = date.today()

        # Use Service to get range
        start, end, prev_start, prev_end = get_date_range(clerk_id, period, ref_date, start_param, end_param)

        qs = Expense.objects.filter(user_id=clerk_id)
        
        # Current Period Data
        qs_current = qs
        if start and end:
            qs_current = qs.filter(date__gte=start, date__lte=end)
        
        total, count, by_category = get_expense_summary(qs_current)

        if total == 0:
             return Response({
                "summary": {
                    "period": period, 
                    "start": start.isoformat() if start else None, 
                    "end": end.isoformat() if end else None, 
                    "total": 0, 
                    "count": 0,
                    "by_category": []
                },
                "cards": {"total_spent": 0, "top_category": None},
                "insight": "No expenses found for this period. Start adding transactions to see AI insights!",
            })

        # Previous Period Data (for comparison)
        prev_total = 0
        if prev_start and prev_end:
            prev_qs = qs.filter(date__gte=prev_start, date__lte=prev_end)
            prev_total, _, _ = get_expense_summary(prev_qs)

        # Prepare Summary Dict for AI
        summary_data = {
            "period": period, 
            "start": start.isoformat() if start else None, 
            "end": end.isoformat() if end else None, 
            "total": total, 
            "count": count,
            "by_category": by_category
        }

        # Generate Insights
        insight_text = "Analysis currently unavailable."
        try:
            insight = generate_insights(summary_data, previous_total=prev_total)
            if isinstance(insight, dict) and "text" in insight:
                insight_text = insight["text"]
            elif isinstance(insight, str):
                insight_text = insight
        except Exception as e:
            print(f"AI Error: {e}")

        return Response({
            "summary": summary_data,
            "cards": {
                "total_spent": total, 
                "top_category": by_category[0]["name"] if by_category else None
            },
            "insight": insight_text,
        })


# ---- USER SETTINGS ----
class UserSettingsViewSet(BaseClerkViewSet):
    queryset = userSetting.objects.all()
    serializer_class = UserSettingSerializer

    def perform_create(self, serializer):
        clerk_id = self.get_clerk_id()
        if not clerk_id:
            from rest_framework.exceptions import NotAuthenticated
            raise NotAuthenticated("User identification failed.")
            
        if userSetting.objects.filter(user_id=clerk_id).exists():
            raise ValueError("Settings already exist for this user.")

        serializer.save(user_id=clerk_id)
