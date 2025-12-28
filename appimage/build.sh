#!/bin/bash
# Build script for S4LT AppImage
# Usage: ./build.sh
#
# Requirements:
# - Python 3.11+
# - PyInstaller
# - appimagetool (or appimage-builder)

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
VERSION="0.7.0"
APP_NAME="S4LT"
APPIMAGE_NAME="S4LT-${VERSION}-x86_64.AppImage"

echo "=== Building $APP_NAME $VERSION AppImage ==="

# Step 1: Install/update dependencies
echo "[1/5] Installing dependencies..."
cd "$PROJECT_ROOT"
pip install -e ".[dev]" --quiet

# Step 2: Run PyInstaller
echo "[2/5] Running PyInstaller..."
pyinstaller --clean --noconfirm appimage/s4lt.spec

# Step 3: Create AppDir structure
echo "[3/5] Creating AppDir..."
APPDIR="$SCRIPT_DIR/AppDir"
rm -rf "$APPDIR"
mkdir -p "$APPDIR/usr/bin"
mkdir -p "$APPDIR/usr/share/icons/hicolor/256x256/apps"
mkdir -p "$APPDIR/usr/share/applications"

# Copy PyInstaller output
cp -r "$PROJECT_ROOT/dist/s4lt/"* "$APPDIR/usr/bin/"

# Copy icons
cp "$PROJECT_ROOT/assets/s4lt-icon.png" "$APPDIR/usr/share/icons/hicolor/256x256/apps/s4lt.png"
cp "$PROJECT_ROOT/assets/s4lt-icon.png" "$APPDIR/s4lt.png"

# Copy desktop file
cp "$SCRIPT_DIR/s4lt.desktop" "$APPDIR/s4lt.desktop"
cp "$SCRIPT_DIR/s4lt.desktop" "$APPDIR/usr/share/applications/s4lt.desktop"

# Create AppRun
cat > "$APPDIR/AppRun" << 'EOF'
#!/bin/bash
SELF=$(readlink -f "$0")
HERE=${SELF%/*}
export PATH="${HERE}/usr/bin:${PATH}"
export LD_LIBRARY_PATH="${HERE}/usr/lib:${LD_LIBRARY_PATH}"
exec "${HERE}/usr/bin/s4lt" "$@"
EOF
chmod +x "$APPDIR/AppRun"

# Step 4: Download appimagetool if needed
echo "[4/5] Getting appimagetool..."
APPIMAGETOOL="$SCRIPT_DIR/appimagetool-x86_64.AppImage"
if [ ! -f "$APPIMAGETOOL" ]; then
    wget -q "https://github.com/AppImage/AppImageKit/releases/download/continuous/appimagetool-x86_64.AppImage" -O "$APPIMAGETOOL"
    chmod +x "$APPIMAGETOOL"
fi

# Step 5: Build AppImage
echo "[5/5] Building AppImage..."
cd "$SCRIPT_DIR"
ARCH=x86_64 "$APPIMAGETOOL" --no-appstream AppDir "$PROJECT_ROOT/dist/$APPIMAGE_NAME"

echo ""
echo "=== Build complete ==="
echo "Output: dist/$APPIMAGE_NAME"
echo ""
echo "To test:"
echo "  chmod +x dist/$APPIMAGE_NAME"
echo "  ./dist/$APPIMAGE_NAME"
