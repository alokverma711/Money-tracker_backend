from django.contrib import admin
from expense.models import Category,Tag,Expense,userSetting

# Register your models here.
admin.site.register(Category)
admin.site.register(Tag)
admin.site.register(Expense)
admin.site.register(userSetting)