# Windows環境でのuv設定スクリプト
# このスクリプトは、GitHub ActionsのWindows環境でuvを正しく設定します

param(
    [switch]$Verbose = $false
)

# エラー時に停止
$ErrorActionPreference = "Stop"

# 詳細出力の設定
if ($Verbose) {
    $VerbosePreference = "Continue"
}

Write-Host "=== Windows環境でのuv設定を開始します ===" -ForegroundColor Green

try {
    # 現在のPATHを表示
    Write-Host "現在のPATH:" -ForegroundColor Yellow
    $env:PATH -split ';' | ForEach-Object { Write-Host "  $_" }

    # uvのインストールパスを確認
    $uvPath = "$env:USERPROFILE\.cargo\bin"
    $uvExe = "$uvPath\uv.exe"

    Write-Host "uvインストールパス: $uvPath" -ForegroundColor Yellow
    Write-Host "uv実行ファイル: $uvExe" -ForegroundColor Yellow

    # uvの存在確認
    if (Test-Path $uvExe) {
        Write-Host "✅ uv実行ファイルが見つかりました" -ForegroundColor Green

        # バージョン確認
        $uvVersion = & $uvExe --version 2>&1
        Write-Host "uvバージョン: $uvVersion" -ForegroundColor Green

    } else {
        Write-Host "❌ uv実行ファイルが見つかりません" -ForegroundColor Red

        # インストールを試行（複数の方法を試す）
        Write-Host "uvのインストールを試行します..." -ForegroundColor Yellow
        
        $installSuccess = $false
        
        # 方法1: 公式インストーラー
        try {
            Write-Host "方法1: 公式インストーラーを使用" -ForegroundColor Yellow
            irm https://astral.sh/uv/install.ps1 | iex
            Start-Sleep -Seconds 3
            if (Test-Path $uvExe) {
                $installSuccess = $true
                Write-Host "✅ 公式インストーラーでのインストールが成功" -ForegroundColor Green
            }
        } catch {
            Write-Host "⚠️  公式インストーラーでのインストールに失敗: $_" -ForegroundColor Yellow
        }
        
        # 方法2: pipでのインストール
        if (-not $installSuccess) {
            try {
                Write-Host "方法2: pipでのインストールを試行" -ForegroundColor Yellow
                python -m pip install uv --upgrade
                
                # pipでインストールした場合のパスを確認
                $pipUvPath = python -c "import uv; print(uv.__file__.replace('__init__.py', '').replace('\\', '/'))" 2>$null
                if ($pipUvPath) {
                    Write-Host "✅ pipでのインストールが成功" -ForegroundColor Green
                    $installSuccess = $true
                }
            } catch {
                Write-Host "⚠️  pipでのインストールに失敗: $_" -ForegroundColor Yellow
            }
        }
        
        # 方法3: GitHub Releasesから直接ダウンロード
        if (-not $installSuccess) {
            try {
                Write-Host "方法3: GitHub Releasesから直接ダウンロード" -ForegroundColor Yellow
                $downloadUrl = "https://github.com/astral-sh/uv/releases/latest/download/uv-x86_64-pc-windows-msvc.zip"
                $tempZip = "$env:TEMP\uv.zip"
                $extractPath = "$env:TEMP\uv-extract"
                
                Invoke-WebRequest -Uri $downloadUrl -OutFile $tempZip
                Expand-Archive -Path $tempZip -DestinationPath $extractPath -Force
                
                # 抽出したファイルをコピー
                $extractedUv = Get-ChildItem -Path $extractPath -Name "uv.exe" -Recurse | Select-Object -First 1
                if ($extractedUv) {
                    $sourcePath = Join-Path $extractPath $extractedUv.FullName
                    New-Item -ItemType Directory -Path $uvPath -Force | Out-Null
                    Copy-Item -Path $sourcePath -Destination $uvExe -Force
                    
                    if (Test-Path $uvExe) {
                        Write-Host "✅ GitHub Releasesからのダウンロードが成功" -ForegroundColor Green
                        $installSuccess = $true
                    }
                }
                
                # 一時ファイルを清理
                Remove-Item -Path $tempZip -Force -ErrorAction SilentlyContinue
                Remove-Item -Path $extractPath -Recurse -Force -ErrorAction SilentlyContinue
                
            } catch {
                Write-Host "⚠️  GitHub Releasesからのダウンロードに失敗: $_" -ForegroundColor Yellow
            }
        }
        
        if (-not $installSuccess) {
            throw "uvのインストールに失敗しました（すべての方法で失敗）"
        }
    }

    # PATHにuvを追加（現在のセッション用）
    if ($env:PATH -notlike "*$uvPath*") {
        Write-Host "現在のセッションのPATHにuvを追加します..." -ForegroundColor Yellow
        $env:PATH = "$uvPath;$env:PATH"
        Write-Host "✅ PATHにuvを追加しました" -ForegroundColor Green
    } else {
        Write-Host "✅ uvは既にPATHに含まれています" -ForegroundColor Green
    }

    # GitHub Actions環境の場合、GITHUB_PATHに追加
    if ($env:GITHUB_ACTIONS -eq "true") {
        Write-Host "GitHub Actions環境でのPATH設定..." -ForegroundColor Yellow

        if ($env:GITHUB_PATH) {
            Add-Content -Path $env:GITHUB_PATH -Value $uvPath -Encoding UTF8
            Write-Host "✅ GITHUB_PATHにuvパスを追加しました" -ForegroundColor Green
        } else {
            Write-Host "⚠️  GITHUB_PATH環境変数が見つかりません" -ForegroundColor Yellow
        }
    }

    # 最終確認
    Write-Host "最終確認を実行します..." -ForegroundColor Yellow

    # uvコマンドの実行テスト
    try {
        $testResult = uv --version 2>&1
        Write-Host "✅ uvコマンドの実行テスト成功: $testResult" -ForegroundColor Green
    } catch {
        Write-Host "❌ uvコマンドの実行テスト失敗: $_" -ForegroundColor Red

        # 直接パスを指定して実行
        try {
            $testResult = & $uvExe --version 2>&1
            Write-Host "✅ 直接パス指定でのuv実行成功: $testResult" -ForegroundColor Green

            # エイリアスを作成
            Set-Alias -Name uv -Value $uvExe -Scope Global
            Write-Host "✅ uvエイリアスを作成しました" -ForegroundColor Green

        } catch {
            throw "uvの実行に失敗しました: $_"
        }
    }

    # Python環境の確認
    Write-Host "Python環境の確認..." -ForegroundColor Yellow
    try {
        $pythonVersion = python --version 2>&1
        Write-Host "Pythonバージョン: $pythonVersion" -ForegroundColor Green
    } catch {
        Write-Host "⚠️  Pythonコマンドが見つかりません: $_" -ForegroundColor Yellow
    }

    Write-Host "=== Windows環境でのuv設定が完了しました ===" -ForegroundColor Green

} catch {
    Write-Host "❌ エラーが発生しました: $_" -ForegroundColor Red
    Write-Host "スタックトレース:" -ForegroundColor Red
    Write-Host $_.ScriptStackTrace -ForegroundColor Red
    exit 1
} finally {
    Write-Host "=== スクリプト実行終了 ===" -ForegroundColor Cyan
}
