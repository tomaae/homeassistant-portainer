#!/usr/bin/env python3
"""
VS Code Test Discovery Helper

Dieses Script hilft VS Code dabei, alle Tests zu finden und zu laden.
Führe es aus, wenn VS Code die Tests nicht automatisch erkennt.
"""

import subprocess
import sys
from pathlib import Path


def main():
    """Führe Test Discovery aus und zeige Ergebnisse."""
    project_root = Path(__file__).parent
    tests_dir = project_root / "tests"

    if not tests_dir.exists():
        print("❌ Tests-Verzeichnis nicht gefunden!")
        return 1

    print("🔍 Führe Test Discovery aus...")

    try:
        # Test Discovery ausführen
        result = subprocess.run(
            [sys.executable, "-m", "pytest", "--collect-only", "tests/", "-q"],
            capture_output=True,
            text=True,
            cwd=project_root,
        )

        if result.returncode == 0:
            print("✅ Test Discovery erfolgreich!")
            lines = result.stdout.strip().split("\n")
            # Zähle Tests
            test_count = len(
                [line for line in lines if "<Function" in line or "<Coroutine" in line]
            )
            print(f"📊 {test_count} Tests gefunden")

            # Zeige Test-Dateien
            print("\n📁 Test-Dateien:")
            for line in lines:
                if "<Module" in line and "test_" in line:
                    module = line.split("<Module ")[1].split(">")[0]
                    print(f"   • {module}")

            print(
                "\n💡 Tipp: Öffne VS Code Test Explorer mit Ctrl+Shift+P → 'Test: Focus on Test Explorer View'"
            )
            return 0
        else:
            print("❌ Test Discovery fehlgeschlagen!")
            print(result.stderr)
            return 1

    except Exception as e:
        print(f"❌ Fehler: {e}")
        return 1


if __name__ == "__main__":
    exit(main())
