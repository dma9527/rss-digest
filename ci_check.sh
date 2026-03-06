#!/usr/bin/env bash
set -e

echo "🔍 Checking Python syntax..."
for f in *.py; do
  python -c "import py_compile; py_compile.compile('$f', doraise=True)"
done

echo "✅ All checks passed"
