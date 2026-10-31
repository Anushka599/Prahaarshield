@echo off
cd /d %~dp0
echo.
echo  PrahaarShield v3 is starting... (first start ~20-40 s to load the model)
echo  TESTING UI (both sides):   http://localhost:8000/sim
echo  Phone view  (same Wi-Fi):  http://YOUR-LAPTOP-IP:8000/sim?view=user
echo  Laptop scammer view:       http://localhost:8000/sim?view=scam
echo  Engine status:             http://localhost:8000/api/info
echo.
python -m uvicorn server.main:app --host 0.0.0.0 --port 8000
pause
