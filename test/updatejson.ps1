$TOKEN = Read-Host "Please enter your token" -AsSecureString

$headers = @{}
$headers["Authorization"] = "Bearer $TOKEN"

Invoke-WebRequest -Uri "https://api.theporndb.net/scenes?q=dorcelclub-2021-12-23-peeping-tom" -ContentType "application/json" -Headers $headers | Set-Content ./dc.json
Invoke-WebRequest -Uri "https://api.theporndb.net/scenes?q=evil-angel-2022-01-03-carmela-clutch-fabulous-anal-3-way" -ContentType "application/json" -Headers $headers | Set-Content ./ea.json
Invoke-WebRequest -Uri "https://api.theporndb.net/scenes/1678283" -ContentType "application/json" -Headers $headers | Set-Content ./ea.full.json
Invoke-WebRequest -Uri "https://api.theporndb.net/scenes?q=brazzers-exxtra-suck-suck-blow" -ContentType "application/json" -Headers $headers | Set-Content ./ssb2.json
Invoke-WebRequest -Uri "https://api.theporndb.net/movies?q=petite18.Harper%20Red&limit=25" -ContentType "application/json" -Headers $headers | Set-Content ./p18.json
