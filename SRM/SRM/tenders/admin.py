from django.contrib import admin
from .models import Tender, Client, TenderDocument, AuditLog

admin.site.register(Tender)
admin.site.register(Client)
admin.site.register(TenderDocument)
admin.site.register(AuditLog)
