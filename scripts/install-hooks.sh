#!/bin/sh
# Install git hooks for adeline-withlove.
# Run once after cloning.

cat > .git/hooks/pre-commit << 'HOOK'
#!/bin/sh
# Block commits containing raw secrets (keys, connection strings).
# Patterns: OpenAI keys, Google API keys, Postgres URIs.
SK_PROJ="sk""-proj-"
SK_KEY="sk-[A-Za-z0-9]{48}"
AIZA_KEY="AIza[0-9A-Za-z\-_]{35}"
DB_URI="postgre""sql://[^:]*:[^@]*@"
PATTERNS="${SK_PROJ}|${SK_KEY}|${AIZA_KEY}|${DB_URI}"
if git diff --cached --name-only | xargs grep -rE "$PATTERNS" 2>/dev/null | grep -v "^.git/"; then
    echo ""
    echo "ERROR: Potential secret found in staged files."
    echo "Remove secrets before committing. Use Railway env vars for production secrets."
    echo ""
    exit 1
fi
exit 0
HOOK
chmod +x .git/hooks/pre-commit
echo "Git hooks installed."
