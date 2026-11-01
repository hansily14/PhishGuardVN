if (Test-Path ".\PhishGuardVN_Weeks5_8\phishguard\create_admin.py") {
    cd ".\PhishGuardVN_Weeks5_8"
}

if (Test-Path ".\phishguard\create_admin.py") {
    py -m phishguard.create_admin
} else {
    Write-Host "Chưa đúng thư mục mã nguồn. Các mục hiện có:"
    Get-ChildItem -Name
}