@echo off
chcp 65001 > nul
echo ======================================================================
echo           ⚡ LANCEMENT DU TERMINAL ALPHA SCANNER PRO STUDIO
echo ======================================================================
echo.

set PYTHON_EXE=C:\Users\kassem.melhem\AppData\Local\anaconda3\envs\alpha\python.exe

if not exist "%PYTHON_EXE%" (
    set PYTHON_EXE=C:\Users\kassem.melhem\AppData\Local\anaconda3\python.exe
)

if not exist "%PYTHON_EXE%" (
    echo [ERREUR] Python introuvable. Verifiez votre installation Anaconda.
    pause
    exit /b 1
)

echo [1/2] Utilisation de l'interpreteur : %PYTHON_EXE%
echo [2/2] Demarrage de l'application interactive Streamlit...
echo.
echo L'application va s'ouvrir dans votre navigateur a l'adresse : http://localhost:8501
echo Pour arreter l'application, appuyez sur Ctrl+C dans cette fenetre.
echo.

"%PYTHON_EXE%" -m streamlit run dashboard.py --server.port 8501 --browser.serverAddress localhost

pause
