from rest_framework import serializers

from shareholders.serializers import UserSerializer
from .models import Announcement, Notification, Dividend
from django.contrib.auth.models import User

# Serializer pour les annonces
class AnnouncementSerializer(serializers.ModelSerializer):
    created_by = UserSerializer(read_only=True)
    
    class Meta:
        model = Announcement
        fields = [
            'id', 'description', 'quantity', 'price', 
            'announcement_date', 'type', 'created_by',
            'is_active', 'expiration_date', 'share'
        ]
        read_only_fields = ['announcement_date', 'created_by']

    def validate(self, data):
        if data.get('expiration_date') and data.get('announcement_date') and \
           data['expiration_date'] <= data['announcement_date']:
            raise serializers.ValidationError(
                "Expiration date must be after announcement date"
            )
        return data

# Serializer pour les notifications
class NotificationSerializer(serializers.ModelSerializer):
    recipient = serializers.PrimaryKeyRelatedField(
        queryset=User.objects.all()
    )

    class Meta:
        model = Notification
        fields = [
            'id', 'title', 'description', 'date_created',
            'date_sent', 'type', 'recipient', 'is_read', 'status'
        ]
        read_only_fields = ['date_created', 'date_sent']

    def validate(self, data):
        if data.get('date_sent') and data.get('date_created') and \
           data['date_sent'] < data['date_created']:
            raise serializers.ValidationError(
                "Sent date cannot be before created date"
            )
        return data

# Serializer pour les dividendes
class DividendSerializer(serializers.ModelSerializer):
    validated_by = UserSerializer(read_only=True)
    
    class Meta:
        model = Dividend
        fields = [
            'id', 'general_assembly_date', 'general_assembly_minutes',
            'total_dividend_amount', 'dividend_per_share', 'payment_date',
            'is_validated', 'validated_by', 'issuing_company',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['created_at', 'updated_at', 'validated_by']

    def validate(self, data):
        if data.get('payment_date') and data.get('general_assembly_date') and \
           data['payment_date'] <= data['general_assembly_date']:
            raise serializers.ValidationError(
                "Payment date must be after the general assembly date"
            )
        if data.get('dividend_per_share', 0) <= 0:
            raise serializers.ValidationError(
                "Dividend per share must be greater than zero"
            )
        if data.get('total_dividend_amount', 0) <= 0:
            raise serializers.ValidationError(
                "Total dividend amount must be greater than zero"
            )
        return data