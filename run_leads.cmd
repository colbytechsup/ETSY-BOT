@echo off
rem Windows Task Scheduler entry point: pulls new lead emails and pushes them to GHL.
rem Reads settings from .env in this folder. Log goes to leads.log next to it.
cd /d "%~dp0"
echo [%date% %time%] imap run >> leads.log
python -m leads imap >> leads.log 2>&1
