# NPITS Backup Script
$ErrorActionPreference = "Stop"

$ProjectDir = "c:\inetpub\wwwroot\NPITS"
$BackupDir = Join-Path $ProjectDir "backups"
$Timestamp = Get-Date -Format "yyyy-MM-dd_HH-mm"
$ZipName = "NPITS_backup_$Timestamp.zip"
$ZipPath = Join-Path $BackupDir $ZipName

Write-Host "Starting backup of $ProjectDir to $ZipPath..."

# Ensure the backups directory exists
if (-not (Test-Path $BackupDir)) {
    New-Item -ItemType Directory -Path $BackupDir | Out-Null
}

# Define items to exclude
$Excludes = @(
    "backups",
    ".git",
    "__pycache__",
    ".gemini",
    "venv",
    ".env", # Optional: can be sensitive, but sometimes we want it. For now, I'll exclude it as a precaution.
    "staticfiles",
    "wfastcgi.log" # Large logs
)

# Use Resolve-Path to get absolute paths for filtering
$Children = Get-ChildItem -Path $ProjectDir -Exclude $Excludes

Write-Host "Compressing files..."
Compress-Archive -Path $Children.FullName -DestinationPath $ZipPath -Force

Write-Host "Backup completed successfully: $ZipPath"
