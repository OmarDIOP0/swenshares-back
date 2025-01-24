from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

# from .permissions import IsAdminUser, IsEditeurUser




# class ActionsView(APIView):
#     permission_classes = [IsAuthenticated]

#     def get(self, request):
#         # Votre logique pour récupérer les actions
#         actions = [
#             {"type": "Action A", "valeur": 1000},
#             {"type": "Action B", "valeur": 2000},
#         ]
#         return Response(actions)
    

# class ActionnairesListView(APIView):
#     permission_classes = [IsAuthenticated, IsAdminUser]
    
#     def get(self, request):
#         actionnaires = [
#             {"nom": "Dupont", "actions": 100},
#             {"nom": "Martin", "actions": 200},
#         ]
#         return Response(actionnaires)
    

# class TestAuthView(APIView):
#     permission_classes = [IsAuthenticated]
    
#     def get(self, request):
#         return Response({
#             'user_id': request.user.id,
#             'username': request.user.username,
#             'email': request.user.email,
#             'roles': request.user.roles,
#             'is_authenticated': request.user.is_authenticated,
#         })