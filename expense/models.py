from django.db import models

# Create your models here.
class Category(models.Model):
    user_id = models.CharField(max_length=255)
    name = models.CharField(max_length=50)

    class Meta:
        unique_together = ('user_id', 'name')

    def __str__(self):
        return f"{self.name} ({self.user_id})"
    
class Tag(models.Model):
    user_id = models.CharField(max_length=255)
    name = models.CharField(max_length=50)

    class Meta:
        unique_together = ('user_id', 'name')

    def __str__(self):
        return self.name

class Expense(models.Model):
    # In this setup we allow user to be null so API can be used without auth
    user_id = models.CharField(max_length=255, db_index=True)
    amount = models.DecimalField(decimal_places=2, max_digits=10)
    description = models.TextField(null=True, blank= True)
    date = models.DateField(null=True, blank=True, db_index=True)
    category = models.ForeignKey(
        Category,
        null=True,
        blank=True,
        on_delete=models.SET_NULL
    )
    tag = models.ManyToManyField(Tag, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.description or 'Expense'} - {self.amount}"

class userSetting(models.Model):
    user_id = models.CharField(max_length=255, unique=True, db_index=True)
    theme = models.CharField(max_length=20, default="dark")

    def __str__(self):
        return f"Settings for {self.user_id}"