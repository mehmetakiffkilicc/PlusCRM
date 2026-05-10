from rest_framework import serializers
from django.contrib.auth.models import User
from .models import DataSource, Dashboard, Widget, SystemSetting
import bcrypt


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'email', 'username']


class RegisterSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True, min_length=6)
    
    def validate(self, data):
        if User.objects.filter(email=data['email']).exists():
            raise serializers.ValidationError("Bu email zaten kullanılıyor")
        return data


class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)


class DataSourceSerializer(serializers.ModelSerializer):
    row_count = serializers.SerializerMethodField()
    
    class Meta:
        model = DataSource
        fields = ['id', 'name', 'type', 'row_count', 'column_mapping', 'uploaded_at']
    
    def get_row_count(self, obj):
        return len(obj.data) if isinstance(obj.data, list) else 0


class DataSourceDetailSerializer(serializers.ModelSerializer):
    class Meta:
        model = DataSource
        fields = ['id', 'name', 'type', 'column_mapping', 'uploaded_at']


class WidgetSerializer(serializers.ModelSerializer):
    class Meta:
        model = Widget
        fields = ['id', 'data_source', 'type', 'title', 'x_axis', 'y_axis', 'aggregation', 'filters']


class DashboardSerializer(serializers.ModelSerializer):
    widgets = WidgetSerializer(many=True, read_only=True)
    widget_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Dashboard
        fields = ['id', 'name', 'description', 'widget_count', 'created_at', 'updated_at', 'widgets']
    
    def get_widget_count(self, obj):
        return getattr(obj, 'widget_count', None) or obj.widgets.count()


class DashboardListSerializer(serializers.ModelSerializer):
    widget_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Dashboard
        fields = ['id', 'name', 'description', 'widget_count', 'created_at', 'updated_at']
    
    def get_widget_count(self, obj):
        return getattr(obj, 'widget_count', None) or obj.widgets.count()


class SystemSettingSerializer(serializers.ModelSerializer):
    class Meta:
        model = SystemSetting
        fields = ['id', 'key', 'value', 'description', 'updated_at']
