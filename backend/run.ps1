# Jharkhand Chatbot - Multi-Server Startup Script
# This script starts all 4 servers concurrently and displays their logs

Write-Host "Starting Jharkhand Chatbot Servers..." -ForegroundColor Green
Write-Host "===============================================" -ForegroundColor Cyan

# Function to start a server with colored output
function Start-Server {
    param(
        [string]$Name,
        [string]$Command,
        [string]$Color
    )
    
    Write-Host "Starting $Name server..." -ForegroundColor $Color
    
    # Start the process in background
    $process = Start-Process -FilePath "powershell" -ArgumentList "-Command", "& { $Command }" -PassThru -NoNewWindow
    
    # Start a job to monitor the process output
    Start-Job -Name $Name -ScriptBlock {
        param($proc, $serverName, $color)
        
        # Wait for the process to start and begin output
        Start-Sleep -Seconds 2
        
        # Monitor process output (this is a simplified approach)
        while (!$proc.HasExited) {
            Start-Sleep -Seconds 1
        }
    } -ArgumentList $process, $Name, $Color | Out-Null
    
    return $process
}

# Start all servers
$orchestrator = Start-Server -Name "Orchestrator" -Command "uvicorn orchestrator.app:app --host 127.0.0.1 --port 9000 --reload" -Color "Red"
$level0 = Start-Server -Name "Level0" -Command "uvicorn level0.app:app --host 127.0.0.1 --port 8000 --reload" -Color "Blue"
$level1 = Start-Server -Name "Level1" -Command "uvicorn level1.app:app --host 127.0.0.1 --port 8001 --reload" -Color "Yellow"
$level2 = Start-Server -Name "Level2" -Command "uvicorn level2.app:app --host 127.0.0.1 --port 8002 --reload" -Color "Magenta"

Write-Host "`nAll servers started successfully!" -ForegroundColor Green
Write-Host "===============================================" -ForegroundColor Cyan
Write-Host "Server URLs:" -ForegroundColor White
Write-Host "   Orchestrator: http://127.0.0.1:9000" -ForegroundColor Red
Write-Host "   Level 0:      http://127.0.0.1:8000" -ForegroundColor Blue
Write-Host "   Level 1:      http://127.0.0.1:8001" -ForegroundColor Yellow
Write-Host "   Level 2:      http://127.0.0.1:8002" -ForegroundColor Magenta
Write-Host "===============================================" -ForegroundColor Cyan
Write-Host "`nServer logs will appear below. Press Ctrl+C to stop all servers." -ForegroundColor White
Write-Host ""

# Function to display logs with color coding
function Show-Logs {
    param($process, $serverName, $color)
    
    # Create a simple log display
    $logPrefix = "[$serverName]"
    Write-Host "$logPrefix Server is running on PID: $($process.Id)" -ForegroundColor $color
}

# Display initial status
Show-Logs -process $orchestrator -serverName "ORCHESTRATOR" -color "Red"
Show-Logs -process $level0 -serverName "LEVEL-0" -color "Blue"
Show-Logs -process $level1 -serverName "LEVEL-1" -color "Yellow"
Show-Logs -process $level2 -serverName "LEVEL-2" -color "Magenta"

Write-Host "`nMonitoring servers... (Press Ctrl+C to stop all)" -ForegroundColor Green

# Wait for user interruption
try {
    while ($true) {
        # Check if any server has stopped
        if ($orchestrator.HasExited -or $level0.HasExited -or $level1.HasExited -or $level2.HasExited) {
            Write-Host "`nWARNING: One or more servers have stopped unexpectedly!" -ForegroundColor Yellow
            break
        }
        Start-Sleep -Seconds 5
    }
} catch {
    Write-Host "`nStopping all servers..." -ForegroundColor Red
}

# Cleanup function
function Stop-AllServers {
    Write-Host "`nShutting down all servers..." -ForegroundColor Red
    
    try {
        if (!$orchestrator.HasExited) { $orchestrator.Kill() }
        if (!$level0.HasExited) { $level0.Kill() }
        if (!$level1.HasExited) { $level1.Kill() }
        if (!$level2.HasExited) { $level2.Kill() }
        
        # Clean up jobs
        Get-Job | Remove-Job -Force
        
        Write-Host "All servers stopped successfully!" -ForegroundColor Green
    } catch {
        Write-Host "WARNING: Error stopping servers: $($_.Exception.Message)" -ForegroundColor Yellow
    }
}

# Set up cleanup on script exit
$null = Register-EngineEvent -SourceIdentifier PowerShell.Exiting -Action { Stop-AllServers }

# Wait for processes to complete or user interruption
try {
    Wait-Process -Id $orchestrator.Id, $level0.Id, $level1.Id, $level2.Id -ErrorAction SilentlyContinue
} catch {
    # User interrupted or processes stopped
}

Stop-AllServers