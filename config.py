"""
Configuration settings for SOX Dashboard
"""
import os
from pathlib import Path

# Application Settings
APP_TITLE = "SOX Controls Executive Report"
APP_LAYOUT = "wide"

# Database Settings
DB_DIR = Path(os.getenv("DB_DIR", "data"))
DB_NAME = os.getenv("DB_NAME", "sox.db")
DB_PATH = DB_DIR / DB_NAME
TABLE_NAME = "controls"

# Logging Settings
LOG_DIR = Path(os.getenv("LOG_DIR", "logs"))
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
LOG_FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'

# File Upload Limits
MAX_FILE_SIZE_MB = int(os.getenv("MAX_FILE_SIZE_MB", 50))
MAX_ROWS = int(os.getenv("MAX_ROWS", 100000))

# Excel Column Names
EXPECTED_COLUMNS = [
    "IT Solution",
    "MICS ID",
    "BU Country/Owner",
    "Zone",
    "Control Owner",
    "Control Tester",
    "Control Reviewer",
    "ControlExecutor (ZCM Lookup) (MICS_ZonalControlMaster)",
    "Control Status",
    "Test Conclusion (OE1)",
    "Test Conclusion (OE2)",
    "Test Conclusion (YE)"
]

# Theme Colors (Blue Corporate)
THEME_COLORS = {
    "background": "#0d1117",
    "text": "#c9d1d9",
    "primary": "#2f81f7",
    "sidebar": "#161b22",
    "effective": "#2ea043",
    "ineffective": "#f85149",
    "not_tested": "#8b949e"
}
