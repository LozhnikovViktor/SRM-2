from django.urls import path
from django.contrib.auth.views import LoginView, LogoutView
from . import views


app_name = 'tenders'

urlpatterns = [
    # 🔹 Главная страница — список тендеров
    path('', views.TenderListView.as_view(), name='list'),
    
    # 🔹 Дашборд
    path('dashboard/', views.dashboard, name='dashboard'),
    
    # 🔹 CRUD тендеров (единообразные URL)
    path('tenders/create/', views.TenderCreateView.as_view(), name='create'),
    path('tenders/<int:pk>/edit/', views.TenderUpdateView.as_view(), name='update'),
    path('tenders/<int:pk>/delete/', views.TenderDeleteView.as_view(), name='delete'),
    
    # 🔹 Авторизация
    path('register/', views.RegisterView.as_view(), name='register'),
    path('login/', LoginView.as_view(template_name='tenders/login.html'), name='login'),
    path('logout/', LogoutView.as_view(next_page='tenders:list'), name='logout'),
    
    # 🔹 Экспорт в Excel
    path('export/excel/', views.export_tenders_excel, name='export_excel'),
    path('dashboard/export/excel/', views.export_dashboard_excel, name='export_dashboard_excel'),
    
    # 🔹 Поиск и импорт тендеров
    path('search/', views.ExternalSearchView.as_view(), name='external_search'),
    path('import/', views.ImportTenderView.as_view(), name='import_tender'),
    
    # 🔹 CRM: Клиенты
    path('clients/', views.ClientListView.as_view(), name='client_list'),
    path('clients/add/', views.ClientCreateView.as_view(), name='client_add'),
    path('clients/<int:pk>/', views.ClientDetailView.as_view(), name='client_detail'),
    path('clients/<int:pk>/edit/', views.ClientUpdateView.as_view(), name='client_edit'),
    path('clients/<int:pk>/delete/', views.ClientDeleteView.as_view(), name='client_delete'),
]