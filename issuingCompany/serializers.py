from rest_framework import serializers
from .models import IssuingCompany,SocialAct
from shareholders.serializers import UserSerializer,AddressSerializer
from shareholders.models import Address 
from .models import ActeSocialAugmentation,ActeSocialReduction,Sociale,Transaction


class IssuingCompanySerializer(serializers.ModelSerializer):
    head_office_address = AddressSerializer(required=False)  # Remove required=False to make it required
    created_by = UserSerializer(read_only=True)
    examined_by = UserSerializer(read_only=True)
    approved_by = UserSerializer(read_only=True)

    class Meta:
        model = IssuingCompany
        fields = '__all__'
        read_only_fields = ('created_at', 'updated_at', 'status', 'history')

    def create(self, validated_data):
        request = self.context.get('request')
        if request and hasattr(request, 'user'):
            validated_data['created_by'] = request.user
        address_data = validated_data.pop('head_office_address', None)
        address = None
        # if not address_data:
        #     raise serializers.ValidationError({"head_office_address": "Adresse obligatoire."})
        # print("Adresse extraite pour création:", address_data)
        try:
            # Create the address first
            if address_data:
                address = Address.objects.create(**address_data)
            
            # Create the issuing company with the address
            issuing_company = IssuingCompany.objects.create(
                head_office_address=address,
                **validated_data
            )
            return issuing_company
        except Exception as e:
            # If there was an error, make sure to clean up any created address
            if 'address' in locals():
                address.delete()
            raise serializers.ValidationError(f"Une erreur s'est produite lors de la création de l'entité émettrice: {str(e)}")

    def update(self, instance, validated_data):
        address_data = validated_data.pop('head_office_address', None)
        if address_data:
            # Update existing address or create new one
            if instance.head_office_address:
                for attr, value in address_data.items():
                    setattr(instance.head_office_address, attr, value)
                instance.head_office_address.save()
            else:
                address = Address.objects.create(**address_data)
                instance.head_office_address = address
        
        # Update the company instance
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        return instance
    
    #Mise a jour d'une societe emettrice 



class SocialActSerializer(serializers.ModelSerializer):
    """
    Serializer pour l'acte social
    """
    issuing_company = IssuingCompanySerializer(read_only=True)
    issuing_company_id = serializers.PrimaryKeyRelatedField(
        queryset=IssuingCompany.objects.all(), write_only=True, source='issuing_company'
    )
    created_by  = UserSerializer(read_only=True)
    examined_by = UserSerializer(read_only=True)
    approved_by = UserSerializer(read_only=True)

    class Meta:
        model = SocialAct
        fields = '__all__'
        read_only_fields = ('created_at', 'updated_at','status','history')

    #Validation du capital
    def validate(self,data):
        new_capital = data.get('new_capital',0)
        older_capital = data.get('older_capital',0)
        if new_capital< older_capital:
            raise serializers.ValidationError({
                'new_capital': "Le capital nouveau doit être supérieur au capital antérieur"
            })
        return data
    
    #Creation d'un acte social
    def create(self, validated_data):
        request = self.context.get('request')
        if request and hasattr(request, 'user'):
            validated_data['created_by'] = request.user
        social_act = SocialAct.objects.create(**validated_data)
        return social_act
    
    #Mise a jour d'un acte social
    def update(self,instance,validate_data):
        for attr,value in validate_data.items():
            setattr(instance,attr,value)
        instance.save()
        return instance
    
class ActeSocialAugmentationSerializer(serializers.ModelSerializer):
    """
    Serializer pour l'augmentation d'un augmentation de capital
    """
    issuing_company= IssuingCompanySerializer(read_only=True)

    class Meta:
        model = ActeSocialAugmentation
        fields = '__all__'
        read_only_fields = ('nouveau_capital',)

    #Validation
    def validate(self, data):
        if data['new_capital'] <= data['older_capital']:
            raise serializers.ValidationError({
                'new_capital': "Le nouveau capital doit être supérieur à l'ancien."
            })
        return data
    

class ActeSocialReductionSerializer(serializers.Serializer):
    """
    Serializer pour la reduction de capital
    """
    issuing_company= IssuingCompanySerializer(read_only=True)
    
    class Meta:
        model = ActeSocialReduction
        fields = '__all__'
        read_only_fields = ('nouveau_capital',)

    #Validation
    def validate(self, data):
        if data['new_capital'] >= data['older_capital']:
            raise serializers.ValidationError({
                'new_capital': "Le nouveau capital doit être inférieur à l'ancien."
            })
        return data
    
class SocialeSerializer(serializers.Serializer):
    """
    Serializer pour les informations sociales
    """
    issuing_company = IssuingCompanySerializer(read_only=True)

    class Meta:
        model = Sociale
        fields = '__all__'


class TransactionSerializer(serializers.Serializer):
    """
    Serializer pour les transactions
    """
    issuing_company = IssuingCompanySerializer(read_only=True)
    issuing_company_id = serializers.PrimaryKeyRelatedField(
        queryset=IssuingCompany.objects.all(), write_only=True, source='issuing_company'
    )
    seller = serializers.SerializerMethodField()
    buyer = serializers.SerializerMethodField()

    class Meta:
        model = Transaction
        fields = '__all__'
        read_only_fields = ('total_amount', 'transaction_date')

    def get_seller(self, obj):
        return str(obj.seller)
    
    def get_buyer(self, obj):
        return str(obj.buyer)
    
    def create(self, validated_data):
        request = self.context.get('request')
        try:
            if request and hasattr(request, 'user'):
                validated_data['created_by'] = request.user
            required_fields = ['seller_content_type', 'seller_object_id', 'buyer_content_type', 'buyer_object_id', 'issuing_company']
            missing_fields = [field for field in required_fields if field not in validated_data]
            if missing_fields:
                raise serializers.ValidationError({"error": f"Missing required fields: {', '.join(missing_fields)}"})
            transaction = Transaction.objects.create(**validated_data)
            try:
                transaction.calculate_total_amount()
            except Exception as e:
                raise serializers.ValidationError({"error": f"Error calculating total amount: {str(e)}"})
            return transaction
        except Exception as e:
            raise serializers.ValidationError({"error": f"Error creating transaction: {str(e)}"})

    
    def update(self, instance, validated_data):
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        instance.calculate_total_amount()
        return instance
    

