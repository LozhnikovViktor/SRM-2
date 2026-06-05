from django.urls import path
from django.contrib.auth.views import LoginView, LogoutView
from . import views

app_name = 'tenders'
urlpatterns = [
    path('', views.TenderListView.as_view(), name='list'),
    path('dashboard/', views.dashboard, name='dashboard'),  # 🔹 Добавьте эту строку
    path('create/', views.TenderCreateView.as_view(), name='create'),  # 🔹 Для создания (не 'add'!)
    path('<int:pk>/edit/', views.TenderUpdateView.as_view(), name='edit'),
    path('<int:pk>/delete/', views.TenderDeleteView.as_view(), name='delete'),
    path('add/', views.TenderCreateView.as_view(), name='add'),
    path('register/', views.RegisterView.as_view(), name='register'),
    path('login/', LoginView.as_view(template_name='tenders/login.html'), name='login'),
    path('logout/', LogoutView.as_view(next_page='tenders:list'), name='logout'),
    path('edit/<int:pk>/', views.TenderUpdateView.as_view(), name='edit'),
    path('delete/<int:pk>/', views.TenderDeleteView.as_view(), name='delete'),
    path('export/excel/', views.export_tenders_excel, name='export_excel'),
    path('dashboard/export/excel/', views.export_dashboard_excel, name='export_dashboard_excel'),
    path('search/', views.ExternalSearchView.as_view(), name='external_search'),
    path('import/', views.ImportTenderView.as_view(), name='import_tender'),
]

