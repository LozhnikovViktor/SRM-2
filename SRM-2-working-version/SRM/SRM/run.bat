@echo off
cd /d "%~dp0"
call "C:\Users\Виктор\Desktop\SRM-2-working-version\.venv\Scripts\activate.bat"
python manage.py runserver
pause