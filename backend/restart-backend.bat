@echo off
echo ========================================
echo Restarting PlanHub Backend
echo ========================================

echo.
echo Step 1: Cleaning and compiling...
cd /d "%~dp0"
mvn clean compile -q

echo.
echo Step 2: Packaging...
mvn package -DskipTests -q

echo.
echo Step 3: Starting application...
echo Please wait for the application to start...
echo.

cd target
java -jar planhub-backend-*.jar

pause
