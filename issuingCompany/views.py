from django.shortcuts import render
from yaml import serialize
from .serializers import (
    IssuingCompanySerializer,
    AddressSerializer,
    SocialActSerializer,
    ActeSocialAugmentationSerializer,
    ActeSocialReductionSerializer,
    TransactionSerializer,
    SocialeSerializer)
from .models import IssuingCompany, SocialAct, Transaction,ActeSocialReduction,ActeSocialAugmentation,Sociale
from rest_framework import viewsets,status
from rest_framework.response import Response
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.exceptions import PermissionDenied
from django.db import transaction
from shareholders.constants import KeycloakRoles
from shareholders.views import HasKeycloakRole
from django.utils import timezone
import logging
from django.db.models import Q
from .constants import IssuingCompanyStatus,TransactionStatus,SocialActType
from simple_history.models import HistoricalRecords


#gerer les entites de la societe emettrice
logger = logging.getLogger(__name__)
class IssuingCompanyViewSet(viewsets.ModelViewSet):
    queryset = IssuingCompany.objects.select_related(
        'head_office_address','created_by','examined_by','approved_by'
    ).all()
    serializer_class = IssuingCompanySerializer
    permission_classes = [IsAuthenticated]


    #Gerer les permissions
    def get_permissions(self):
        if self.action in ['create','update','partial_update','destroy']:
            return [HasKeycloakRole(KeycloakRoles.EDITOR)]
        elif self.action in ['examine','approve']:
            return [HasKeycloakRole([KeycloakRoles.EXAMINER,KeycloakRoles.APPROVER])]
        return [HasKeycloakRole([KeycloakRoles.ADMIN,KeycloakRoles.EDITOR])]
    
    # Redéfinir get_queryset pour filtrer en fonction de l'utilisateur ou d'autres critères


    def get_queryset(self):
        """
        Filtre les sociétés émettrices selon les rôles de l'utilisateur et applique
        des optimisations de requête.
        """
        user = self.request.user
        logger.info(f"Fetching IssuingCompany queryset for user: {user.username}")

        # Optimisations des requêtes pour les relations
        base_queryset = super().get_queryset().select_related(
            'created_by', 'examined_by', 'approved_by', 'head_office_address'
        )

        try:
            keycloak_user = user.keycloak_user
            filters = Q()

            # Rôle ADMIN : accès total
            if keycloak_user.has_role(KeycloakRoles.ADMIN):
                logger.debug("Admin role detected; returning full queryset.")
                return base_queryset

            # Rôle EDITOR : sociétés créées par l'utilisateur ou en brouillon
            if keycloak_user.has_role(KeycloakRoles.EDITOR):
                logger.debug("Applying filters for EDITOR role.")
                filters |= Q(created_by=user) | Q(status='SUBMITTED')

            # Rôle EXAMINER : sociétés soumises
            if keycloak_user.has_role(KeycloakRoles.EXAMINER):
                logger.debug("Applying filters for EXAMINER role.")
                filters |= Q(status='SUBMITTED')

            # Rôle APPROVER : sociétés examinées
            if keycloak_user.has_role(KeycloakRoles.APPROVER):
                logger.debug("Applying filters for APPROVER role.")
                filters |= Q(status='EXAMINED')

            # Application des filtres
            return base_queryset.filter(filters)

        except AttributeError as e:
            logger.error(f"Keycloak user attribute missing for user {user.username}: {str(e)}")
            return base_queryset.none()
        except Exception as e:
            logger.error(f"Unexpected error in IssuingCompany get_queryset: {str(e)}")
            raise serialize.ValidationError("Error")
    
     # Méthode pour valider et gérer les erreurs 400
    def verify_request_data(self, data, required_fields):
        missing_fields = [field for field in required_fields if field not in data]
        if missing_fields:
            return Response(
                {"error": f"Missing fields: {', '.join(missing_fields)}"},
                status=status.HTTP_400_BAD_REQUEST
            )
        return None
    
    # Marquer une société émettrice comme soumise
    @action(detail=True, methods=['POST'])
    def submit(self, request, pk=None):
        company = self.get_object()
        notes = request.data.get('notes', '')
        error_response = self.verify_request_data(request.data, ['notes'])
        if error_response:
            return error_response
        if company.status != 'SUBMITTED':
            return Response(
                {"error": "Only SUBMITTED companies can be submitted"},
                status=status.HTTP_400_BAD_REQUEST
            )
        with transaction.atomic():
            company.status = 'SUBMITTED'
            company.notes = f"{company.notes}\n[Submission {timezone.now()}]: {notes}".strip()
            company.save()
        serializer = self.get_serializer(company)
        return Response(serializer.data, status=status.HTTP_200_OK)

    #Marquer une société émettrice comme examinée.
    @action(detail=True, methods=['POST'])
    def examine(self, request, pk=None):
        company = self.get_object()
        if not request.user.keycloak_user.has_role(KeycloakRoles.EXAMINER):
            raise PermissionDenied("Only examiners can perform this action")
        notes = request.data.get('notes', '')

        if company.transition_status(IssuingCompanyStatus.EXAMINED,request.user):
            with transaction.atomic():
                company.status = 'EXAMINED'
                company.examined_by = request.user
                company.notes = f"{company.notes}\n[Examination {timezone.now()}]: {notes}".strip()
                company.save()
            serializer = self.get_serializer(company)
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(
            {"error": "Status transition failed"},
            status=status.HTTP_400_BAD_REQUEST
        )

    
    #Marquer une société émettrice comme approuvée.
    @action(detail=True, methods=['POST'])
    def approve(self, request, pk=None):
        company = self.get_object()
        if not request.user.keycloak_user.has_role(KeycloakRoles.APPROVER):
            raise PermissionDenied("Only approvers can perform this action")
        decision = request.data.get('decision', '').lower()
        notes = request.data.get('notes', '')
        if decision not in ['approve', 'reject']:
            return Response(
                {"error": "Decision must be 'approve' or 'reject'"},
                status=status.HTTP_400_BAD_REQUEST
            )
        new_status = IssuingCompanyStatus.APPROVED if decision == 'approve' else IssuingCompanyStatus.REJECTED
        if company.transition_status(new_status,request.user):
            with transaction.atomic():
                company.status = new_status
                company.approved_by = request.user
                company.notes = f"{company.notes}\n[{new_status} {timezone.now()}]: {notes}".strip()
                company.save()
            serializer = self.get_serializer(company)
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(
            {"error": "Status transition failed"},
            status=status.HTTP_400_BAD_REQUEST
        )
    @action(detail=True, methods=['GET'])
    def history(self, request, pk=None):
        """
        Récupère l'historique des modifications de la societe
        """
        company = self.get_object()
        return Response(company.history)

