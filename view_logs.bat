@echo off
title SponsorPulse Live Logs
echo ========================================================
echo   SponsorPulse Live Backend Logs (Auto-Refreshing)
echo ========================================================
echo.
powershell -NoExit -Command "Get-Content -Wait -Tail 50 'C:\Users\pavan\.gemini\antigravity\brain\bcd89a24-9b1b-43a2-9f0f-b3c75d49cbdf\.system_generated\tasks\task-702.log'"
