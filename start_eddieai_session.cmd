@echo off
title EddieAI Session
cd /d C:\EddieAI
powershell -NoExit -ExecutionPolicy Bypass -Command "Set-Location C:\EddieAI; & 'C:\Users\keris\AppData\Roaming\npm\opencode.ps1' 'Read file SESSION_BRIEF_EDDIEAI.md now and follow it strictly'"
