#!/bin/bash
set -e

echo "Cleaning previous builds..."
rm -rf dist/ build/ *.egg-info

echo "Building package..."
python -m build

echo "Build complete! Files in dist/:"
ls -lh dist/

echo ""
echo "Uploading to PyPI..."
twine upload dist/*

echo ""
echo "✓ Successfully built and uploaded to PyPI!"