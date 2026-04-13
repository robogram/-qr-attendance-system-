# PowerShell script to create a Desktop Shortcut for the QR Attendance System
$DesktopPath = [Environment]::GetFolderPath("Desktop")
$ShortcutPath = Join-Path $DesktopPath "로보그램 QR 출석 시스템.lnk"
$WshShell = New-Object -ComObject WScript.Shell
$Shortcut = $WshShell.CreateShortcut($ShortcutPath)

# Target configuration
$BaseDir = Get-Location
$Shortcut.TargetPath = Join-Path $BaseDir "start_system.bat"
$Shortcut.WorkingDirectory = $BaseDir
$Shortcut.IconLocation = Join-Path $BaseDir "icons\attendance_icon.ico"
$Shortcut.WindowStyle = 1 # Normal window
$Shortcut.Description = "로보그램 QR 출석 시스템 시작"

$Shortcut.Save()

Write-Host "✅ 바탕화면에 '로보그램 QR 출석 시스템' 아이콘이 생성되었습니다!" -ForegroundColor Green
Write-Host "📍 경로: $ShortcutPath"
