from django.db import models
from django.contrib.auth.models import User
import json

class DataSource(models.Model):
    TYPE_CHOICES = [
        ('csv', 'CSV'),
        ('json', 'JSON'),
        ('database', 'Database'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, db_index=True)
    name = models.CharField(max_length=255, db_index=True)
    type = models.CharField(max_length=20, choices=TYPE_CHOICES, db_index=True)
    data = models.JSONField(default=list)
    column_mapping = models.JSONField(default=dict, blank=True, null=True)
    connection_info = models.JSONField(default=dict, blank=True, null=True)
    uploaded_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ['-uploaded_at']
        indexes = [
            models.Index(fields=['user', 'uploaded_at'], name='datasrc_user_upload_idx'),
            models.Index(fields=['user', 'type'], name='datasrc_user_type_idx'),
        ]

    def __str__(self):
        return self.name


class Dashboard(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, db_index=True)
    name = models.CharField(max_length=255, db_index=True)
    description = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True, db_index=True)

    class Meta:
        ordering = ['-updated_at']
        indexes = [
            models.Index(fields=['user', 'updated_at'], name='dashboard_user_updated_idx'),
        ]

    def __str__(self):
        return self.name


class Widget(models.Model):
    TYPE_CHOICES = [
        ('line', 'Çizgi Grafik'),
        ('bar', 'Çubuk Grafik'),
        ('pie', 'Pasta Grafik'),
        ('scatter', 'Scatter'),
        ('heatmap', 'Heatmap'),
    ]
    
    AGGREGATION_CHOICES = [
        ('sum', 'Toplam'),
        ('average', 'Ortalama'),
        ('count', 'Sayı'),
        ('min', 'Minimum'),
        ('max', 'Maksimum'),
    ]
    
    dashboard = models.ForeignKey(Dashboard, on_delete=models.CASCADE, related_name='widgets', db_index=True)
    data_source = models.ForeignKey(DataSource, on_delete=models.CASCADE, db_index=True)
    type = models.CharField(max_length=20, choices=TYPE_CHOICES, db_index=True)
    title = models.CharField(max_length=255)
    x_axis = models.CharField(max_length=255, blank=True, null=True)
    y_axis = models.CharField(max_length=255, blank=True, null=True)
    aggregation = models.CharField(max_length=20, choices=AGGREGATION_CHOICES, blank=True, null=True)
    filters = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ['created_at']
        indexes = [
            models.Index(fields=['dashboard', 'created_at'], name='widget_dash_created_idx'),
        ]
    
    def __str__(self):
        return self.title


class SystemSetting(models.Model):
    key = models.CharField(max_length=100, unique=True, db_index=True)
    value = models.JSONField(default=dict)
    description = models.TextField(blank=True, null=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Sistem Ayarı"
        verbose_name_plural = "Sistem Ayarları"

    def __str__(self):
        return self.key


class AISession(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, db_index=True)
    title = models.CharField(max_length=255, default='Yeni Sohbet')
    model_name = models.CharField(max_length=100, default='gemini-2.0-flash')
    total_tokens = models.IntegerField(default=0)
    total_cost = models.DecimalField(max_digits=10, decimal_places=6, default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

class AIMessage(models.Model):
    ROLE_CHOICES = [('user', 'User'), ('assistant', 'Assistant')]
    session = models.ForeignKey(AISession, on_delete=models.CASCADE, related_name='messages')
    role = models.CharField(max_length=20, choices=ROLE_CHOICES)
    content = models.TextField()
    tool_calls = models.JSONField(default=list, blank=True)
    input_tokens = models.IntegerField(default=0)
    output_tokens = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

class AIAuditLog(models.Model):
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    session = models.ForeignKey(AISession, on_delete=models.SET_NULL, null=True, blank=True)
    tool_called = models.CharField(max_length=100, blank=True)
    prompt_hash = models.CharField(max_length=64, blank=True)
    response_hash = models.CharField(max_length=64, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)

class AINotification(models.Model):
    TYPE_CHOICES = [
        ('info', 'Bilgi'),
        ('warning', 'Uyarı'),
        ('success', 'Başarılı'),
        ('critical', 'Kritik'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, db_index=True)
    title = models.CharField(max_length=255)
    message = models.TextField()
    type = models.CharField(max_length=20, choices=TYPE_CHOICES, default='info')
    is_read = models.BooleanField(default=False, db_index=True)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', 'is_read', 'created_at'], name='notif_user_read_idx'),
        ]

class ScheduledCampaign(models.Model):
    CHANNEL_CHOICES = [
        ('sms', 'SMS'),
        ('email', 'E-posta'),
        ('push', 'Anlık Bildirim'),
    ]
    STATUS_CHOICES = [
        ('pending', 'Beklemede'),
        ('completed', 'Tamamlandı'),
        ('cancelled', 'İptal Edildi'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, db_index=True)
    title = models.CharField(max_length=255)
    description = models.TextField()
    segment = models.CharField(max_length=255)
    channel = models.CharField(max_length=20, choices=CHANNEL_CHOICES, default='email')
    scheduled_at = models.DateTimeField(db_index=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending', db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['scheduled_at']
        indexes = [
            models.Index(fields=['user', 'status', 'scheduled_at'], name='sched_camp_user_status_idx'),
        ]

class AIDashboard(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, db_index=True)
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    config = models.JSONField(help_text="Dashboard components and their settings")
    is_favorite = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', 'created_at'], name='aidash_user_created_idx'),
        ]

    def __str__(self):
        return f"{self.name} ({self.user.username})"
