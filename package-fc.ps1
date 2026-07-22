# VoxAeterna FC 打包脚本
# 用法: .\package-fc.ps1

Write-Host "[VoxAeterna] 开始打包 FC 部署包..." -ForegroundColor Cyan

 = "F:\etc\VoiceStudio\cloud\voxaeterna-fc.zip"
 = "F:\etc\VoiceStudio\cloud"

# 删除旧包
if (Test-Path ) { Remove-Item  -Force }

# 要排除的目录和文件
 = @(
    "admin\node_modules",
    "__pycache__",
    ".git",
    "*.pyc",
    "alembic"
)

# 创建 ZIP
Add-Type -AssemblyName System.IO.Compression.FileSystem
 = [System.IO.Compression.ZipFile]::Open(, [System.IO.Compression.ZipArchiveMode]::Create)

try {
    # 添加 bootstrap（必须在根目录）
     = Join-Path  "bootstrap"
    if (Test-Path ) {
        [System.IO.Compression.ZipFileExtensions]::CreateEntryFromFile(, , "bootstrap")
        Write-Host "  + bootstrap" -ForegroundColor Green
    }

    # 添加 cloud/ 目录内容（排除 node_modules、__pycache__ 等）
     = Get-ChildItem -Path  -Recurse -File | Where-Object {
         = .FullName.Replace(, "").TrimStart("\")
        .ForEach({  -notlike  }) -notcontains False
    }

    foreach ( in ) {
         = .FullName.Replace(, "").TrimStart("\")
        # 跳过 bootstrap（已添加）和 zip 本身
        if ( -eq "bootstrap" -or  -eq "voxaeterna-fc.zip") { continue }
        # 跳过 admin/node_modules
        if (.StartsWith("admin\node_modules")) { continue }
        # 跳过 __pycache__
        if ( -match "__pycache__") { continue }

         = "cloud\" + 
        try {
            [System.IO.Compression.ZipFileExtensions]::CreateEntryFromFile(, .FullName, )
        } catch {
            Write-Host "  ! 跳过: " -ForegroundColor Yellow
        }
    }
} finally {
    .Dispose()
}

 = [math]::Round((Get-Item ).Length / 1KB, 1)
Write-Host "
[VoxAeterna] 打包完成:  ( KB)" -ForegroundColor Green
Write-Host "请将此 ZIP 上传到阿里云函数计算的「通过 ZIP 包上传代码」" -ForegroundColor Yellow
