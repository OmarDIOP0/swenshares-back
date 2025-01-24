from django.core.exceptions import ValidationError

class Exception:

    #Fonction pour gerer le format PDF
    @staticmethod
    def validate_file_extension(value):
        if not value.name.endswith('.pdf'):
            raise ValidationError("Seul les documents PDF sont permis .")
    
    @staticmethod
    def validate_image_extension(value):
        if not (value.name.endswith('.jpg') or value.name.endswith('.png') or value.name.endswith('.jpeg')):
            raise ValidationError("Seul les images jpg, png ou jpeg sont permis .")

    #Fonction pour gerer la taille du fichier
    @staticmethod
    def validate_file_size(value):
        max_size = 5 * 1024 * 1024  #5MB
        if value.size > max_size:
            raise ValidationError("La taille du fichier doit etre inferieur a 5MB")