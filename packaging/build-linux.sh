#!/usr/bin/env bash
set -euo pipefail

version="${1:-}"
output_dir="${2:-release}"
if [[ -z "$version" || "$version" == *[^0-9.]* ]]; then
  echo "Usage: $0 VERSION [OUTPUT_DIR]" >&2
  exit 2
fi

repo_root="$(cd "$(dirname "$0")/.." && pwd)"
output_dir="$(realpath -m "$output_dir")"
build_root="$(mktemp -d -t ucc-linux-build-XXXXXX)"
trap 'chmod -R u+w "$build_root" 2>/dev/null || true; find "$build_root" -depth -delete 2>/dev/null || true' EXIT

cd "$repo_root"
python3 -m PyInstaller \
  --noconfirm \
  --clean \
  --onefile \
  --name undertale-control-center \
  --distpath "$build_root/bin" \
  --workpath "$build_root/pyinstaller" \
  --specpath "$build_root" \
  --add-data "$repo_root/dist:dist" \
  --add-data "$repo_root/data:data" \
  server.py

mkdir -p "$output_dir"

portable="$build_root/undertale-control-center-v${version}-linux-x86_64"
mkdir -p "$portable"
install -m 0755 "$build_root/bin/undertale-control-center" "$portable/undertale-control-center"
install -m 0644 README.md README.ru.md LICENSE "$portable/"
tar -C "$build_root" -czf "$output_dir/undertale-control-center-v${version}-linux-x86_64.tar.gz" "$(basename "$portable")"

deb_root="$build_root/deb"
mkdir -p "$deb_root/DEBIAN" "$deb_root/opt/undertale-control-center" "$deb_root/usr/bin" \
  "$deb_root/usr/share/applications" "$deb_root/usr/share/icons/hicolor/scalable/apps" \
  "$deb_root/usr/share/doc/undertale-control-center"
install -m 0755 "$build_root/bin/undertale-control-center" "$deb_root/opt/undertale-control-center/undertale-control-center"
ln -s /opt/undertale-control-center/undertale-control-center "$deb_root/usr/bin/undertale-control-center"
install -m 0644 packaging/undertale-control-center.desktop "$deb_root/usr/share/applications/undertale-control-center.desktop"
install -m 0644 packaging/undertale-control-center.svg "$deb_root/usr/share/icons/hicolor/scalable/apps/undertale-control-center.svg"
install -m 0644 README.md README.ru.md LICENSE "$deb_root/usr/share/doc/undertale-control-center/"

cat > "$deb_root/DEBIAN/control" <<EOF
Package: undertale-control-center
Version: $version
Section: games
Priority: optional
Architecture: amd64
Depends: libc6 (>= 2.35), xdg-utils
Maintainer: ari3lYT <173036157+ari3lYT@users.noreply.github.com>
Description: Local UNDERTALE save editor and runtime dashboard
 Browser-based local manager with backups, validation, timeline, save slots,
 presets, diagnostics, and an optional live game bridge.
EOF

dpkg-deb --root-owner-group --build "$deb_root" "$output_dir/undertale-control-center_${version}_amd64.deb"

(
  cd "$output_dir"
  sha256sum \
    "undertale-control-center-v${version}-linux-x86_64.tar.gz" \
    "undertale-control-center_${version}_amd64.deb" > SHA256SUMS
)

printf 'Linux artifacts created in %s\n' "$output_dir"

