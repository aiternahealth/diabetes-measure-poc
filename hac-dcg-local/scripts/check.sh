#!/usr/bin/env bash
# Prerequisite check for the local stack (macOS). Prints OK / FIX lines; exits 1 if anything blocks.
fail=0
ok()  { printf "  \033[32mOK\033[0m   %s\n" "$1"; }
fix() { printf "  \033[31mFIX\033[0m  %s\n       → %s\n" "$1" "$2"; fail=1; }
warn(){ printf "  \033[33mNOTE\033[0m %s\n" "$1"; }

echo "Checking prerequisites…"

command -v brew >/dev/null && ok "Homebrew" || fix "Homebrew not found" "Install from https://brew.sh, then run: brew bundle"

if command -v docker >/dev/null; then
  if docker info >/dev/null 2>&1; then ok "Docker running ($(docker --version | cut -d, -f1))"
  else fix "Docker installed but not running" "Start Docker Desktop (or OrbStack) and wait for it to finish starting"; fi
  v=$(docker compose version --short 2>/dev/null | sed 's/^v//')
  if [ -n "$v" ] && [ "$(printf '%s\n2.24.0\n' "$v" | sort -V | head -1)" = "2.24.0" ]; then ok "Docker Compose $v"
  else fix "Docker Compose ${v:-missing} (need 2.24+)" "Update Docker Desktop"; fi
else
  fix "Docker not installed" "Install Docker Desktop (docker.com) or OrbStack: brew install --cask orbstack"
fi

JDK="$(brew --prefix openjdk@21 2>/dev/null)/libexec/openjdk.jdk/Contents/Home/bin/java"
JAVA=$([ -x "$JDK" ] && echo "$JDK" || command -v java)
if [ -n "$JAVA" ] && "$JAVA" -version >/dev/null 2>&1; then
  jv=$("$JAVA" -version 2>&1 | head -1 | sed -E 's/.*version "([0-9]+).*/\1/')
  [ "${jv:-0}" -ge 17 ] && ok "Java $jv" || fix "Java $jv is too old (need 17+)" "brew install openjdk@21"
else
  fix "Java not found" "brew install openjdk@21"
fi

command -v uv >/dev/null && ok "uv $(uv --version | cut -d' ' -f2)" || fix "uv not found" "brew install uv"
if command -v node >/dev/null; then ok "Node $(node --version)"; else fix "Node.js not found" "brew install node (or nvm install --lts)"; fi
command -v sushi >/dev/null && ok "SUSHI $(sushi --version 2>/dev/null | head -1)" || warn "SUSHI not installed yet — make setup installs it"

mem_gb=$(( $(sysctl -n hw.memsize 2>/dev/null || echo 0) / 1073741824 ))
if [ "$mem_gb" -ge 16 ]; then ok "${mem_gb} GB RAM"; elif [ "$mem_gb" -ge 8 ]; then warn "${mem_gb} GB RAM — use POP=1000 and ENGINE=mini, stop Medplum while running views"; else warn "RAM unknown"; fi
free_gb=$(df -g . | awk 'NR==2{print $4}')
[ "${free_gb:-0}" -ge 15 ] && ok "${free_gb} GB free disk" || warn "Only ${free_gb} GB free disk (15+ recommended)"

for p in 3000 8103; do
  if lsof -nP -iTCP:$p -sTCP:LISTEN >/dev/null 2>&1; then
    owner=$(lsof -nP -iTCP:$p -sTCP:LISTEN | awk 'NR==2{print $1}')
    [[ "$owner" == com.docke* || "$owner" == *docker* || "$owner" == OrbStack* ]] && ok "Port $p used by Docker (Medplum already up?)" \
      || fix "Port $p is in use by $owner" "Stop that app; Medplum needs ports 3000 and 8103"
  else ok "Port $p free"; fi
done

[ -f .env ] && grep -q '^MEDPLUM_CLIENT_ID=.\+' .env && ok ".env has a Medplum client id" || warn ".env client id/secret not set yet (README step 3)"

echo; [ $fail -eq 0 ] && echo "Ready." || echo "Fix the items above, then run make check again."
exit $fail
