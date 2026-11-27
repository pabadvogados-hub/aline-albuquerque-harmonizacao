@echo off
rem Atualiza o painel todo dia as 7h
schtasks /create /tn "Painel Aline Albuquerque" /tr "\"%~dp0atualizar_painel.bat\"" /sc daily /st 07:00 /f
pause
