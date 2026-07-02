from django.urls import path
from django.contrib.auth.views import LoginView, LogoutView
from django.contrib.auth import views as auth_views
from . import views
from drf_spectacular.views import SpectacularAPIView, SpectacularRedocView, SpectacularSwaggerView
from rest_framework.routers import DefaultRouter


app_name = 'tenders'

urlpatterns = [
    # ============================================
    # 🔹 ГЛАВНАЯ И ДАШБОРД
    # ============================================
    path('', views.TenderListView.as_view(), name='list'),
    path('dashboard/', views.dashboard, name='dashboard'),
    
    # ============================================
    # 🔹 CRUD ТЕНДЕРОВ
    # ============================================
    path('tenders/create/', views.TenderCreateView.as_view(), name='create'),
    path('tenders/<int:pk>/edit/', views.TenderUpdateView.as_view(), name='update'),
    path('tenders/<int:pk>/delete/', views.TenderDeleteView.as_view(), name='delete'),
    
    # ============================================
    # 🔹 АВТОРИЗАЦИЯ
    # ============================================
    path('register/', views.RegisterView.as_view(), name='register'),
    path('login/', LoginView.as_view(template_name='tenders/login.html'), name='login'),
    path('logout/', LogoutView.as_view(next_page='tenders:list'), name='logout'),
    path('client-login/', views.client_login, name='client_login'),
    
    # ============================================
    # 🔹 ВОССТАНОВЛЕНИЕ ПАРОЛЯ
    # ============================================
    path('password_reset/', auth_views.PasswordResetView.as_view(
        template_name='tenders/password_reset.html',
        email_template_name='tenders/password_reset_email.html',
        subject_template_name='tenders/password_reset_subject.txt',
        success_url='/password_reset/done/'
    ), name='password_reset'),
    
    path('password_reset/done/', auth_views.PasswordResetDoneView.as_view(
        template_name='tenders/password_reset_done.html'
    ), name='password_reset_done'),
    
    path('reset/<uidb64>/<token>/', auth_views.PasswordResetConfirmView.as_view(
        template_name='tenders/password_reset_confirm.html',
        success_url='/reset/done/'
    ), name='password_reset_confirm'),
    
    path('reset/done/', auth_views.PasswordResetCompleteView.as_view(
        template_name='tenders/password_reset_complete.html'
    ), name='password_reset_complete'),
    
    # ============================================
    # 🔹 ЭКСПОРТ
    # ============================================
    path('export/excel/', views.export_tenders_excel, name='export_excel'),
    path('dashboard/export/excel/', views.export_dashboard_excel, name='export_dashboard_excel'),
    path('export/word/', views.export_kanban_to_word, name='export_kanban_word'),
    path('dashboard/export/word/', views.export_dashboard_to_word, name='export_dashboard_word'),
    
    # ============================================
    # 🔹 ПОИСК И ИМПОРТ
    # ============================================
    path('search/', views.ExternalSearchView.as_view(), name='external_search'),
    path('import/', views.ImportTenderView.as_view(), name='import_tender'),
    path('tenderplan-search/', views.TenderplanSearchView.as_view(), name='tenderplan_search'),
    path('import-tenderplan/', views.ImportFromTenderplanView.as_view(), name='import_tenderplan'),
    
    # ============================================
    # 🔹 CRM: КЛИЕНТЫ
    # ============================================
    path('clients/', views.ClientListView.as_view(), name='client_list'),
    path('clients/add/', views.ClientCreateView.as_view(), name='client_add'),
    path('clients/<int:pk>/', views.ClientDetailView.as_view(), name='client_detail'),
    path('clients/<int:pk>/edit/', views.ClientUpdateView.as_view(), name='client_edit'),
    path('clients/<int:pk>/delete/', views.ClientDeleteView.as_view(), name='client_delete'),
    path('clients/<int:pk>/activate/', views.activate_client_access, name='client_activate'),
    # ============================================
    # 🔹 ДОКУМЕНТЫ
    # ============================================
    path('tenders/<int:pk>/upload/', views.TenderDocumentUploadView.as_view(), name='document_upload'),
    path('documents/<int:pk>/delete/', views.TenderDocumentDeleteView.as_view(), name='document_delete'),
    
    # ============================================
    # 🔹 АУДИТ
    # ============================================
    path('audit/', views.AuditLogView.as_view(), name='audit_log'),
    
    # ============================================
    # 🔹 КАНБАН
    # ============================================
    path('kanban/', views.TenderKanbanView.as_view(), name='kanban'),
    path('api/tender/status/', views.TenderStatusUpdateView.as_view(), name='api_tender_status'),
    
    # ============================================
    # 🔹 КАЛЕНДАРЬ
    # ============================================
    path('calendar/', views.TenderCalendarView.as_view(), name='calendar'),
    path('api/calendar/data/', views.TenderCalendarDataView.as_view(), name='api_calendar_data'),
    
    # ============================================
    # 🔹 КОММЕНТАРИИ
    # ============================================
    path('tenders/<int:pk>/comments/add/', views.add_comment, name='add_comment'),
    path('comments/<int:pk>/edit/', views.edit_comment, name='edit_comment'),
    path('comments/<int:pk>/delete/', views.delete_comment, name='delete_comment'),
    
    # ============================================
    # 🔹 SWAGGER API
    # ============================================
    path('api/v1/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('api/v1/docs/', SpectacularSwaggerView.as_view(url_name='tenders:schema'), name='swagger-ui'),
    path('api/v1/redoc/', SpectacularRedocView.as_view(url_name='tenders:schema'), name='redoc'),
    
    # ============================================
    # 🔹 API ДЛЯ УВЕДОМЛЕНИЙ
    # ============================================
    path('api/tender/overdue/', views.OverdueTendersView.as_view(), name='api_overdue_tenders'),
    path('api/tender/upcoming/', views.UpcomingDeadlinesView.as_view(), name='api_upcoming_deadlines'),
    
    # ============================================
    # 🔹 АДМИНКА (КАСТОМНАЯ)
    # ============================================
    path('admin/users/', views.user_management, name='user_management'), # 🔹 ЧАТ
    path('chat/', views.chat_room_list, name='chat_list'),
    path('chat/<int:room_id>/', views.chat_room, name='chat_room'),
    path('chat/<int:room_id>/send/', views.chat_send_message, name='chat_send_message'),
    path('chat/<int:room_id>/messages/', views.chat_get_messages, name='chat_get_messages'),
    path('chat/start/<str:content_type>/<int:object_id>/', views.start_chat, name='start_chat'),
    path('api/products/prices/', views.api_products_prices, name='api_products_prices'),
        # ============================================
    # 🔹 ЗАЯВКИ НА ОТГРУЗКУ
    # ============================================
    path('shipment/create/', views.create_shipment_request, name='shipment_create'),
    path('shipment/', views.shipment_request_list, name='shipment_list'),
    path('shipment/<int:pk>/', views.shipment_request_detail, name='shipment_request_detail'),
    path('shipment/<int:pk>/status/', views.shipment_request_update_status, name='shipment_update_status'),
    path('shipment/export/1c/', views.export_shipment_to_1c, name='shipment_export_1c'),
    
    # ============================================
    # 🔹 НОМЕНКЛАТУРА
    # ============================================
    path('products/', views.product_list, name='product_list'),
    path('products/add/', views.product_create, name='product_create'),
    path('api/products/prices/', views.api_products_prices, name='api_products_prices'),
        # ============================================
    # 🔹 КОММЕРЧЕСКИЕ ПРЕДЛОЖЕНИЯ
    # ============================================
    path('cp/create/', views.create_commercial_proposal, name='cp_create'),
    path('cp/<int:pk>/preview/', views.cp_preview, name='cp_preview'),
    path('cp/<int:pk>/edit/', views.cp_edit, name='cp_edit'),
    path('cp/', views.cp_list, name='cp_list'),
    path('cp/<int:pk>/', views.cp_detail, name='cp_detail'),
]

# ============================================
# 🔹 DRF ROUTER
# ============================================
router = DefaultRouter()
router.register(r'api/tenders', views.TenderViewSet, basename='tender')
router.register(r'api/clients', views.ClientViewSet, basename='client')

urlpatterns += router.urls