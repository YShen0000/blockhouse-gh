from django.contrib.auth.models import User
from django.db import models
from django.utils import timezone

class Uploads(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='csv_files')
    file_name = models.CharField(max_length=255)
    upload_date = models.DateTimeField(auto_now_add=True)
    file_size = models.IntegerField()
    file_path = models.CharField(max_length=500)  # Path to the file in blob storage

    def __str__(self):
        return self.file_name


class UploadBlockhouse(models.Model):
    # user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='csv_files')
    user_email = models.CharField(max_length=255)
    account_type = models.CharField(max_length=255)
    file_name = models.CharField(max_length=255)
    upload_date = models.DateTimeField(auto_now_add=True)
    file_size = models.IntegerField()
    file_path = models.CharField(max_length=500)  # Path to the file in blob storage
    platform = models.CharField(max_length=255, default="unknown")

    def __str__(self):
        return self.file_name


class UploadHoodWinked(models.Model):
    # user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='csv_files')
    user_email = models.CharField(max_length=255)
    file_name = models.CharField(max_length=255)
    upload_date = models.DateTimeField(auto_now_add=True)
    file_size = models.IntegerField()
    file_path = models.CharField(max_length=500)  # Path to the file in blob storage
    platform = models.CharField(max_length=255)

    def __str__(self):
        return self.file_name

class Trade(models.Model):
    file = models.ForeignKey(Uploads, on_delete=models.CASCADE, related_name='contents', null=True)
    cusip = models.CharField(max_length=10)
    trade_timestamp = models.DateTimeField(default=timezone.now)
    trade_size = models.IntegerField()
    face_value = models.IntegerField()
    asset_inventory = models.IntegerField()
    fill = models.IntegerField()
    execution_time = models.IntegerField()
    trade_price = models.FloatField()
    trade_direction = models.CharField(max_length=4)
    counterparty = models.CharField(max_length=50)
    trader = models.CharField(max_length=50)

    def __str__(self):
        return f"Trade {self.cusip} on {self.trade_timestamp}"

class Market_Prices(models.Model):
    cusip = models.CharField(max_length=10)
    trade_timestamp = models.DateTimeField(default=timezone.now)
    trade_price = models.FloatField()

    def __str__(self):
        return f"Market Price {self.cusip} on {self.trade_timestamp}"