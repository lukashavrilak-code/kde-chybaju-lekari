$root = Split-Path -Parent $PSScriptRoot
Set-Location $root
$python = Join-Path $root ".venv\Scripts\python.exe"
$shell = New-Object -ComObject WScript.Shell

$vystup = & $python -m pipeline skontroluj 2>&1 | Out-String
$kod = $LASTEXITCODE
if ($kod -eq 10) {
    $null = $shell.Popup("Na stránke ÚDZS je nový register.`n`n$vystup`nPostup: docs\runbook.md, Mesačná aktualizácia.", 0, "Lekári – nový register", 64)
} elseif ($kod -ne 0) {
    $null = $shell.Popup("Kontrola registra ÚDZS zlyhala (kód $kod).`n`n$vystup", 0, "Lekári – chyba kontroly", 48)
}

$zaloha = & $python -m pipeline zaloha 2>&1 | Out-String
if ($LASTEXITCODE -ne 0) {
    $null = $shell.Popup("Záloha zlyhala.`n`n$zaloha`nSpusti ju ručne: python -m pipeline zaloha", 0, "Lekári – chyba zálohy", 48)
    exit 1
}
exit $kod
