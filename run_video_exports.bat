
@echo off
setlocal
cd /d "%~dp0"

echo ==========================================
echo   FACELESS VIDEO EXPORT PIPELINE
echo ==========================================

echo.
echo [1/3] Checking Python script syntax...
python -m py_compile src\run_pipeline_final.py
if errorlevel 1 goto failed

echo.
echo [2/3] Rendering landscape and vertical videos...
python src\run_pipeline_final.py
if errorlevel 1 goto failed

echo.
echo [3/3] Checking final video files...

if not exist "output\youtube_landscape_final.mp4" goto failed
if not exist "output\short_vertical_final.mp4" goto failed

for %%F in ("output\youtube_landscape_final.mp4") do (
    if %%~zF LEQ 0 goto failed
)

for %%F in ("output\short_vertical_final.mp4") do (
    if %%~zF LEQ 0 goto failed
)

echo.
echo Pipeline finished without a reported error.
echo Landscape: output\youtube_landscape_final.mp4
echo Vertical:  output\short_vertical_final.mp4
echo.
echo Please play both files to confirm the result.
pause
exit /b 0

:failed
echo.
echo PIPELINE FAILED. Read the error above before retrying.
pause
exit /b 1
