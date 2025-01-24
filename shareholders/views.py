# views.py
from rest_framework import viewsets, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.permissions import IsAuthenticated
from django.db.models import Q, Count
from django.utils import timezone
from django.db import transaction
from django_filters.rest_framework import DjangoFilterBackend
from .constants import ShareholderStatus, KeycloakRoles

from rest_framework.permissions import BasePermission

from .models import PhysicalShareholder, LegalShareholder, Share, FileDocument
from .serializers import (
    ContactPersonSerializer,
    PhysicalShareholderSerializer, 
    LegalShareholderSerializer,
    AddressSerializer,
    ShareSerializer,
    FileDocumentSerializer
)


class HasKeycloakRole(BasePermission):
    """
    Permission personnalisée pour vérifier les rôles Keycloak
    Permet de vérifier si l'utilisateur a un rôle spécifique ou plusieurs rôles
    """
    def __init__(self, required_roles):
        if isinstance(required_roles, str):
            self.required_roles = [required_roles]
        else:
            self.required_roles = required_roles

    def has_permission(self, request, view):
        if not hasattr(request.user, 'keycloak_user'):
            return False
        return any(role in request.user.keycloak_user.roles for role in self.required_roles)

class ShareholderViewSetMixin:
    """
    Mixin pour les fonctionnalités communes aux actionnaires physiques et moraux
    Inclut la gestion des permissions, filtrage, et actions communes
    """
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    ordering_fields = ['created_at', 'effective_date', 'status']


    def get_permissions(self):
        """
        Définit les permissions en fonction de l'action
        """
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            return [HasKeycloakRole(KeycloakRoles.EDITOR)]
        elif self.action == 'examine':
            return [HasKeycloakRole(KeycloakRoles.EXAMINER)]
        elif self.action == 'approve' or self.action == 'reject':
            return [HasKeycloakRole(KeycloakRoles.APPROVER)]
        else:
            return [HasKeycloakRole([
                KeycloakRoles.ADMIN,
                KeycloakRoles.EDITOR,
                KeycloakRoles.EXAMINER,
                KeycloakRoles.APPROVER
            ])]
        
        

    # Dans le mixin ShareholderViewSetMixin
    def get_queryset(self):
        """
        Filtre les actionnaires selon les rôles de l'utilisateur et applique
        des optimisations de requête
        """
        user = self.request.user
        base_queryset = super().get_queryset().select_related(
            'created_by', 'examined_by', 'approved_by'
        ).prefetch_related('addresses')

        try:
            keycloak_user = user.keycloak_user
            filters = Q()
            if keycloak_user.has_role(KeycloakRoles.ADMIN):
                return base_queryset
            if keycloak_user.has_role(KeycloakRoles.EDITOR):
                # Modification ici pour inclure les actionnaires rejetés créés par l'utilisateur
                filters |= Q(created_by=user) | Q(status=ShareholderStatus.REJECTED, created_by=user)
                # filters |= Q(created_by=user) 
            if keycloak_user.has_role(KeycloakRoles.EXAMINER):
                filters |= Q(status=ShareholderStatus.SUBMITTED)
            if keycloak_user.has_role(KeycloakRoles.APPROVER):
                filters |= Q(status=ShareholderStatus.EXAMINED)
            return base_queryset.filter(filters)
        except AttributeError:
            return base_queryset.none()
        

    @action(detail=True, methods=['POST'])
    def submit(self, request, pk=None):
        """
        Soumet un actionnaire pour examen
        Vérifie les conditions nécessaires avant la soumission
        """
        shareholder = self.get_object()
        
        # Validation supplémentaire avant soumission
        if not self.validate_submission(shareholder):
            raise ValidationError("All required fields must be filled before submission")
        
        # Lors de la création, le statut sera directement SUBMITTED
        shareholder.status = ShareholderStatus.SUBMITTED
        shareholder.created_by = request.user
        shareholder.save()
        
        self.record_action(shareholder, "submitted", request.user)
        serializer = self.get_serializer(shareholder)
        return Response(serializer.data)

    @action(detail=True, methods=['POST'])
    def examine(self, request, pk=None):
        """
        Marque un actionnaire comme examiné
        Permet d'ajouter des commentaires d'examen
        """
        shareholder = self.get_object()
        if not request.user.keycloak_user.has_role(KeycloakRoles.EXAMINER):
            raise PermissionDenied("Only examiners can perform this action")
            
        comments = request.data.get('comments', '')
        
        if shareholder.transition_status(ShareholderStatus.EXAMINED, request.user):
            # Ajout des commentaires d'examen
            shareholder.notes = f"{shareholder.notes}\n[Examination {timezone.now()}]: {comments}".strip()
            shareholder.save()
            
            self.record_action(shareholder, "examined", request.user, comments)
            serializer = self.get_serializer(shareholder)
            return Response(serializer.data)
        return Response(
            {"error": "Status transition failed"},
            status=status.HTTP_400_BAD_REQUEST
        )
    

    @action(detail=True, methods=['POST'])
    def approve(self, request, pk=None):
        """
        Approuve un actionnaire
        Vérifie les conditions nécessaires et enregistre la décision
        """
        shareholder = self.get_object()
        if not request.user.keycloak_user.has_role(KeycloakRoles.APPROVER):
            raise PermissionDenied("Only approvers can perform this action")
            
        decision = request.data.get('decision', '')
        comments = request.data.get('comments', '')
        
        new_status = ShareholderStatus.APPROVED if decision == 'approve' else ShareholderStatus.REJECTED
        
        if shareholder.transition_status(new_status, request.user):
            shareholder.notes = f"{shareholder.notes}\n[{new_status} {timezone.now()}]: {comments}".strip()
            shareholder.save()
            
            self.record_action(shareholder, new_status.lower(), request.user, comments)
            serializer = self.get_serializer(shareholder)
            return Response(serializer.data)
        return Response(
            {"error": "Status transition failed"},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    # Rejeter un actionnaire
    @action(detail=True, methods=['POST'])
    def reject(self, request, pk=None):
        """
        Action de rejet pour un actionnaire
        Renvoie l'actionnaire à l'éditeur initial
        """
        shareholder = self.get_object()
        
        # Vérifier les permissions
        if not request.user.keycloak_user.has_role(KeycloakRoles.APPROVER):
            raise PermissionDenied("Seuls les approbateurs peuvent rejeter un actionnaire")
        
        comments = request.data.get('comments', '')
        
        # Transition vers le statut REJECTED
        if shareholder.transition_status(ShareholderStatus.REJECTED, request.user):
            # Ajouter des commentaires de rejet
            shareholder.notes = f"{shareholder.notes}\n[Rejeté le {timezone.now()}]: {comments}".strip()
            shareholder.save()
            
            # Enregistrer l'action de rejet
            self.record_action(shareholder, "rejected", request.user, comments)
            
            serializer = self.get_serializer(shareholder)
            return Response(serializer.data)
        
        return Response(
            {"error": "La transition de statut a échoué"},
            status=status.HTTP_400_BAD_REQUEST
    )

    @action(detail=False, methods=['GET'])
    def statistics(self, request):
        """
        Fournit des statistiques sur les actionnaires
        """
        queryset = self.get_queryset()
        stats = {
            'total_count': queryset.count(),
            'status_distribution': queryset.values('status').annotate(count=Count('status')),
            'monthly_created': queryset.extra(
                select={'month': "DATE_TRUNC('month', created_at)"}
            ).values('month').annotate(count=Count('id')).order_by('month')
        }
        return Response(stats)

    @action(detail=True, methods=['GET'])
    def history(self, request, pk=None):
        """
        Récupère l'historique des modifications d'un actionnaire
        """
        shareholder = self.get_object()
        return Response(shareholder.history)

    @action(detail=True, methods=['POST'])
    def add_address(self, request, pk=None):
        """
        Ajoute une nouvelle adresse à l'actionnaire
        """
        shareholder = self.get_object()
        serializer = AddressSerializer(data=request.data)
        
        if serializer.is_valid():
            with transaction.atomic():
                address = serializer.save()
                shareholder.addresses.add(address)
                if address.is_primary:
                    # Mettre à jour les autres adresses
                    shareholder.addresses.exclude(id=address.id).update(is_primary=False)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def validate_submission(self, shareholder):
        """
        Valide qu'un actionnaire peut être soumis
        """
        required_fields = ['effective_date', 'activity_sector']
        for field in required_fields:
            if not getattr(shareholder, field):
                return False
        return shareholder.addresses.filter(is_primary=True).exists()

    def record_action(self, shareholder, action, user, comments=''):
        """
        Enregistre une action dans l'historique
        """
        history_entry = {

            'action': action,
            'user': user.username,
            'timestamp': timezone.now().isoformat(),
            'comments': comments
        }
        if not isinstance(shareholder.history, list):
             # Créer un enregistrement historique
            shareholder.history.create(
                history_type='~',  # Symbole pour la mise à jour
                history_user=user,
                history_change_reason=f"{action}: {comments}"
            )
            # shareholder.history = []
        shareholder.history.append(history_entry)
        shareholder.save(update_fields=['history'])

    
    @action(detail=True, methods=['POST'])
    def update_contact_person(self, request, pk=None):
        """
        Met à jour ou crée la personne de contact de l'actionnaire
        """
        shareholder = self.get_object()
        serializer = ContactPersonSerializer(data=request.data)
        
        if serializer.is_valid():
            with transaction.atomic():
                if shareholder.contact_person:
                    for attr, value in serializer.validated_data.items():
                        setattr(shareholder.contact_person, attr, value)
                    shareholder.contact_person.save()
                else:
                    contact_person = serializer.save()
                    shareholder.contact_person = contact_person
                    shareholder.save()
                
                return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class FileDocumentMixin:
    """
    Mixin to add file management actions to ViewSets
    """
    @action(detail=True, methods=['POST'], url_path='upload-document')
    def upload_document(self, request, pk=None):
        """
        Upload a document for the specific object
        """
        serializer = FileDocumentSerializer(
            data=request.data, 
            context={'request': request, 'view': self}
        )
        
        if serializer.is_valid():
            document = serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['GET'], url_path='get-documents')
    def get_documents(self, request, pk=None):
        """
        Retrieve all documents for the specific object
        """
        instance = self.get_object()
        documents = instance.visa_document.all()
        serializer = FileDocumentSerializer(documents, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['DELETE'], url_path='delete-document/(?P<doc_id>[^/.]+)')
    def delete_document(self, request, pk=None, doc_id=None):
        """
        Delete a specific document
        """
        try:
            document = FileDocument.objects.get(
                id=doc_id, 
                content_type__model=self.queryset.model.__name__.lower(),
                object_id=pk
            )
            document.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)
        except FileDocument.DoesNotExist:
            return Response(
                {"error": "Document not found"}, 
                status=status.HTTP_404_NOT_FOUND
            )
        
  
