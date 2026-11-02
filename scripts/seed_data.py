"""
SIH26002 — Seed script for initial test data and corridor graph.
"""
import os
import sys

import django

# Setup django environment
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "backend"))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.development")

def main():
    django.setup()
    from django.core.management import call_command
    print("Running seed_corridor...")
    call_command("seed_corridor")
    print("Corridor seeded successfully.")

if __name__ == "__main__":
    main()
