from django.urls import include, path

from django.contrib import admin
from . import views
from .views import  ChatView, LoginView, HistoryView, SignupView, DeleteConversationView,AdminHistoryView,UploadPDFView,ConversationDetailView, ChatRAGView_2, download_pdf, AdminHistoryPaginatedView, ChatRAGView_3,download_pdf_source
urlpatterns = [
    path('login/', LoginView.as_view(), name='login'),
    path('signup/', SignupView.as_view(), name='signup'),
    path('upload/', UploadPDFView.as_view(), name='upload'),
    path('chat/', ChatView.as_view(), name='chat'),
    path('rag/', ChatRAGView_2.as_view(), name='rag'), #changed from 1 to 2 for timesheet
   # path('rag/status/<str:task_id>/', RAGTaskStatusView.as_view(), name='rag_status'),
    path('rag_excel/', ChatRAGView_3.as_view(), name='rag_excel'),
   # path('rag_ollama/', ChatRAGView_1.as_view(), name='rag_ollama'),
    path('history/', HistoryView.as_view(), name='history'),
    path('delete/<int:conversation_id>/', DeleteConversationView.as_view(), name='delete_conversation'),
    path('history/all/', AdminHistoryView.as_view(), name='history_all'),
    path('history/paginated/', AdminHistoryPaginatedView.as_view(), name='history_paginated'),
    #path('upload/', ChatWithSessionDocsView.as_view(), name='chat_with_session_docs'),
    path('api/conversation/<int:conversation_id>/', ConversationDetailView.as_view(), name='conversation_detail'),
    path('download/<int:user_id>/<int:conversation_id>/<str:file_name>/', download_pdf, name='download_pdf'),
    path('download-report/<str:filename>/', views.download_price_report, name='download_report'),
    path('download-source/<str:filename>/', views.download_source_document, name='download_source_document'),
    path('download_source_doc/<str:file_name>/', views.download_pdf_source, name='download_pdf_source'),

]
