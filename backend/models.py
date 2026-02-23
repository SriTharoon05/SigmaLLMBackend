from django.db import models
from django.contrib.auth.models import Group

class Conversation(models.Model):
    user = models.ForeignKey('auth.User', on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    title = models.CharField(max_length=255, blank=True, default="New Conversation")
    
    # Token-related fields to store usage and cost
    tokens_used = models.IntegerField(default=0)  # Total tokens used across the entire conversation
    prompt_tokens = models.IntegerField(default=0)  # Tokens used in the prompt
    completion_tokens = models.IntegerField(default=0)  # Tokens used in the completion
    total_cost = models.FloatField(default=0.0)
    active_intent = models.CharField(max_length=50, null=True, blank=True)
    def __str__(self):
        return f"Conversation {self.id}: {self.title}"

class Message(models.Model):
    conversation = models.ForeignKey(Conversation, on_delete=models.CASCADE, related_name='messages')
    content = models.TextField()
    is_user = models.BooleanField(default=True)
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Message in {self.conversation.id} at {self.timestamp}"

class Document(models.Model):
    file_path = models.CharField(max_length=255)
    file_name = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    file_hash = models.CharField(max_length=64, blank=True)
    metadata = models.JSONField(default=dict)

    processed = models.BooleanField(default=False)

    def __str__(self):
        return self.file_name


class QueryLog(models.Model):
    conversation = models.ForeignKey(Conversation, on_delete=models.CASCADE, null=True)
    prompt = models.TextField()  # The user's query
    response = models.TextField()  # The AI-generated response
    timestamp = models.DateTimeField(auto_now_add=True)  # When the query was logged
    sources = models.TextField(blank=True, null=True)  # Citations or sources used to generate the response
    tokens_used = models.IntegerField(default=0)  # Tokens used for this specific response
    prompt_tokens = models.IntegerField(default=0)  # Tokens used in the prompt for this specific response
    completion_tokens = models.IntegerField(default=0)  # Tokens used in the completion for this specific response
    total_cost = models.FloatField(default=0.0)
    latency = models.FloatField(default=0.0)  # Time taken to generate the response in seconds

    def __str__(self):
        return f"Query at {self.timestamp}"

class FAQ(models.Model):
    question = models.TextField()
    answer = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.question
    
class Conversation_infinium(models.Model):
    user = models.ForeignKey('auth.User', on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    title = models.CharField(max_length=255, blank=True, default="New Conversation")
    
    # Token-related fields to store usage and cost
    tokens_used = models.IntegerField(default=0)  # Total tokens used across the entire conversation
    prompt_tokens = models.IntegerField(default=0)  # Tokens used in the prompt
    completion_tokens = models.IntegerField(default=0)  # Tokens used in the completion
    total_cost = models.FloatField(default=0.0)

    def __str__(self):
        return f"Conversation {self.id}: {self.title}"

class Message_infinium(models.Model):
    conversation = models.ForeignKey(Conversation_infinium, on_delete=models.CASCADE, related_name='messages')
    content = models.TextField()
    is_user = models.BooleanField(default=True)
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Message in {self.conversation.id} at {self.timestamp}"

class Document_infinium(models.Model):
    file_path = models.CharField(max_length=255)
    file_name = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    file_hash = models.CharField(max_length=64, blank=True)
    metadata = models.JSONField(default=dict)

    processed = models.BooleanField(default=False)

    def __str__(self):
        return self.file_name


class QueryLog_infinium(models.Model):
    conversation = models.ForeignKey(Conversation_infinium, on_delete=models.CASCADE, null=True)
    prompt = models.TextField()  # The user's query
    response = models.TextField()  # The AI-generated response
    timestamp = models.DateTimeField(auto_now_add=True)  # When the query was logged
    sources = models.TextField(blank=True, null=True)  # Citations or sources used to generate the response
    #sources = models.JSONField()
    tokens_used = models.IntegerField(default=0)  # Tokens used for this specific response
    prompt_tokens = models.IntegerField(default=0)  # Tokens used in the prompt for this specific response
    completion_tokens = models.IntegerField(default=0)  # Tokens used in the completion for this specific response
    total_cost = models.FloatField(default=0.0)
    latency = models.FloatField(default=0.0)  # Time taken to generate the response in seconds

    def __str__(self):
        return f"Query at {self.timestamp}"

class FAQ_infinium(models.Model):
    question = models.TextField()
    answer = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.question

def create_roles():
    Group.objects.get_or_create(name='Admin')
    Group.objects.get_or_create(name='User')