class SocialActViewSet(viewsets.ModelViewSet):
    """
    ViewSet pour gérer les actes sociaux.
    """
    queryset = SocialAct.objects.select_related(
        'issuing_company', 'created_by', 'examined_by', 'approved_by'
    ).all()
    serializer_class = SocialActSerializer
    permission_classes = [IsAuthenticated]

    # Gérer les permissions
    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            return [HasKeycloakRole(KeycloakRoles.EDITOR)]
        elif self.action in ['approve', 'calculate']:
            return [HasKeycloakRole([KeycloakRoles.APPROVER, KeycloakRoles.EXAMINER])]
        return [HasKeycloakRole([KeycloakRoles.ADMIN, KeycloakRoles.EDITOR])]
    
        # Méthode pour valider et gérer les erreurs 400
    def verify_request_data(self, data, required_fields):
        missing_fields = [field for field in required_fields if field not in data]
        if missing_fields:
            return Response(
                {"error": f"Missing fields: {', '.join(missing_fields)}"},
                status=status.HTTP_400_BAD_REQUEST
            )
        return None

    # Calculer le montant total associé à l'acte social
    # @action(detail=True, methods=['POST'])
    # def calculate(self, request, pk=None):
    #     """
    #     Calcule le montant total associé à l'acte social.
    #     """
    #     social_act = self.get_object()
    #     try:
    #         social_act.calculate_amount()
    #         social_act.save()
    #     except Exception as e:
    #         return Response(
    #             {"error": f"Error during calculation: {str(e)}"},
    #             status=status.HTTP_400_BAD_REQUEST
    #         )
    #     serializer = self.get_serializer(social_act)
    #     return Response(serializer.data, status=status.HTTP_200_OK)

 # Approuver ou rejeter un acte social
    @action(detail=True, methods=['POST'])
    def approve(self, request, pk=None):
        """
        Approuve ou rejette un acte social.
        """
        if not request.user.keycloak_user.has_role(KeycloakRoles.APPROVER):
            raise PermissionDenied("Only approvers can perform this action")
        error_response = self.verify_request_data(request.data, ['decision', 'notes'])
        if error_response:
            return error_response
        social_act = self.get_object()
        decision = request.data.get('decision', 'approve').lower()
        notes = request.data.get('notes', '')

        if decision not in ['approve', 'reject']:
            return Response(
                {"error": "Decision must be 'approve' or 'reject'"},
                status=status.HTTP_400_BAD_REQUEST
            )
        new_status = SocialActType.APPROVED if decision == 'approve' else SocialActType.REJECTED
        if social_act.transition_status(new_status,request.user):
            with transaction.atomic():
                social_act.status = 'APPROVED' if decision == 'approve' else 'REJECTED'
                social_act.approved_by = request.user
                social_act.notes = f"{social_act.notes}\n[{social_act.status} {timezone.now()}]: {notes}".strip()
                social_act.save()
            serializer = self.get_serializer(social_act)
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(
            {"error": "Status transition failed"},
            status=status.HTTP_400_BAD_REQUEST
        )
    @action(detail=True, methods=['POST'])
    def examine(self, request, pk=None):
        social_act = self.get_object()
        if not request.user.keycloak_user.has_role(KeycloakRoles.EXAMINER):
            raise PermissionDenied("Only examiners can perform this action")
        notes = request.data.get('notes', '')

        if social_act.transition_status(SocialActType.EXAMINED,request.user):
            with transaction.atomic():
                social_act.status = 'EXAMINED'
                social_act.examined_by = request.user
                social_act.notes = f"{social_act.notes}\n[Examination {timezone.now()}]: {notes}".strip()
                social_act.save()
            serializer = self.get_serializer(social_act)
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(
            {"error": "Status transition failed"},
            status=status.HTTP_400_BAD_REQUEST
        )

    # Historique des modifications d'un acte social
    @action(detail=True, methods=['GET'])
    def history(self, request, pk=None):
        """
        Récupère l'historique des modifications d'un acte social.
        """
        social_act = self.get_object()
        history_data = social_act.history  # Vous devez implémenter un système d'historique, ex: django-simple-history
        return Response(history_data, status=status.HTTP_200_OK)

    # Soumettre un acte social pour approbation
    @action(detail=True, methods=['POST'])
    def submit(self, request, pk=None):
        """
        Soumet un acte social pour approbation.
        """
        social_act = self.get_object()
        notes = request.data.get('notes', '')

        error_response = self.verify_request_data(request.data, ['notes'])
        if error_response:
            return error_response
        if social_act.status != 'SUBMITTED':
            return Response(
                {"error": "Only SUBMITTED social act can be submitted"},
                status=status.HTTP_400_BAD_REQUEST
            )
        with transaction.atomic():
            social_act.status = 'SUBMITTED'
            social_act.notes = f"{social_act.notes}\n[Submission {timezone.now()}]: {notes}".strip()
            social_act.save()

        serializer = self.get_serializer(social_act)
        return Response(serializer.data, status=status.HTTP_200_OK)
    

