import logging
import mimetypes

from rest_framework.views import APIView

from rest_framework.response import Response

from rest_framework import status

from rest_framework.permissions import IsAuthenticated, AllowAny, IsAdminUser

from rest_framework.authtoken.models import Token

from django.contrib.auth import authenticate

from django.conf import settings

# from api.tasks import run_rag_task

import requests

import os
from rest_framework.pagination import PageNumberPagination
from .models import QueryLog, Conversation, Message
from backend.serializers import ConversationSerializer, SignupSerializer
#from .agent import ask_agent
from .orchestrator import ask_agent
from django.http import FileResponse, Http404
from django.conf import settings
import json


 
logger = logging.getLogger(__name__)
 
class LoginView(APIView):

    permission_classes = [AllowAny]

    def post(self, request):

        username = request.data.get('username')

        password = request.data.get('password')

        user = authenticate(username=username, password=password)

        if user:

            token, _ = Token.objects.get_or_create(user=user)

            return Response(

                {

                    'token': token.key,

                    'user_id': user.id,

                    'username': user.username,

                    'email': user.email,

                    'staff_status': user.is_staff

                },

                status=status.HTTP_200_OK

            )

        return Response({'error': 'Invalid credentials'}, status=status.HTTP_401_UNAUTHORIZED)
 
class SignupView(APIView):

    permission_classes = [AllowAny]

    def post(self, request):

        serializer = SignupSerializer(data=request.data)

        if serializer.is_valid():

            serializer.save()

            return Response({"success": "User created successfully"}, status=status.HTTP_201_CREATED)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
 
class UploadPDFView(APIView):

    permission_classes = [IsAuthenticated]

    def post(self, request):

        files = request.FILES.getlist("files")

        conversation_id = request.data.get("conversation_id")
 
        if not conversation_id:

            return Response({"error": "conversation_id is required"}, status=status.HTTP_400_BAD_REQUEST)

        if not files:

            return Response({"error": "No files uploaded"}, status=status.HTTP_400_BAD_REQUEST)
 
        session_folder = os.path.join(settings.BASE_DIR, "tmp_uploads", str(request.user.id), str(conversation_id))

        os.makedirs(session_folder, exist_ok=True)
 
        uploaded_files = []

        for file in files:

            file_path = os.path.join(session_folder, file.name)

            with open(file_path, "wb+") as f:

                for chunk in file.chunks():

                    f.write(chunk)

            uploaded_files.append(file.name)
 
        return Response({

            "conversation_id": conversation_id,

            "uploaded_files": uploaded_files,

            "message": f"{len(uploaded_files)} file(s) uploaded successfully."

        })
 
