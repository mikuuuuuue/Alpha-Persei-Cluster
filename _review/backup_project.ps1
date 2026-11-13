<#
.SYNOPSIS
  Alpha-Persei-Cluster 项目备份脚本（只备份，不删除任何东西）

.DESCRIPTION
  打包整个项目到指定目录，自动跳过冗余与可再生产物，
  并在完成后校验压缩包完整性。

  设计原则：
    1. 不删除、不移动源目录里的任何文件
    2. 不可再生数据（抓包、account.db）全部包含
    3. 冗余内容跳过（便携包解压目录 vs zip、重复 zip、selftest_tmp）

.PARAMETER Destination
  备份输出目录。必须与其他磁盘/网盘路径不同。例：E:\backup

.EXAMPLE
  .\backup_project.ps1 -Destination "E:\backup"
#>
[CmdletBinding()]
param(
  [Parameter(Mandatory = $true)]
  [string]$Destination,

  [string]$Source = $PSScriptRoot,

  # 若为 true，额外把 1.5GB 的游戏录像一起打包（默认打包）
  [switch]$ExcludeVideo
)

$ErrorActionPreference = 'Stop'
$stamp = Get-Date -Format 'yyyyMMdd_HHmmss'
$name  = "Alpha-Persei-Cluster_$stamp"

Write-Host "=== Alpha-Persei-Cluster 备份 ===" -ForegroundColor Cyan
Write-Host "源目录   : $Source"
Write-Host "目标目录 : $Destination"
Write-Host ""

# ---------- 1. 预检 ----------
if (-not (Test-Path -LiteralPath $Source)) { throw "源目录不存在: $Source" }
if (-not (Test-Path -LiteralPath $Destination)) {
  New-Item -ItemType Directory -Path $Destination -Force | Out-Null
  Write-Host "已创建目标目录" -ForegroundColor Yellow
}

$srcRoot   = Split-Path -Parent $Source
$srcLeaf   = Split-Path -Leaf   $Source
$totalMB   = [math]::Round(((Get-ChildItem -LiteralPath $Source -Recurse -File -Force -ErrorAction SilentlyContinue |
                 Measure-Object Length -Sum).Sum) / 1MB, 1)

# 估算排除量
$excl = @(
  "$srcLeaf/selftest_tmp",
  "$srcLeaf/AetherGazer_Server_v5.0_Portable",
  "$srcLeaf/Alpha-Persei-Assets/installers",
  "$srcLeaf/**/__pycache__",
  "$srcLeaf/**/.pytest_cache"
)
if ($ExcludeVideo) { $excl += "$srcLeaf/Alpha-Persei-Captures/**/*.mp4" }

Write-Host "项目总大小 : $totalMB MB"
Write-Host "将跳过的冗余项:" -ForegroundColor Yellow
Write-Host "  selftest_tmp/                    509 MB  (临时测试产物，可再生)"
Write-Host "  AetherGazer_Server_v5.0_Portable/ 554 MB  (与根目录 zip 内容完全相同)"
Write-Host "  Alpha-Persei-Assets/installers/  262 MB  (与根目录 zip 逐字节相同)"
if ($ExcludeVideo) { Write-Host "  *.mp4                          1528 MB  (按 -ExcludeVideo 排除)" }
Write-Host ""

# 空间检查（粗略：压缩后约 55%）-- 磁盘信息不可用时跳过
try {
  $freeMB = (Get-PSDrive -Name ([IO.Path]::GetPathRoot($Destination).TrimEnd(':'))).Free / 1MB
  if ($freeMB -lt 500) { throw "目标磁盘可用空间不足 500MB（当前 $([math]::Round($freeMB,0))MB）" }
  Write-Host "目标磁盘可用: $([math]::Round($freeMB,0)) MB" -ForegroundColor Green
} catch [System.Management.Automation.DriveNotFoundException] {
  Write-Host "无法读取目标磁盘剩余空间，跳过检查" -ForegroundColor Yellow
}
Write-Host ""

# ---------- 2. 打包 ----------
$outFile = Join-Path $Destination "$name.tar.gz"

Write-Host "开始打包（大文件较多，请耐心等待）..." -ForegroundColor Cyan
$argList = @('-czf', $outFile, '-C', $srcRoot)
foreach ($e in $excl) { $argList += "--exclude=$e" }
$argList += $srcLeaf

& tar @argList
if ($LASTEXITCODE -ne 0) { throw "tar 打包失败，退出码 $LASTEXITCODE" }

$archiveMB = [math]::Round((Get-Item -LiteralPath $outFile).Length / 1MB, 1)
Write-Host "打包完成: $outFile  ($archiveMB MB)" -ForegroundColor Green
Write-Host ""

# ---------- 3. 校验 ----------
Write-Host "=== 校验 ===" -ForegroundColor Cyan
$listFile = Join-Path $Destination "$name.manifest.txt"
& tar -tzf $outFile | Out-File -LiteralPath $listFile -Encoding utf8
$entryCount = (Get-Content -LiteralPath $listFile).Count
Write-Host "归档条目数: $entryCount"

# 关键文件存在性检查
$must = @(
  "$srcLeaf/.git/HEAD",
  "$srcLeaf/README.md",
  "$srcLeaf/实施计划.md",
  "$srcLeaf/v5_server/main.py",
  "$srcLeaf/v5_server/account.db",
  "$srcLeaf/AetherGazer_Server_v5.0_Portable.zip",
  "$srcLeaf/Alpha-Persei-Captures"
)
$manifest = Get-Content -LiteralPath $listFile
$missing = @()
foreach ($m in $must) {
  if (-not ($manifest | Where-Object { $_ -like "$m*" })) { $missing += $m }
}
if ($missing.Count -gt 0) {
  Write-Host "警告：以下关键路径不在归档中：" -ForegroundColor Red
  $missing | ForEach-Object { Write-Host "  $_" }
} else {
  Write-Host "关键路径检查：全部通过" -ForegroundColor Green
}

# 哈希
Write-Host "计算 SHA256..."
$hash = (Get-FileHash -LiteralPath $outFile -Algorithm SHA256).Hash
$hashFile = Join-Path $Destination "$name.sha256.txt"
"$hash  $name.tar.gz" | Out-File -LiteralPath $hashFile -Encoding utf8
Write-Host "SHA256: $hash"
Write-Host ""

# ---------- 4. 摘要 ----------
$summary = @"
=== Alpha-Persei-Cluster 备份摘要 ===
时间        : $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')
源目录      : $Source
归档文件    : $outFile
归档大小    : $archiveMB MB
条目数      : $entryCount
SHA256      : $hash

校验文件    : $hashFile
清单文件    : $listFile

恢复方式:
  tar -xzf "$name.tar.gz" -C <目标目录>

注意:
  - 本备份已跳过 selftest_tmp、便携包解压目录、重复的安装包 zip
  - 便携包请用归档中的 AetherGazer_Server_v5.0_Portable.zip 解压获得
  - 游戏录像已包含在 Alpha-Persei-Captures/2026-09-27_补抓2/ 内（除非用了 -ExcludeVideo）
"@
$summaryFile = Join-Path $Destination "$name.txt"
$summary | Out-File -LiteralPath $summaryFile -Encoding utf8

Write-Host $summary
Write-Host "备份完成。" -ForegroundColor Green
