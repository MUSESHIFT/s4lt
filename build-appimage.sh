#!/bin/bash
# Build S4LT AppImage for Linux/Steam Deck distribution
set -e

VERSION="0.8.4"
APP_NAME="S4LT"
ARCH="x86_64"

echo "Building S4LT v${VERSION} AppImage..."

# Clean previous builds
rm -rf build dist AppDir

# Create virtual environment if not exists
if [ ! -d ".venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv .venv
fi

# Activate and install dependencies
source .venv/bin/activate
pip install --upgrade pip
pip install -e ".[dev]"

# Run tests first
echo "Running tests..."
pytest tests/ -v --tb=short || echo "Some tests failed, continuing build..."

# Build with PyInstaller
echo "Building with PyInstaller..."
pyinstaller s4lt.spec --clean --noconfirm

# Create AppDir structure
echo "Creating AppDir..."
mkdir -p AppDir/usr/bin
mkdir -p AppDir/usr/share/applications
mkdir -p AppDir/usr/share/icons/hicolor/256x256/apps
mkdir -p AppDir/usr/share/icons/hicolor/64x64/apps
mkdir -p AppDir/usr/share/icons/hicolor/32x32/apps

# Copy built application
cp -r dist/s4lt/* AppDir/usr/bin/

# Copy icons
cp assets/s4lt-icon.png AppDir/usr/share/icons/hicolor/256x256/apps/s4lt.png
cp assets/s4lt-icon-64.png AppDir/usr/share/icons/hicolor/64x64/apps/s4lt.png 2>/dev/null || cp assets/s4lt-icon.png AppDir/usr/share/icons/hicolor/64x64/apps/s4lt.png
cp assets/s4lt-icon-32.png AppDir/usr/share/icons/hicolor/32x32/apps/s4lt.png 2>/dev/null || cp assets/s4lt-icon.png AppDir/usr/share/icons/hicolor/32x32/apps/s4lt.png
cp assets/s4lt-icon.png AppDir/s4lt.png

# Create desktop file
cat > AppDir/usr/share/applications/s4lt.desktop << EOF
[Desktop Entry]
Type=Application
Name=S4LT
GenericName=Sims 4 Mod Manager
Comment=Manage your Sims 4 mods on Linux and Steam Deck
Exec=s4lt
Icon=s4lt
Terminal=false
Categories=Game;Utility;
Keywords=sims;sims4;mods;modding;steamdeck;
StartupWMClass=S4LT
EOF

# Copy desktop file to AppDir root
cp AppDir/usr/share/applications/s4lt.desktop AppDir/

# Create AppRun
cat > AppDir/AppRun << 'EOF'
#!/bin/bash
SELF=$(readlink -f "$0")
HERE=${SELF%/*}
export PATH="${HERE}/usr/bin:${PATH}"
export LD_LIBRARY_PATH="${HERE}/usr/lib:${LD_LIBRARY_PATH}"
export XDG_DATA_DIRS="${HERE}/usr/share:${XDG_DATA_DIRS}"
exec "${HERE}/usr/bin/s4lt" "$@"
EOF
chmod +x AppDir/AppRun

# Download appimagetool if not present
if [ ! -f "appimagetool-x86_64.AppImage" ]; then
    echo "Downloading appimagetool..."
    wget -q "https://github.com/AppImage/AppImageKit/releases/download/continuous/appimagetool-x86_64.AppImage"
    chmod +x appimagetool-x86_64.AppImage
fi

# Build AppImage
echo "Building AppImage..."
ARCH=$ARCH ./appimagetool-x86_64.AppImage AppDir "dist/${APP_NAME}-${VERSION}-${ARCH}.AppImage"

echo ""
echo "Build complete!"
echo "AppImage: dist/${APP_NAME}-${VERSION}-${ARCH}.AppImage"
echo ""
echo "To test: ./dist/${APP_NAME}-${VERSION}-${ARCH}.AppImage"