class ActeSocialAugmentationViewSet(viewsets.ModelViewSet):
    """
    ViewSet pour gérer les actes sociaux augmentés.
    """
    queryset = ActeSocialAugmentation.objects.select_related('issuing_company').all()
    serializer_class = ActeSocialAugmentationSerializer
    permission_classes = [IsAuthenticated]

    # Gérer les permissions
    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            return [HasKeycloakRole(KeycloakRoles.EDITOR)]
        elif self.action == 'approve':
            return [HasKeycloakRole([KeycloakRoles.APPROVER])]
        return [HasKeycloakRole([KeycloakRoles.ADMIN, KeycloakRoles.EDITOR])]
    
    @action(detail=True,methods=['POST'])
    def approve(self, request, pk=None):
        """
        Approuver un acte social augmenté.
        """
        instance = self.get_object()
        with transaction.atomic():
            instance.status = 'APPROVED'
            instance.save()
        serializer = self.get_serializer(instance)
        return Response(serializer.data, status=status.HTTP_200_OK)
    

class ActeSocialReductionViewSet(viewsets.ModelViewSet):
    """
    ViewSet pour gérer les réductions de capital.
    """
    queryset = ActeSocialReduction.objects.select_related('issuing_company').all()
    serializer_class = ActeSocialReductionSerializer
    permission_classes = [IsAuthenticated]

    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            return [HasKeycloakRole(KeycloakRoles.EDITOR)]
        elif self.action in ['approve']:
            return [HasKeycloakRole([KeycloakRoles.APPROVER])]
        return [HasKeycloakRole([KeycloakRoles.ADMIN, KeycloakRoles.EDITOR])]

    @action(detail=True, methods=['POST'])
    def approve(self, request, pk=None):
        """
        Approuve une réduction de capital.
        """
        instance = self.get_object()
        with transaction.atomic():
            instance.status = 'APPROVED'
            instance.save()
        serializer = self.get_serializer(instance)
        return Response(serializer.data, status=status.HTTP_200_OK)
    

