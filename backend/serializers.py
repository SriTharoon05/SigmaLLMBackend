from rest_framework import serializers

from .models import Conversation, QueryLog, Message, Document_infinium, Conversation_infinium, Message_infinium, QueryLog_infinium, FAQ_infinium

from django.contrib.auth.models import User
import json
from django.contrib.auth.hashers import make_password
 
# --- User Serializer ---

class UserSerializer(serializers.ModelSerializer):

    class Meta:

        model = User

        fields = ["id", "username", "email"]
 
# --- Signup Serializer ---

class SignupSerializer(serializers.ModelSerializer):

    password = serializers.CharField(write_only=True, required=True, min_length=6)
 
    class Meta:

        model = User

        fields = ["username", "email", "password"]
 
    def create(self, validated_data):

        validated_data["password"] = make_password(validated_data["password"])

        return super().create(validated_data)
 
# --- QueryLog Serializer ---

class QueryLogSerializer(serializers.ModelSerializer):

    source_documents = serializers.SerializerMethodField()
 
    class Meta:

        model = QueryLog

        fields = [

            "prompt",

            "response",

            "source_documents",

            "tokens_used",

            "prompt_tokens",

            "completion_tokens",

            "total_cost",

            "timestamp",
            "latency",

        ]
 
    def get_source_documents(self, obj):
    
        if not obj.sources:
            return []

        try:
            # Convert JSON string → Python list
            return json.loads(obj.sources)
        except Exception:
            return []

    # def get_source_documents(self, obj):
    #     if obj.sources:
    #         # Assuming sources is a list of dictionaries, you can return the relevant parts.
    #         # For example, extracting 'name' and 'url' if they exist.
    #         return [{"name": s.get("name", ""), "url": s.get("url", "")} for s in obj.sources]
    #     return []
# --- Message Serializer ---

class MessageSerializer(serializers.ModelSerializer):

    class Meta:

        model = Message

        fields = ["id", "content", "is_user", "timestamp"]
 
# --- Conversation Serializer ---

class ConversationSerializer(serializers.ModelSerializer):

    user = UserSerializer(read_only=True)  # Add user info for admin

    query_logs = serializers.SerializerMethodField()

    messages = MessageSerializer(many=True, read_only=True, source="message_set")  # <-- Fix: include all conversation messages
 
    class Meta:

        model = Conversation

        fields = [

            "id",

            "title",

            "created_at",

            "tokens_used",

            "prompt_tokens",

            "completion_tokens",

            "total_cost",

            "user",

            "query_logs",

            "messages",  # <-- Main fix for frontend reload issue!

        ]
 
    def get_query_logs(self, obj):

        logs = QueryLog.objects.filter(conversation=obj).order_by("timestamp")

        return QueryLogSerializer(logs, many=True).data
 