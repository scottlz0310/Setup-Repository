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

        # インストールを試行
        Write-Host "uvのインストールを試行します..." -ForegroundColor Yellow
        irm https://astral.sh/uv/install.ps1 | iex

        # 再度確認
        if (Test-Path $uvExe) {
            Write-Host "✅ uvのインストールが成功しました" -ForegroundColor Green
        } else {
            throw "uvのインストールに失敗しました"
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