class ChatRAGView_1(APIView):

    permission_classes = [IsAuthenticated]

    def post(self, request):

        prompt = request.data.get("prompt", "").strip()

        conversation_id = request.data.get("conversation_id")

        if not prompt:

            return Response({"error": "Prompt is required"}, status=status.HTTP_400_BAD_REQUEST)
 
        #result = ask_agent(prompt=prompt, user=request.user, conversation_id=conversation_id)
        result = []
        if "error" in result:

            return Response({"error": result["error"]}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
 
        return Response({

            "conversation_id": result.get("conversation_id", "new"),

            "content": result.get("response_text", ""),

            "source_documents": result.get("source_documents", []),

            "tokens_used": result.get("tokens_used", 0),

            "prompt_tokens": result.get("prompt_tokens", 0),

            "completion_tokens": result.get("completion_tokens", 0),

            "total_cost": result.get("total_cost", 0.0),

            "latency": result.get("latency", 0.0),
           

        })

class ChatRAGView_3(APIView):

    permission_classes = [IsAuthenticated]

    def post(self, request):

        prompt = request.data.get("prompt", "").strip()

        conversation_id = request.data.get("conversation_id")

        if not prompt:

            return Response({"error": "Prompt is required"}, status=status.HTTP_400_BAD_REQUEST)
 
        #result = ask_agent_2(prompt=prompt, user=request.user, conversation_id=conversation_id)
        result = []
        if "error" in result:

            return Response({"error": result["error"]}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
 
        return Response({

            "conversation_id": result.get("conversation_id", "new"),

            "content": result.get("response_text", ""),

            "source_documents": result.get("source_documents", []),

            "tokens_used": result.get("tokens_used", 0),

            "prompt_tokens": result.get("prompt_tokens", 0),

            "completion_tokens": result.get("completion_tokens", 0),

            "total_cost": result.get("total_cost", 0.0),

            "latency": result.get("latency", 0.0),
           

        })

# class ChatRAGView_2(APIView):
 
#     permission_classes = [IsAuthenticated]
 
#     def post(self, request):
 
#         prompt = request.data.get("prompt", "").strip()
 
#         conversation_id = request.data.get("conversation_id")

#         trinity_Auth = request.data.get("trinity_auth", "").strip()
#         if not trinity_Auth:
#             return Response({"error": "Trinity AuthToken is required"}, status=400)
 
#         if not prompt:
 
#             return Response({"error": "Prompt is required"}, status=status.HTTP_400_BAD_REQUEST)
        
#         strEmpID = request.data.get("strEmpID").strip(),
#         if not strEmpID:
#             return Response({"error": "Employee ID is required"}, status=400)
        
#         lms_jwt_token = request.data.get("lms_jwt_token").strip(),
#         if not lms_jwt_token:
#             return Response({"error": "LMS JWT Token is required"}, status=400)
        
#         result = ask_agent(prompt=prompt, trinity_Auth=trinity_Auth, strEmpID=strEmpID, lms_jwt_token=lms_jwt_token, user=request.user, conversation_id=conversation_id)
       
#         if "error" in result:
 
#             return Response({"error": result["error"]}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
 
#         return Response({
 
#             "conversation_id": result.get("conversation_id", "new"),
 
#             "content": result.get("response_text", ""),
 
#             "source_documents": result.get("source_documents", []),
 
#             "tokens_used": result.get("tokens_used", 0),
 
#             "prompt_tokens": result.get("prompt_tokens", 0),
 
#             "completion_tokens": result.get("completion_tokens", 0),
 
#             "total_cost": result.get("total_cost", 0.0),
 
#         })


class ChatRAGView_2(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        # 1. Extract Data from Request
        prompt = request.data.get("prompt", "").strip()
        conversation_id = request.data.get("conversation_id")
        
        # Extract Auth Tokens required for specific tools
        trinity_auth = request.data.get("trinity_auth", "").strip()
        str_emp_id = request.data.get("strEmpID", "").strip()
        lms_jwt_token = request.data.get("lms_jwt_token", "").strip()

        # 2. Basic Validation
        if not prompt:
            return Response({"error": "Prompt is required"}, status=status.HTTP_400_BAD_REQUEST)
        
        # (Optional) Add specific validation for tokens if critical
        if not trinity_auth:
             return Response({"error": "Trinity AuthToken is required"}, status=status.HTTP_400_BAD_REQUEST)

        # 3. Call the Orchestrator
        # We pass request.user so the agent knows who is asking (for PDF pathing/history)
        result = ask_agent(
            prompt=prompt, 
            trinity_Auth=trinity_auth, 
            strEmpID=str_emp_id, 
            lms_jwt_token=lms_jwt_token, 
            user=request.user, 
            conversation_id=conversation_id
        )
        
        # 4. Handle Internal Errors from Agent
        if "error" in result:
            return Response({"error": result["error"]}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        # 5. Return Success Response matching your Orchestrator return
        return Response({
            "conversation_id": result.get("conversation_id"),
            "content": result.get("response_text", ""),
            "source_documents": result.get("source_documents", []),
            "tokens_used": result.get("tokens_used", 0),
            "prompt_tokens": result.get("prompt_tokens", 0),
            "completion_tokens": result.get("completion_tokens", 0),
            "total_cost": result.get("total_cost", 0.0),
            "latency": result.get("latency", 0.0),
        }, status=status.HTTP_200_OK)


class ChatView(APIView):

    permission_classes = [IsAuthenticated]

    def post(self, request):

        prompt = request.data.get('prompt', '')

        conversation_id = request.data.get('conversation_id', None)

        if not prompt:

            return Response({'error': 'Prompt is required'}, status=status.HTTP_400_BAD_REQUEST)
 
        if conversation_id:

            try:

                conversation = Conversation.objects.get(id=conversation_id, user=request.user)

            except Conversation.DoesNotExist:

                return Response({'error': 'Invalid conversation ID'}, status=status.HTTP_400_BAD_REQUEST)

        else:

            conversation = Conversation.objects.create(user=request.user, title=prompt[:50])
 
        previous_queries = QueryLog.objects.filter(conversation=conversation).order_by('timestamp')

        conversation_history = '\n'.join([f"Q: {q.prompt}\nA: {q.response}" for q in previous_queries])

        full_prompt = f"Conversation History:\n{conversation_history}\n\n Always provide the response in less than 100 words Question: {prompt}\nAnswer:"
 
        try:

            response = requests.post(

                "http://ollama:11434/api/generate",

                json={"model": "gemma2:2b-instruct-q4_K_M", "prompt": full_prompt, "stream": False},

                timeout=60

            )

            response.raise_for_status()

            data = response.json()

            response_text = data.get('response', '').strip()
 
            QueryLog.objects.create(conversation=conversation, prompt=prompt, response=response_text)

            Message.objects.create(conversation=conversation, content=prompt, is_user=True)

            Message.objects.create(conversation=conversation, content=response_text, is_user=False)
 
            return Response({

                'content': response_text,

                'conversation_id': conversation.id

            }, status=status.HTTP_200_OK)
 
        except requests.Timeout:

            return Response({'error': 'Ollama request timed out'}, status=status.HTTP_504_GATEWAY_TIMEOUT)

        except requests.RequestException as e:

            return Response({'error': f'Ollama request failed: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
 
class HistoryView(APIView):

    permission_classes = [IsAuthenticated]

    def get(self, request):

        conversations = Conversation.objects.filter(user=request.user).prefetch_related('messages').order_by('-created_at')

        serializer = ConversationSerializer(conversations, many=True)

        return Response(serializer.data, status=status.HTTP_200_OK)
    
class ConversationDetailView(APIView):    
    permission_classes = [IsAuthenticated]
    def get(self, request, conversation_id):
        try:            
            conversation = Conversation.objects.prefetch_related('message_set').get(id=conversation_id, 
                user=request.user
            )            
            serializer = ConversationSerializer(conversation)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except Conversation.DoesNotExist:
            return Response({"error": "Conversation not found or does not belong to the user"},                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:            logger.error(f"Error in ConversationDetailView: {str(e)}")
        return Response({"error": f"Error fetching conversation: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
 
 
class DeleteConversationView(APIView):

    permission_classes = [IsAuthenticated]

    def delete(self, request, conversation_id):

        try:

            conversation = Conversation.objects.get(id=conversation_id, user=request.user)

            conversation.delete()

            conversations = Conversation.objects.filter(user=request.user).prefetch_related('messages').order_by('-created_at')

            serializer = ConversationSerializer(conversations, many=True)

            return Response({

                "message": "Conversation deleted successfully",

                "conversations": serializer.data

            }, status=status.HTTP_200_OK)

        except Conversation.DoesNotExist:

            return Response({"error": "Conversation not found or does not belong to the user"}, status=status.HTTP_404_NOT_FOUND)

        except Exception as e:

            return Response({"error": f"Error deleting conversation: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


 
class AdminHistoryView(APIView):

    permission_classes = [IsAdminUser]

    def get(self, request):

        try:

            user_id = request.query_params.get('user_id')

            username = request.query_params.get('username')

            conversations = Conversation.objects.select_related('user').prefetch_related('messages').order_by('-created_at')

            if user_id:

                conversations = conversations.filter(user__id=user_id)

            elif username:

                conversations = conversations.filter(user__username__icontains=username)

            serializer = ConversationSerializer(conversations, many=True)

            return Response(serializer.data, status=status.HTTP_200_OK)

        except Exception as e:

            return Response({"error": f"Error fetching conversations: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class AdminHistoryPagination(PageNumberPagination):
    page_size = 10  # Define how many items per page
    page_size_query_param = 'page_size'
    max_page_size = 100  # Max number of items that can be fetched in one page


class AdminHistoryPaginatedView(APIView):
    permission_classes = [IsAdminUser]

    def get(self, request):

        try:
            user_id = request.query_params.get('user_id')
            username = request.query_params.get('username')

            # Start with the basic queryset
            conversations = Conversation.objects.select_related('user').prefetch_related('messages').order_by('-created_at')

            # Apply filters based on the query params
            if user_id:
                conversations = conversations.filter(user__id=user_id)
            elif username:
                conversations = conversations.filter(user__username__icontains=username)

            # Paginate the queryset
            paginator = AdminHistoryPagination()
            result_page = paginator.paginate_queryset(conversations, request)

            # Serialize the paginated result
            serializer = ConversationSerializer(result_page, many=True)

            return paginator.get_paginated_response(serializer.data)

        except Exception as e:
            return Response({"error": f"Error fetching conversations: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
def download_pdf(request, user_id, conversation_id, file_name):
    # Construct the file path
    file_path = os.path.join(settings.BASE_DIR, "tmp_uploads", str(user_id), str(conversation_id), file_name)

    # Debugging: print the file path to ensure it is correct
    print(f"Requested file: {file_path}")

    # Check if the file exists
    if not os.path.exists(file_path):
        raise Http404("File not found")

    # Use mimetypes to get the correct content type based on the file extension
    mime_type, _ = mimetypes.guess_type(file_path)

    # If mime_type is None, default to a generic binary type (for non-text files)
    if mime_type is None:
        mime_type = 'application/octet-stream'

    # Serve the file as a response
    response = FileResponse(open(file_path, 'rb'), content_type=mime_type)

    # Set the content disposition to inline (show in browser) or attachment (force download)
    response['Content-Disposition'] = f'inline; filename="{file_name}"'  # Use 'attachment' if you want to force download

    return response

def download_pdf_source(request, file_name):
    # Construct the file path
    file_path = os.path.join(settings.BASE_DIR, "Uploads_folder", file_name)

    # Debugging: print the file path to ensure it is correct
    print(f"Requested file: {file_path}")

    # Check if the file exists
    if not os.path.exists(file_path):
        raise Http404("File not found")

    # Use mimetypes to get the correct content type based on the file extension
    mime_type, _ = mimetypes.guess_type(file_path)

    # If mime_type is None, default to a generic binary type (for non-text files)
    if mime_type is None:
        mime_type = 'application/octet-stream'

    # Serve the file as a response
    response = FileResponse(open(file_path, 'rb'), content_type=mime_type)

    # Set the content disposition to inline (show in browser) or attachment (force download)
    response['Content-Disposition'] = f'inline; filename="{file_name}"'  # Use 'attachment' if you want to force download

    return response

from django.conf import settings
from django.http import FileResponse, Http404
import os

def download_price_report(request, filename):
    """
    Serve a generated price report CSV file for download.
    """
    filepath = os.path.join(settings.MEDIA_ROOT, filename)
    if os.path.exists(filepath):
        return FileResponse(open(filepath, 'rb'), as_attachment=True, filename=filename)
    else:
        raise Http404("Report not found")
    
def download_source_document(request, filename):
    """
    Serve an Excel file from Excel_upload for download.
    """
    base_path = os.path.join(settings.BASE_DIR, "Excel_upload")
    filepath = os.path.join(base_path, filename)

    if os.path.exists(filepath):
        return FileResponse(open(filepath, 'rb'),
                            as_attachment=True,
                            filename=filename)
    else:
        raise Http404("Source document not found")

logger = logging.getLogger(__name__)

 