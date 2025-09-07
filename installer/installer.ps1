if (-not ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
    Write-Host "Запусти скрипт от админки!"
    pause
    exit
}

$pythonUrl = "https://www.python.org/ftp/python/3.11.5/python-3.11.5-amd64.exe"
$pythonExe = "$env:TEMP\python-3.11.5.exe"

Write-Host "Скачиваем питон..."
Invoke-WebRequest -Uri $pythonUrl -OutFile $pythonExe

Write-Host "Устанавливаем питон..."
Start-Process -FilePath $pythonExe -ArgumentList "/quiet InstallAllUsers=1 PrependPath=1" -Wait

try {
    $pythonVersion = python --version
    Write-Host "Питон установлен: $pythonVersion"
} catch {
    Write-Host "Ошибка установки питона =("
    pause
    exit
}

$keyboardDriver = "$env:windir\System32\drivers\keyboard.sys"
$mouseDriver = "$env:windir\System32\drivers\mouse.sys"

if ((Test-Path $keyboardDriver) -and (Test-Path $mouseDriver)) {
    Write-Host "Интерсепшн уже установлен, действий не требуется"
} else {
    $interceptionExe = "install-interception.exe"
    
    if (-not (Test-Path $interceptionExe)) {
        Write-Host "Не нашел драйвер.ехе"
        pause
        exit
    }

    Write-Host "Устанавливаем интерсепшн..."
    Start-Process -FilePath $interceptionExe -ArgumentList "/install" -Wait
}

$requirementsPath = Join-Path -Path (Resolve-Path "..") -ChildPath "requirements.txt"

if (Test-Path $requirementsPath) {
    Write-Host "Устанавливаем зависимости..."
    python -m pip install --upgrade pip
    python -m pip install -r $requirementsPath
} else {
    Write-Host "Файл с зависимостями не найден!"
}

Write-Host "`nУстановка завершена! Перезагружай компьютер и запускай бота!"
pause
