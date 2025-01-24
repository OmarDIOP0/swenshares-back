
# Create your views here.
from datetime import timedelta
from django.forms import ValidationError
from rest_framework import viewsets, filters, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend
from django.utils import timezone
from django.db.models import Q

from shareholders.constants import KeycloakRoles

from .models import Announcement, Notification, Dividend
from .serializers import AnnouncementSerializer, NotificationSerializer, DividendSerializer
from .constants import NotificationStatus
from shareholders.views import HasKeycloakRole
from django.db.models import Sum, Avg, Count

# ViewSet pour la gestion des annonces
class AnnouncementViewSet(viewsets.ModelViewSet):
    """
    ViewSet pour la gestion des annonces d'achat/vente d'actions
    """
    queryset = Announcement.objects.all()
    serializer_class = AnnouncementSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['type', 'is_active', 'share']
    search_fields = ['description']
    ordering_fields = ['announcement_date', 'price', 'quantity']

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)

    def get_queryset(self):
        queryset = super().get_queryset()
        if self.action == 'list':
            now = timezone.now().date()
            return queryset.filter(
                Q(expiration_date__gte=now) & Q(is_active=True)
            )
        return queryset

    @action(detail=True, methods=['POST'])
    def deactivate(self, request, pk=None):
        """
        Désactive une annonce
        """
        announcement = self.get_object()
        if announcement.created_by != request.user:
            return Response(
                {"error": "You can only deactivate your own announcements"},
                status=status.HTTP_403_FORBIDDEN
            )
        
        announcement.is_active = False
        announcement.save()
        return Response({"status": "announcement deactivated"})
    
    @action(detail=False, methods=['GET'])
    def statistics(self, request):
        """
        Fournit des statistiques sur les annonces
        """
        queryset = self.get_queryset()
        stats = {
            'total_active': queryset.filter(is_active=True).count(),
            'total_expired': queryset.filter(
                expiration_date__lt=timezone.now().date()
            ).count(),
            'avg_price': queryset.aggregate(Avg('price'))['price__avg'],
            'type_distribution': queryset.values('type').annotate(
                count=Count('id')
            ),
            'monthly_created': queryset.extra(
                select={'month': "DATE_TRUNC('month', announcement_date)"}
            ).values('month').annotate(count=Count('id')).order_by('month')
        }
        return Response(stats)

    @action(detail=False, methods=['GET'])
    def my_announcements(self, request):
        """
        Retourne les annonces de l'utilisateur connecté
        """
        queryset = self.queryset.filter(created_by=request.user)
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['POST'])
    def extend_expiration(self, request, pk=None):
        """
        Prolonge la date d'expiration d'une annonce
        """
        announcement = self.get_object()
        new_date = request.data.get('new_expiration_date')
        
        if not new_date:
            return Response(
                {"error": "New expiration date is required"},
                status=status.HTTP_400_BAD_REQUEST
            )
            
        try:
            new_date = timezone.make_aware(timezone.datetime.strptime(new_date, "%Y-%m-%d")).date()
            if new_date <= timezone.now().date():
                raise ValidationError("New date must be in the future")
        except ValidationError:
            return Response(
                {"error": "Invalid date format or date in the past"},
                status=status.HTTP_400_BAD_REQUEST
            )
            
        announcement.expiration_date = new_date
        announcement.save()
        return Response(self.get_serializer(announcement).data)


