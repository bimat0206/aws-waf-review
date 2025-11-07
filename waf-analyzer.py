#!/usr/bin/env python3
"""
AWS WAF Security Analysis Tool - Launcher Script

This wrapper script ensures the src/ directory is in the Python path
before importing and running the main application.
"""

import sys
from pathlib import Path

# Add src directory to Python path
src_dir = Path(__file__).parent / 'src'
sys.path.insert(0, str(src_dir))

# Import and run the main application
from main import main

if __name__ == '__main__':
    sys.exit(main())
