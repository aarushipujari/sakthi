"""
config.py - Central Configuration Constants for Vulcan Melt-OS
Single source of truth for exchange rates, optimizer build versioning, and environment paths.
"""

import os

DEFAULT_FX_RATE = 84.0  # USD to INR standard conversion rate
OPTIMIZER_VERSION = "2.1.0-scipy-highs"  # LP engine version for replay verification
