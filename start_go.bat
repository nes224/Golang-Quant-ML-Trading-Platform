@echo off
echo Starting Golang Analysis Service...
cd Trading_Api\go_analysis
set PATH=%USERPROFILE%\go\bin;C:\Program Files\Go\bin;%PATH%
go run main.go