# ViewSet pour la gestion des notifications
class NotificationViewSet(viewsets.ModelViewSet):
    """
    ViewSet pour la gestion des notifications système
    """
    queryset = Notification.objects.all()
    serializer_class = NotificationSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['type', 'status', 'is_read']
    search_fields = ['title', 'description']
    ordering_fields = ['date_created', 'date_sent']

    def get_queryset(self):
        return self.queryset.filter(recipient=self.request.user)

    @action(detail=True, methods=['POST'])
    def mark_as_read(self, request, pk=None):
        """
        Marque une notification comme lue
        """
        notification = self.get_object()
        notification.is_read = True
        notification.save()
        return Response({"status": "notification marked as read"})

    @action(detail=True, methods=['POST'])
    def send(self, request, pk=None):
        """
        Envoie une notification
        """
        notification = self.get_object()
        if notification.status != NotificationStatus.PENDING:
            return Response(
                {"error": "Only pending notifications can be sent"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        notification.status = NotificationStatus.SENT
        notification.date_sent = timezone.now()
        notification.save()
        return Response({"status": "notification sent"})
    
    @action(detail=False, methods=['POST'])
    def mark_all_as_read(self, request):
        """
        Marque toutes les notifications de l'utilisateur comme lues
        """
        self.get_queryset().filter(is_read=False).update(is_read=True)
        return Response({"status": "all notifications marked as read"})

    @action(detail=False, methods=['GET'])
    def unread_count(self, request):
        """
        Retourne le nombre de notifications non lues
        """
        count = self.get_queryset().filter(is_read=False).count()
        return Response({"unread_count": count})

    @action(detail=True, methods=['POST'])
    def resend(self, request, pk=None):
        """
        Renvoie une notification qui a échoué
        """
        notification = self.get_object()
        if notification.status != NotificationStatus.FAILED:
            return Response(
                {"error": "Only failed notifications can be resent"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        notification.status = NotificationStatus.PENDING
        notification.save()
        return Response({"status": "notification queued for resend"})
    

# ViewSet pour la gestion des dividendes
class DividendViewSet(viewsets.ModelViewSet):
    """
    ViewSet pour la gestion des dividendes
    """
    queryset = Dividend.objects.all()
    serializer_class = DividendSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['is_validated', 'issuing_company']
    search_fields = ['general_assembly_minutes']
    ordering_fields = ['general_assembly_date', 'payment_date', 'total_dividend_amount']

    def get_permissions(self):
        if self.action in ['validate', 'create', 'update', 'partial_update', 'destroy']:
            return [HasKeycloakRole(KeycloakRoles.EDITOR)]
        return [IsAuthenticated()]

    @action(detail=True, methods=['POST'])
    def validate(self, request, pk=None):
        """
        Valide un dividende
        """
        dividend = self.get_object()
        if dividend.is_validated:
            return Response(
                {"error": "Dividend is already validated"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        dividend.is_validated = True
        dividend.validated_by = request.user
        dividend.save()
        return Response({"status": "dividend validated"})

    @action(detail=False, methods=['GET'])
    def upcoming_payments(self, request):
        """
        Liste les paiements de dividendes à venir
        """
        now = timezone.now().date()
        upcoming = self.queryset.filter(
            payment_date__gt=now,
            is_validated=True
        ).order_by('payment_date')
        serializer = self.get_serializer(upcoming, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['GET'])
    def statistics(self, request):
        """
        Fournit des statistiques sur les dividendes
        """
        queryset = self.get_queryset()
        current_year = timezone.now().year
        stats = {
            'total_amount_this_year': queryset.filter(
                payment_date__year=current_year,
                is_validated=True
            ).aggregate(total=Sum('total_dividend_amount'))['total'],
            'avg_dividend_per_share': queryset.filter(
                is_validated=True
            ).aggregate(avg=Avg('dividend_per_share'))['avg'],
            'yearly_distribution': queryset.extra(
                select={'year': "EXTRACT(year FROM payment_date)"}
            ).values('year').annotate(
                total=Sum('total_dividend_amount')
            ).order_by('year'),
            'validation_status': queryset.values('is_validated').annotate(
                count=Count('id')
            )
        }
        return Response(stats)

    @action(detail=False, methods=['GET'])
    def payment_calendar(self, request):
        """
        Retourne un calendrier des paiements de dividendes
        """
        start_date = request.query_params.get(
            'start_date', 
            timezone.now().date().isoformat()
        )
        end_date = request.query_params.get(
            'end_date',
            (timezone.now() + timedelta(days=365)).date().isoformat()
        )
        
        try:
            payments = self.queryset.filter(
                payment_date__range=[start_date, end_date],
                is_validated=True
            ).order_by('payment_date')
            serializer = self.get_serializer(payments, many=True)
            return Response(serializer.data)
        except ValidationError:
            return Response(
                {"error": "Invalid date format"},
                status=status.HTTP_400_BAD_REQUEST
            )

    @action(detail=True, methods=['POST'])
    def cancel_validation(self, request, pk=None):
        """
        Annule la validation d'un dividende
        """
        dividend = self.get_object()
        if not dividend.is_validated:
            return Response(
                {"error": "Dividend is not validated"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Vérifie si le paiement n'a pas déjà été effectué
        if dividend.payment_date <= timezone.now().date():
            return Response(
                {"error": "Cannot cancel validation for paid dividends"},
                status=status.HTTP_400_BAD_REQUEST
            )
            
        dividend.is_validated = False
        dividend.validated_by = None
        dividend.save()
        return Response({"status": "dividend validation cancelled"})