class PhysicalShareholderViewSet(ShareholderViewSetMixin, FileDocumentMixin, viewsets.ModelViewSet):
    """
    ViewSet pour les actionnaires physiques
    """
    queryset = PhysicalShareholder.objects.all().select_related('contact_person')
    serializer_class = PhysicalShareholderSerializer
    filterset_fields = ['status', 'activity_sector', 'date_of_birth',
                       'total_shares', 'reference_number']
    search_fields = ['first_name', 'last_name', 'email', 'national_id',
                    'reference_number']

    def validate_submission(self, shareholder):
        """
        Validation spécifique pour les actionnaires physiques
        """
        basic_validation = super().validate_submission(shareholder)
        return basic_validation and all([
            shareholder.first_name,
            shareholder.last_name,
            shareholder.national_id,
            shareholder.national_id_expiration,
            shareholder.date_of_birth,
            shareholder.phone_number,
            shareholder.total_shares,
            shareholder.reference_number
        ])

class LegalShareholderViewSet(ShareholderViewSetMixin,  FileDocumentMixin, viewsets.ModelViewSet):
    """
    ViewSet pour les actionnaires moraux
    """
    # queryset = LegalShareholder.objects.all()
    queryset = LegalShareholder.objects.prefetch_related('visa_document').all().select_related('contact_person')
    serializer_class = LegalShareholderSerializer
    filterset_fields = ['status', 'activity_sector', 'is_group_member',
                       'total_shares', 'reference_number']
    search_fields = ['company_name', 'registration_number', 'tax_id',
                    'reference_number']

    def validate_submission(self, shareholder):
        """
        Validation spécifique pour les actionnaires moraux
        """
        basic_validation = super().validate_submission(shareholder)
        return basic_validation and all([
            shareholder.company_name,
            shareholder.registration_number,
            shareholder.tax_id,
            shareholder.legal_representative,
            shareholder.representative_email,
            shareholder.total_shares,
            shareholder.reference_number
        ])
    
    @action(detail=False, methods=['GET'])
    def group_statistics(self, request):
        """
        Statistiques spécifiques pour les actionnaires moraux
        """
        queryset = self.get_queryset()
        stats = {
            'total_companies': queryset.count(),
            'group_members': queryset.filter(is_group_member=True).count(),
            'average_capital_percentage': queryset.aggregate(Avg('capital_percentage')),
            'capital_distribution': queryset.values('activity_sector').annotate(
                total_capital=Sum('capital_percentage')
            )
        }
        return Response(stats)

    def create(self, request, *args, **kwargs):
        # Gestion personnalisée de la création
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        # Création de l'instance principale
        instance = serializer.save()

        # Gestion des documents uploadés
        documents_data = request.FILES.getlist('visa_document')
        for doc in documents_data:
            FileDocument.objects.create(
                file=doc,
                content_object=instance,
                uploaded_by=request.user
            )

        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)


class ShareViewSet(viewsets.ModelViewSet):
    """ 
    ViewSet pour les actions.
    """

    queryset = Share.objects.all()
    serializer_class = ShareSerializer
    permission_classes = [IsAuthenticated]
    filterset_fields = ['is_validated', 'issuing_company']
    search_fields = ['label', 'description']

    @action(detail=True, methods=['POST'])
    def validate_share(self, request, pk=None):
        """
        Custom action to validate a share.
        """
        share = self.get_object()
        share.validate()
        return Response({'status': 'Share validated', 'id': share.id, 'is_validated': share.is_validated})

    @action(detail=False, methods=['GET'])
    def unvalidated_shares(self, request):
        """
        Custom action to list all unvalidated shares.
        """
        unvalidated = self.queryset.filter(is_validated=False)
        serializer = self.get_serializer(unvalidated, many=True)
        return Response(serializer.data)