class SocialeViewSet(viewsets.ModelViewSet):
    """
    ViewSet pour gérer les informations sociales.
    """
    queryset = Sociale.objects.select_related('issuing_company').all()
    serializer_class = SocialeSerializer
    permission_classes = [IsAuthenticated]

    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            return [HasKeycloakRole(KeycloakRoles.EDITOR)]
        return [HasKeycloakRole([KeycloakRoles.ADMIN, KeycloakRoles.EDITOR])]

    @action(detail=True, methods=['GET'])
    def history(self, request, pk=None):
        """
        Récupère l'historique des modifications.
        """
        instance = self.get_object()
        history_data = instance.history
        return Response(history_data, status=status.HTTP_200_OK)
    

#La view de la transaction
class TransactionViewSet(viewsets.ModelViewSet):
    """
    ViewSet pour gérer les transactions.
    """
    queryset = Transaction.objects.select_related(
            'issuing_company', 'validated_by', 'announcement'
            ).prefetch_related('seller_content_type', 'buyer_content_type')

    serializer_class = TransactionSerializer
    permission_classes = [IsAuthenticated]

    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            return [HasKeycloakRole(KeycloakRoles.EDITOR)]
        return [HasKeycloakRole([KeycloakRoles.ADMIN, KeycloakRoles.EDITOR])]
    
    #Fonction pour gerer la saisi les champs requis
    def verify_request_data(self, data, required_fields):
        missing_fields = [field for field in required_fields if field not in data]
        if missing_fields:
            return Response(
                {"error": f"Missing fields: {', '.join(missing_fields)}"},
                status=status.HTTP_400_BAD_REQUEST
            )
        return None
    
    @action(detail=True, methods=['POST'])
    def calculate(self, request, pk=None):
        """
        Calcule le montant total de la transaction.
        """
        instance = self.get_object()
        with transaction.atomic():
            instance.calculate_total_amount()
            instance.save()
        serializer = self.get_serializer(instance)
        return Response(serializer.data, status=status.HTTP_200_OK)
    

    #Submit Transaction
    @action(detail=True,methods=['POST'])
    def submit(self, request, pk=None):
        transactions = self.get_object()
        notes = request.data.get('notes', '')
        error_message = self.verify_request_data(request.data,['notes'])
        if error_message:
            return error_message
        with transaction.atomic():
            transactions.status = 'SUBMITTED'
            transactions.notes = f"{transactions.notes}\n[Submission {timezone.now()}]: {notes}".strip()
            transactions.save()
        serializer = self.get_serializer(transactions)
        return Response(serializer.data, status=status.HTTP_200_OK)
    
    #Valider la transaction
    @action(detail=True,methods=['POST'])
    def validate(self, request, pk=None):
        """Valider la transaction"""
        transaction_instance = self.get_object()
        notes = request.data.get('notes','')
        error_message = self.verify_request_data(request.data,['notes'])
        if error_message:
            return error_message
        if transaction_instance.status != 'PENDING':
            return Response(
                {"error": "Only transactions with 'PENDING' status can be validated."},
                status = status.HTTP_400_BAD_REQUEST
            )
        #Verification de la conformite
        if not transaction_instance.seller or not transaction_instance.buyer:
            return Response(
                {"error": "Seller and buyer must be set."},
                status = status.HTTP_400_BAD_REQUEST
            )
        
        if transaction_instance.total_amount <= 0:
            return Response(
                {"error": "Total amount must be greater than zero."},
                status = status.HTTP_400_BAD_REQUEST
            )
        with transaction.atomic():
            transaction_instance.status = 'VALIDATED'
            transaction_instance.notes = f"{transaction_instance.notes}\n[Validation {timezone.now()}]: {notes}".strip()
            transaction_instance.save()

        serializer = self.get_serializer(transaction_instance)
        return Response(serializer.data, status=status.HTTP_200_OK)






