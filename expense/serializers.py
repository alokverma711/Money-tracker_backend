from rest_framework import serializers
from .models import Category, Tag, Expense,userSetting


class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ['id', 'name']

class TagSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tag
        fields = ['id', 'name']

class ExpenseSerializer(serializers.ModelSerializer):
    # expose category name for easy display on the frontend
    category_name = serializers.CharField(
        source="category.name", read_only=True
    )

    class Meta:
        model = Expense
        fields = [
            'id',
            'amount',
            'description',
            'date',
            'category',
            'category_name',
            'tag',
            'created_at'
        ]


class UserSettingSerializer(serializers.ModelSerializer):
    class Meta:
        model = userSetting
        fields = ['theme']
