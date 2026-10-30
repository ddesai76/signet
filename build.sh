#!/usr/bin/env bash

# build.sh:       BUILD A SIGNET 26 BINARY WITH NUITKA (LINUX, --standalone)
# AUTHOR:         DANIEL DESAI
# UPDATED:        2026-10-25
# VERSION:        26.b.0.1.3
#
# Needs python3, nuitka (pip install nuitka), patchelf, and a C compiler.
# Output: dist/signet-<version>-linux-<arch>.tar.gz, holding signet/signet and its libraries.

set -euo pipefail
cd "$(dirname "$0")"

VERSION=$(head -n1 VERSION | tr -d '[:space:]')
ARCH=$(uname -m)
NAME="signet-$VERSION-linux-$ARCH"

for tool in python3 patchelf; do
    command -v "$tool" >/dev/null || { echo "build.sh: $tool not found" >&2; exit 1; }
done
command -v gcc >/dev/null || command -v clang >/dev/null || { echo "build.sh: no C compiler found" >&2; exit 1; }
python3 -m nuitka --version >/dev/null 2>&1 || { echo "build.sh: nuitka not found (pip install nuitka)" >&2; exit 1; }

BAKED=$(sed -n 's/^VERSION = "\(.*\)".*/\1/p' signet.py)
[ "$BAKED" = "$VERSION" ] || { echo "build.sh: VERSION ($VERSION) differs from signet.py ($BAKED)" >&2; exit 1; }

rm -rf build "dist/$NAME" "dist/$NAME.tar.gz"
mkdir -p build dist
python3 -m nuitka --standalone --assume-yes-for-downloads --remove-output \
    --include-data-files=VERSION=VERSION \
    --output-dir=build --output-filename=signet signet.py
mkdir -p "dist/$NAME"
cp -r build/signet.dist "dist/$NAME/signet"
cp VERSION LICENSE SIGNET.md "dist/$NAME/"
BIN="$PWD/dist/$NAME/signet/signet"

# Smoke test: run the binary on a hello module in a scratch folder.
T=$(mktemp -d); trap 'rm -rf "$T"' EXIT
printf "let hello = 'Hello, world!'\nconnect(hello, message.input)\nrun(message)\necho(message.output.sig)\n" > "$T/hello.signet"
printf 'echo(input)\noutput(output, input)\n' > "$T/message.signet"
cd "$T"
"$BIN" --version | grep -q "$VERSION"
"$BIN" hello.signet --check | grep -q ok
"$BIN" hello.signet | grep -q 'message.output.sig = "Hello, world!"'
"$BIN" --export-helpers helpers >/dev/null && [ -f helpers/signet/__init__.py ]
rm message.signet
printf 'from signet import signals\nprint(signals.input)\nsignals.output = signals.input\n' > message.py
"$BIN" hello.signet | grep -q 'message.output.sig = "Hello, world!"'
echo "smoke test: ok"

cd "$OLDPWD"
tar -czf "dist/$NAME.tar.gz" -C dist "$NAME"
echo "built dist/$NAME.tar.gz"
