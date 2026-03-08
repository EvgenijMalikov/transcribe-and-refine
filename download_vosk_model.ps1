# Vosk model download helper
# Usage: .\download_vosk_model.ps1 [language] [small|full]
# Example: .\download_vosk_model.ps1 ru full

[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$OutputEncoding = [System.Text.Encoding]::UTF8

param(
    [string]$Language = "ru",
    [string]$ModelSize = "small"
)

Write-Host "=== Vosk Model Installation ===" -ForegroundColor Cyan
Write-Host "Language: $Language" -ForegroundColor Cyan

# Supported model catalog
$Models = @{
    "ru_small" = @{
        Name = "vosk-model-small-ru-0.22"
        Url = "https://alphacephei.com/vosk/models/vosk-model-small-ru-0.22.zip"
        Size = "45 MB"
    }
    "ru_full" = @{
        Name = "vosk-model-ru-0.42"
        Url = "https://alphacephei.com/vosk/models/vosk-model-ru-0.42.zip"
        Size = "1.8 GB"
    }
    "en_small" = @{
        Name = "vosk-model-small-en-us-0.15"
        Url = "https://alphacephei.com/vosk/models/vosk-model-small-en-us-0.15.zip"
        Size = "40 MB"
    }
    "en_full" = @{
        Name = "vosk-model-en-us-0.22"
        Url = "https://alphacephei.com/vosk/models/vosk-model-en-us-0.22.zip"
        Size = "1.8 GB"
    }
    "es_full" = @{
        Name = "vosk-model-es-0.42"
        Url = "https://alphacephei.com/vosk/models/vosk-model-es-0.42.zip"
        Size = "1.4 GB"
    }
    "fr_full" = @{
        Name = "vosk-model-fr-0.22"
        Url = "https://alphacephei.com/vosk/models/vosk-model-fr-0.22.zip"
        Size = "1.4 GB"
    }
    "de_full" = @{
        Name = "vosk-model-de-0.21"
        Url = "https://alphacephei.com/vosk/models/vosk-model-de-0.21.zip"
        Size = "1.8 GB"
    }
    "zh_full" = @{
        Name = "vosk-model-cn-0.22"
        Url = "https://alphacephei.com/vosk/models/vosk-model-cn-0.22.zip"
        Size = "1.3 GB"
    }
}

$ModelKey = "${Language}_$(if ($ModelSize -eq 'small') {'small'} else {'full'})"
$ModelInfo = $Models[$ModelKey]

if (-not $ModelInfo) {
    Write-Host "Error: Model not found for language '$Language' and size '$ModelSize'" -ForegroundColor Red
    Write-Host "Available combinations:" -ForegroundColor Yellow
    Write-Host "  ru small, ru full" -ForegroundColor Yellow
    Write-Host "  en small, en full" -ForegroundColor Yellow
    Write-Host "  es full, fr full, de full, zh full" -ForegroundColor Yellow
    exit 1
}

$ModelName = $ModelInfo.Name
$ModelUrl = $ModelInfo.Url
Write-Host "Selected: $ModelName ($($ModelInfo.Size))" -ForegroundColor Green

$ZipFile = "vosk-model-temp.zip"
$TargetDir = "vosk-model\$Language"

# Create vosk-model directory if it does not exist
if (-not (Test-Path "vosk-model")) {
    New-Item -ItemType Directory -Path "vosk-model" | Out-Null
}

# Check whether a model for the language is already installed
if (Test-Path $TargetDir) {
    Write-Host "A model for language '$Language' is already installed" -ForegroundColor Yellow
    $Response = Read-Host "Do you want to reinstall? (y/n)"
    if ($Response -ne "y") {
        Write-Host "Installation cancelled" -ForegroundColor Yellow
        exit
    }
    Remove-Item -Recurse -Force $TargetDir
}

# Download
Write-Host "`nDownloading model..." -ForegroundColor Cyan
try {
    Invoke-WebRequest -Uri $ModelUrl -OutFile $ZipFile
    Write-Host "Model downloaded successfully" -ForegroundColor Green
} catch {
    Write-Host "Download error: $_" -ForegroundColor Red
    exit 1
}

# Extract
Write-Host "`nExtracting archive..." -ForegroundColor Cyan
try {
    Expand-Archive -Path $ZipFile -DestinationPath "." -Force
    Write-Host "Archive extracted" -ForegroundColor Green
} catch {
    Write-Host "Extraction error: $_" -ForegroundColor Red
    Remove-Item $ZipFile -ErrorAction SilentlyContinue
    exit 1
}

# Move the extracted model into the language-specific folder
Write-Host "`nSetting up model..." -ForegroundColor Cyan
try {
    if (Test-Path $ModelName) {
        Move-Item -Path $ModelName -Destination $TargetDir
        Write-Host "Model installed in '$TargetDir'" -ForegroundColor Green
    } else {
        Write-Host "Error: folder $ModelName not found" -ForegroundColor Red
        exit 1
    }
} catch {
    Write-Host "Move error: $_" -ForegroundColor Red
    exit 1
}

# Clean up
Remove-Item $ZipFile -ErrorAction SilentlyContinue

Write-Host "`n=== Installation completed successfully! ===" -ForegroundColor Green
Write-Host "Model location: $TargetDir/" -ForegroundColor Cyan
Write-Host "Language: $Language" -ForegroundColor Cyan
Write-Host "This folder is already in .gitignore and won't be committed to Git" -ForegroundColor Yellow
Write-Host "`nTo install models for other languages:" -ForegroundColor Yellow
Write-Host "  .\download_vosk_model.ps1 en full" -ForegroundColor White
Write-Host "  .\download_vosk_model.ps1 es full" -ForegroundColor White
Write-Host "  .\download_vosk_model.ps1 zh full" -ForegroundColor White