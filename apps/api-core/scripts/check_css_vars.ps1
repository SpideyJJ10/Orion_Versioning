$cssRoot = 'c:\Users\JJ\Desktop\Zafiro\TizonV2\Tizon_MVP_Version_2\frontend\css'
$files = Get-ChildItem -Path $cssRoot -Recurse -Include *.css | Where-Object { $_.FullName -notmatch '\.bak$' }
$defined = New-Object 'System.Collections.Generic.HashSet[string]'
$used = New-Object 'System.Collections.Generic.HashSet[string]'

foreach ($f in $files) {
  $c = Get-Content -Raw $f.FullName
  foreach ($m in [regex]::Matches($c, '--[a-zA-Z][a-zA-Z0-9-]*\s*:')) {
    [void]$defined.Add($m.Value.TrimEnd(':', ' ', "`t"))
  }
  foreach ($m in [regex]::Matches($c, 'var\((--[a-zA-Z][a-zA-Z0-9-]*)')) {
    [void]$used.Add($m.Groups[1].Value)
  }
}

$orphans = $used | Where-Object { -not $defined.Contains($_) } | Sort-Object
Write-Host "ORPHAN VARIABLES (used but not defined):" -ForegroundColor Yellow
if ($orphans.Count -eq 0) {
  Write-Host "  (none)" -ForegroundColor Green
} else {
  $orphans | ForEach-Object { Write-Host "  - $_" -ForegroundColor Red }
}
