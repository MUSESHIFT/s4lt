#!/usr/bin/env python3
"""Simple CLI to test package reading.

Usage:
    python -m s4lt.cli.package_info <path_to_package>
"""

import sys
from pathlib import Path
from collections import Counter

from s4lt.core import Package, DBPFError


def main():
    if len(sys.argv) < 2:
        print("Usage: python -m s4lt.cli.package_info <package_path>")
        sys.exit(1)

    path = Path(sys.argv[1])

    if not path.exists():
        print(f"Error: File not found: {path}")
        sys.exit(1)

    try:
        with Package.open(path) as pkg:
            print(f"Package: {path.name}")
            print(f"Version: {pkg.version[0]}.{pkg.version[1]}")
            print(f"Resources: {len(pkg)}")
            print()

            # Count by type
            type_counts = Counter(r.type_name for r in pkg.resources)

            print("Resource Types:")
            for type_name, count in type_counts.most_common():
                print(f"  {type_name}: {count}")
            print()

            # List first 10 resources
            print("First 10 Resources:")
            for i, resource in enumerate(pkg.resources[:10]):
                print(f"  [{i}] {resource}")

            if len(pkg.resources) > 10:
                print(f"  ... and {len(pkg.resources) - 10} more")

            # Try extracting first resource
            if pkg.resources:
                print()
                print("Testing extraction of first resource...")
                r = pkg.resources[0]
                try:
                    data = r.extract()
                    print(f"  Extracted {len(data)} bytes")
                    if r.type_name == "Tuning" and data[:5] == b"<?xml":
                        print(f"  Preview: {data[:100].decode('utf-8', errors='replace')}...")
                except Exception as e:
                    print(f"  Extraction failed: {e}")

    except DBPFError as e:
        print(f"Error reading package: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
