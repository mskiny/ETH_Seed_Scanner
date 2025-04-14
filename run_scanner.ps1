# Run ETH_Seed_Scanner
# This script activates the virtual environment and runs the scanner

# Activate virtual environment
.\venv\Scripts\Activate

# Run scanner with arguments passed to this script
python -m app.main $args

# Keep the window open if there's an error
if ($LASTEXITCODE -ne 0) {
    Write-Host "Press any key to continue..."
    $null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
}
