#!/bin/bash
# Build on a native macOS runner; no Homebrew runtime libraries are shipped.
set -euo pipefail
cd "$(dirname "$0")"
[[ "$(uname -s)" == Darwin ]] || { echo 'This build requires macOS.' >&2; exit 1; }
ARCH="$(uname -m)"
[[ "$ARCH" == arm64 || "$ARCH" == x86_64 ]]
export MACOSX_DEPLOYMENT_TARGET=15.0
ROOT="$PWD"
BUILD="$ROOT/build/macos-$ARCH"
PREFIX="$BUILD/prefix"
mkdir -p "$BUILD" "$PREFIX" "$ROOT/dist" "$BUILD/notices"

FFMPEG_REF=140fd653aed8cad774f991ba083e2d01e86420c7
X264_REF=c24e06c2e184345ceb33eb20a15d1024d9fd3497
NODE_VERSION=22.17.0
NODE_ARCH=arm64
[[ "$ARCH" != x86_64 ]] || NODE_ARCH=x64
curl -fL --retry 3 "https://github.com/FFmpeg/FFmpeg/archive/$FFMPEG_REF.tar.gz" -o "$BUILD/ffmpeg-source.tar.gz"
curl -fL --retry 3 "https://github.com/mirror/x264/archive/$X264_REF.tar.gz" -o "$BUILD/x264-source.tar.gz"
tar -xzf "$BUILD/ffmpeg-source.tar.gz" -C "$BUILD"
tar -xzf "$BUILD/x264-source.tar.gz" -C "$BUILD"
(
  cd "$BUILD/x264-$X264_REF"
  ./configure --prefix="$PREFIX" --enable-static --enable-pic --disable-cli --disable-opencl
  make -j"$(sysctl -n hw.logicalcpu)"
  make install
)
(
  cd "$BUILD/FFmpeg-$FFMPEG_REF"
  PKG_CONFIG_PATH="$PREFIX/lib/pkgconfig" ./configure --prefix="$PREFIX" \
    --disable-autodetect --disable-shared --enable-static --enable-gpl --enable-libx264 \
    --enable-securetransport --enable-zlib --enable-bzlib --enable-iconv --extra-libs=-liconv \
    --disable-doc --disable-debug --disable-ffplay
  make -j"$(sysctl -n hw.logicalcpu)"
  make install
)
curl -fL --retry 3 "https://nodejs.org/dist/v$NODE_VERSION/node-v$NODE_VERSION-darwin-$NODE_ARCH.tar.gz" -o "$BUILD/node-v$NODE_VERSION-darwin-$NODE_ARCH.tar.gz"
curl -fL --retry 3 "https://nodejs.org/dist/v$NODE_VERSION/SHASUMS256.txt" -o "$BUILD/SHASUMS256.txt"
(
  cd "$BUILD"
  grep " node-v$NODE_VERSION-darwin-$NODE_ARCH.tar.gz$" SHASUMS256.txt | shasum -a 256 -c -
  tar -xzf "node-v$NODE_VERSION-darwin-$NODE_ARCH.tar.gz"
)
cp "$BUILD/node-v$NODE_VERSION-darwin-$NODE_ARCH/bin/node" "$PREFIX/bin/node"
cp "$BUILD/node-v$NODE_VERSION-darwin-$NODE_ARCH/LICENSE" "$BUILD/notices/Node-LICENSE.txt"
cp "$BUILD/FFmpeg-$FFMPEG_REF/COPYING.GPLv2" "$BUILD/notices/FFmpeg-LICENSE.txt"
cp "$BUILD/x264-$X264_REF/COPYING" "$BUILD/notices/x264-LICENSE.txt"
"$PREFIX/bin/ffmpeg" -buildconf > "$BUILD/notices/FFmpeg-build.txt" 2>&1
cp build-macos.sh "$BUILD/notices/"
cp "$BUILD/ffmpeg-source.tar.gz" "dist/ffmpeg-macos-source.tar.gz"
cp "$BUILD/x264-source.tar.gz" "dist/x264-macos-source.tar.gz"

# Integration tests must use the same encoder that will ship in the application.
PATH="$PREFIX/bin:$PATH" python -m pytest tests -q
node --test tests/*.test.mjs

# PyInstaller collects the native Cocoa backend and all yt-dlp runtime modules.
python -m PyInstaller --noconfirm --clean --onedir --windowed \
  --name 'YouTube Clipper' --target-arch "$ARCH" --icon 'installer/YouTube Clipper.icns' \
  --osx-bundle-identifier 'com.matlukowski.youtubeclipper' \
  --collect-all yt_dlp --collect-all yt_dlp_ejs --collect-all webview \
  --add-data 'web:web' --add-data "$BUILD/notices:third_party" \
  --add-binary "$PREFIX/bin/node:tools" --add-binary "$PREFIX/bin/ffmpeg:tools" desktop.py
APP="$ROOT/dist/YouTube Clipper.app"
/usr/libexec/PlistBuddy -c 'Set :CFBundleShortVersionString 1.1.6' "$APP/Contents/Info.plist"
/usr/libexec/PlistBuddy -c 'Set :CFBundleVersion 1.1.6' "$APP/Contents/Info.plist"
/usr/libexec/PlistBuddy -c 'Set :LSMinimumSystemVersion 15.0' "$APP/Contents/Info.plist"
codesign --force --deep --sign - "$APP"
codesign --verify --deep --strict "$APP"

# Check the actual installed bundle with only system utilities on PATH.
REPORT="$BUILD/smoke.json"
PATH=/usr/bin:/bin:/usr/sbin:/sbin "$APP/Contents/MacOS/YouTube Clipper" --smoke-test "$REPORT" &
APP_PID=$!
for ((i=0; i<180; i++)); do
  kill -0 "$APP_PID" 2>/dev/null || break
  sleep 1
done
if kill -0 "$APP_PID" 2>/dev/null; then
  kill "$APP_PID"
  echo 'Installed app smoke test timed out.' >&2
  exit 1
fi
wait "$APP_PID"
cat "$REPORT"
python -c 'import json,sys; assert json.load(open(sys.argv[1]))["ok"]' "$REPORT"

STAGE="$BUILD/dmg"
mkdir -p "$STAGE"
ditto "$APP" "$STAGE/YouTube Clipper.app"
ln -s /Applications "$STAGE/Applications"
cp installer/macOS-README.txt "$STAGE/Przeczytaj przed instalacja.txt"
hdiutil create -volname 'YouTube Clipper' -srcfolder "$STAGE" -ov -format UDZO "dist/YouTube-Clipper-macOS-$ARCH.dmg"
hdiutil verify "dist/YouTube-Clipper-macOS-$ARCH.dmg"
