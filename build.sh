#!/usr/bin/env bash

# build.sh:       BUILDS SIGNET.PY INTO A LINUX BINARY WITH NUITKA
# AUTHOR:         DANIEL DESAI
# UPDATED:        2026-10-26
# VERSION:        26.b.0.1.0
#
# ./build.sh [--onefile | --standalone] [--python PY]
#   --onefile     one file, dist/signet-<version>-linux-<arch> (default)
#   --standalone  a folder, dist/signet-<version>-linux-<arch>-standalone/signet
# Dependencies: python3 -m pip install nuitka zstandard patchelf; gcc

set -euo pipefail
cd "$(dirname "$0")"

mode=onefile
py=python3
while [ $# -gt 0 ]; do
    case "$1" in
        --onefile)    mode=onefile ;;
        --standalone) mode=standalone ;;
        --python)     py="$2"; shift ;;
        -h|--help)    sed -n '8,11p' "$0" | sed 's/^# \{0,1\}//'; exit 0 ;;
        *)            echo "build.sh: unknown option $1" >&2; exit 2 ;;
    esac
    shift
done

[ "$(uname -s)" = Linux ] || { echo "build.sh: Linux only for now" >&2; exit 1; }

# VERSION and signet.py must agree
version=$(tr -d '[:space:]' < VERSION)
code_version=$(sed -n 's/^VERSION = "\(.*\)"/\1/p' signet.py)
if [ "$version" != "$code_version" ]; then
    echo "build.sh: VERSION says $version but signet.py says $code_version" >&2
    exit 1
fi

for need in gcc patchelf; do
    command -v "$need" >/dev/null || { echo "build.sh: $need not found" >&2; exit 1; }
done
"$py" -m nuitka --version >/dev/null 2>&1 || { echo "build.sh: $py -m pip install nuitka zstandard" >&2; exit 1; }

name="signet-$version-linux-$(uname -m)"
[ "$mode" = standalone ] && name="$name-standalone"
rm -rf build "dist/$name"
mkdir -p build dist

opts=(--output-dir=build --output-filename=signet --remove-output --assume-yes-for-downloads
      --python-flag=no_site --python-flag=-O)
if [ "$mode" = onefile ]; then
    # unpack once per version under the user's cache, not on every start
    opts+=(--onefile --onefile-tempdir-spec="{CACHE_DIR}/signet/bin-$version")
else
    opts+=(--standalone)
fi

echo "build.sh: building $name ($mode)"
"$py" -m nuitka "${opts[@]}" signet.py

if [ "$mode" = onefile ]; then
    mv build/signet "dist/$name"
    bin="$PWD/dist/$name"
else
    mv build/signet.dist "dist/$name"
    bin="$PWD/dist/$name/signet"
fi
rm -rf build

# smoke test in an empty folder
t=$(mktemp -d)
trap 'rm -rf "$t"' EXIT
fail() { echo "build.sh: smoke test failed: $1" >&2; exit 1; }

"$bin" --version | grep -qF "signet $version" || fail "--version"
cd "$t"
cat > hello.signet <<'EOF'
let hello = 'Hello, world!'
connect(hello, messenger.input)
run(messenger)
let response = messenger.output.sig
echo(response)
EOF
"$bin" hello.signet --check >/dev/null || fail "--check"
if command -v python3 >/dev/null; then
    cat > messenger.py <<'EOF'
from signet import signals
signals.output = signals.input
EOF
    "$bin" hello.signet | grep -qF 'Hello, world!' || fail "hello/messenger"
fi
cat > double.signet <<'EOF'
output(float::y, x * 2)
EOF
cat > twice.signet <<'EOF'
connect(2.5, double.x)
run(double)
echo(double.y.sig)
EOF
"$bin" twice.signet | grep -qF '5.0' || fail ".signet module"

echo "build.sh: ok -> ${bin#$OLDPWD/}"