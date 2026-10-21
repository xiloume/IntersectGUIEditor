@echo off
echo ============================================
echo   Intersect GUI Editor - Build Script
echo ============================================
echo.

REM Check Python
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERREUR] Python n'est pas installe ou pas dans le PATH.
    echo Telecharger Python: https://www.python.org/downloads/
    pause
    exit /b 1
)

echo [1/3] Installation des dependances...
pip install -r requirements.txt
if errorlevel 1 (
    echo [ERREUR] Echec d'installation des dependances.
    pause
    exit /b 1
)

echo.
echo [2/3] Compilation de l'executable...
pyinstaller --onefile --windowed ^
    --name "IntersectGUIEditor" ^
    --add-data "icon.ico;." ^
    --icon icon.ico ^
    intersect_gui_editor.py 2>nul

if not exist "icon.ico" (
    pyinstaller --onefile --windowed ^
        --name "IntersectGUIEditor" ^
        intersect_gui_editor.py
)

if errorlevel 1 (
    echo [ERREUR] Echec de compilation.
    pause
    exit /b 1
)

echo.
echo [3/3] Nettoyage...
rmdir /s /q build 2>nul
del IntersectGUIEditor.spec 2>nul

echo.
echo ============================================
echo   SUCCES! L'executable se trouve dans:
echo   dist\IntersectGUIEditor.exe
echo ============================================
echo.
pause
