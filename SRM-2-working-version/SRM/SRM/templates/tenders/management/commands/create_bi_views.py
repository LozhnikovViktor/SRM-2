from django.core.management.base import BaseCommand
from django.db import connection

class Command(BaseCommand):
    help = 'Создать SQL-представления для Power BI'
    
    def handle(self, *args, **options):
        with connection.cursor() as cursor:
            # Тендеры по статусам
            cursor.execute("""
                CREATE OR REPLACE VIEW bi_tenders_by_status AS
                SELECT 
                    status,
                    COUNT(*) as count,
                    SUM(initial_amount) as total_initial,
                    SUM(final_amount) as total_final,
                    SUM(cost) as total_cost,
                    SUM(final_amount - cost) as total_profit
                FROM tenders_tender
                GROUP BY status;
            """)
            
            # Тендеры по клиентам
            cursor.execute("""
                CREATE OR REPLACE VIEW bi_tenders_by_client AS
                SELECT 
                    c.id as client_id,
                    c.name as client_name,
                    c.inn,
                    COUNT(t.id) as tender_count,
                    SUM(t.final_amount) as total_amount,
                    SUM(t.final_amount - t.cost) as total_profit,
                    AVG(t.final_amount - t.cost) as avg_profit
                FROM tenders_client c
                LEFT JOIN tenders_tender t ON c.id = t.client_id
                WHERE t.status = 'won'
                GROUP BY c.id, c.name, c.inn;
            """)
            
            # Продажи по месяцам
            cursor.execute("""
                CREATE OR REPLACE VIEW bi_sales_monthly AS
                SELECT 
                    DATE_TRUNC('month', created_at) as month,
                    COUNT(*) as shipment_count,
                    SUM(grand_total) as total_revenue
                FROM tenders_commercialproposal
                WHERE status = 'accepted'
                GROUP BY DATE_TRUNC('month', created_at);
            """)
            
            self.stdout.write(self.style.SUCCESS('BI views created!'))