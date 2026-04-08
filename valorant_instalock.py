from __future__ import annotations

import argparse
import base64
import json
import logging
import os
import re
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Optional

import requests
import urllib3
from requests import Response
from urllib3.exceptions import InsecureRequestWarning

# ─────────────────────────────────────────────
#  Configuración Interna (Ofuscada)
# ─────────────────────────────────────────────
_INT_CFG = "RGV2ZWxvcGVkIGJ5IEp1bmlvciB8IERpc2NvcmQ6IGh0dHBzOi8vZGlzY29yZC5nZy9zZUpya2pKTWhK"

def _get_credits() -> str:
    return base64.b64decode(_INT_CFG).decode("utf-8")

# ─────────────────────────────────────────────
#  Soporte Multilenguaje
# ─────────────────────────────────────────────

LANGUAGES = {
    "es": "Español",
    "en": "English",
    "pt": "Português",
}

STRINGS: dict[str, dict[str, str]] = {
    # Menú principal
    "menu_option_1":        {"es": "Activar Insta-Lock",         "en": "Enable Insta-Lock",           "pt": "Ativar Insta-Lock"},
    "menu_option_1_desc":   {"es": "Bloquea agente al entrar",   "en": "Locks agent on entry",        "pt": "Bloqueia agente ao entrar"},
    "menu_option_q":        {"es": "Finalizar",                   "en": "Exit",                        "pt": "Finalizar"},
    "menu_option_q_desc":   {"es": "Salida segura",               "en": "Safe exit",                   "pt": "Saída segura"},
    "menu_prompt":          {"es": "InstaLock@Console",           "en": "InstaLock@Console",           "pt": "InstaLock@Console"},
    "menu_quit_keys":       {"es": "q,salir",                     "en": "q,quit,exit",                 "pt": "q,sair"},

    # Selección de idioma
    "lang_select_title":    {"es": "Selección de Idioma",         "en": "Language Selection",          "pt": "Seleção de Idioma"},
    "lang_select_prompt":   {"es": "Elige tu idioma",             "en": "Choose your language",        "pt": "Escolha seu idioma"},

    # Selección de agente
    "agent_section":        {"es": "Selección de Agente",         "en": "Agent Selection",             "pt": "Seleção de Agente"},
    "agent_selected":       {"es": "Agente seleccionado",         "en": "Agent selected",              "pt": "Agente selecionado"},
    "agent_prompt":         {"es": "Escribe el número o nombre",  "en": "Type number or name",         "pt": "Digite o número ou nome"},

    # Estados del bucle
    "waiting_valorant":     {"es": "Esperando a que VALORANT se inicie...",      "en": "Waiting for VALORANT to start...",         "pt": "Aguardando VALORANT iniciar..."},
    "connected":            {"es": "Junior Instalock conectado.",                 "en": "Junior Instalock connected.",              "pt": "Junior Instalock conectado."},
    "state_searching":      {"es": "Buscando partida...",                         "en": "Searching for a match...",                 "pt": "Procurando partida..."},
    "state_ingame":         {"es": "Partida en curso...",                         "en": "Match in progress...",                     "pt": "Partida em andamento..."},
    "state_waiting":        {"es": "Esperando a buscar partida...",               "en": "Waiting to search for a match...",         "pt": "Aguardando para buscar partida..."},
    "match_found":          {"es": "Partida encontrada!",                         "en": "Match found!",                             "pt": "Partida encontrada!"},
    "lobby_detected_lock":  {"es": "¡Lobby detectada! Bloqueando...",             "en": "Lobby detected! Locking...",               "pt": "Lobby detectada! Bloqueando..."},
    "lock_success":         {"es": "{agent} bloqueado con éxito.",                "en": "{agent} locked successfully.",             "pt": "{agent} bloqueado com sucesso."},
    "waiting_match":        {"es": "Esperando partida para bloquear a {agent}...", "en": "Waiting for a match to lock {agent}...", "pt": "Aguardando partida para bloquear {agent}..."},
    "ctrl_c_hint":          {"es": "Presiona Ctrl+C para volver al menú.",        "en": "Press Ctrl+C to return to menu.",          "pt": "Pressione Ctrl+C para voltar ao menu."},
    "selection_done":       {"es": "Selección completada. El script se reactivará automáticamente al finalizar...", "en": "Selection done. Script will reactivate automatically when the match ends...", "pt": "Seleção concluída. O script será reativado automaticamente ao finalizar..."},
    "lobby_restart":        {"es": "Lobby detectado. Reiniciando Insta-Lock para la próxima partida.", "en": "Lobby detected. Restarting Insta-Lock for the next match.", "pt": "Lobby detectado. Reiniciando Insta-Lock para a próxima partida."},
    "session_ended":        {"es": "Sesión de partida finalizada. Volviendo a modo búsqueda.",        "en": "Match session ended. Returning to search mode.",               "pt": "Sessão de partida finalizada. Voltando ao modo busca."},
    "process_stopped":      {"es": "Proceso detenido por el usuario.",            "en": "Process stopped by user.",                 "pt": "Processo encerrado pelo usuário."},
    "region_error":         {"es": "No se detectó la región. Abre el juego.",     "en": "Region not detected. Open the game.",      "pt": "Região não detectada. Abra o jogo."},
    "lockfile_error":       {"es": "Error al leer sesión de Riot.",               "en": "Error reading Riot session.",              "pt": "Erro ao ler sessão do Riot."},

    # Salida
    "app_exit":             {"es": "Aplicación finalizada correctamente.",        "en": "Application closed successfully.",         "pt": "Aplicação encerrada corretamente."},
    "closing":              {"es": "Cerrando aplicación... ¡Suerte!",             "en": "Closing application... Good luck!",        "pt": "Fechando aplicação... Boa sorte!"},
    "press_enter":          {"es": "Pulsa Enter para continuar...",               "en": "Press Enter to continue...",               "pt": "Pressione Enter para continuar..."},

    # Sección
    "section_instalock":    {"es": "Insta-Lock",                                  "en": "Insta-Lock",                               "pt": "Insta-Lock"},
}

# Idioma activo (por defecto español)
_LANG: str = "es"

def t(key: str, **kwargs: str) -> str:
    """Devuelve el texto en el idioma activo. Soporta placeholders {var}."""
    text = STRINGS.get(key, {}).get(_LANG, key)
    return text.format(**kwargs) if kwargs else text

# ─────────────────────────────────────────────
#  Constantes
# ─────────────────────────────────────────────

AGENTS_URL   = "https://valorant-api.com/v1/agents"
VERSION_URL  = "https://valorant-api.com/v1/version"
LOCKFILE_REL = Path("Riot Games") / "Riot Client" / "Config" / "lockfile"
SHOOTER_LOG_REL = Path("VALORANT") / "Saved" / "Logs" / "ShooterGame.log"

DEFAULT_CLIENT_PLATFORM = (
    "ew0KCSJwbGF0Zm9ybVR5cGUiOiAiUEMiLA0KCSJwbGF0Zm9ybU9TIjogIldpbmRvd3MiLA0KCSJwbGF0Zm9ybU9TVmVyc2lvbiI6ICIxMC4wLjE5MDQyLjEuMjU2LjY0Yml0IiwNCgkicGxhdGZvcm1DaGlwc2V0IjogIlVua25vd24iDQp9"
)

EMPTY_MATCH_ID = "00000000-0000-0000-0000-000000000000"
VALORANT_PROCESS_NAMES = ("VALORANT-Win64-Shipping.exe", "VALORANT.exe")
SHOOTER_LOG_MAX_AGE_SEC = 10 * 60

GLZ_URL_RE = re.compile(r"https://glz-([^/]+?)-1\.([^.]+?)\.a\.pvp\.net", re.IGNORECASE)
MAX_CONSECUTIVE_NET_ERRORS = 15

# ─────────────────────────────────────────────
#  Utilidades de presentación
# ─────────────────────────────────────────────

BANNER = r"""
    ╔╦╗ ╦ ╦ ╔╗╔ ╦ ╔═╗ ╦═╗   ╦ ╔╗╔ ╔═╗ ╔╦╗ ╔═╗ ╦   ╔═╗ ╔═╗ ╦╔═
     ║  ║ ║ ║║║ ║ ║ ║ ╠╦╝   ║ ║║║ ╚═╗  ║  ╠═╣ ║   ║ ║ ║   ╠╩╗
    ╚╝  ╚═╝ ╝╚╝ ╩ ╚═╝ ╩╚═   ╩ ╝╚╝ ╚═╝  ╩  ╩ ╩ ╩═╝ ╚═╝ ╚═╝ ╩ ╩
    ────────────────────────────────────────────────────────
"""

def clr(code: str, text: str) -> str:
    if sys.stdout.isatty():
        return f"\033[{code}m{text}\033[0m"
    return text

def red(t_: str)    -> str: return clr("91", t_)
def green(t_: str)  -> str: return clr("92", t_)
def yellow(t_: str) -> str: return clr("93", t_)
def cyan(t_: str)   -> str: return clr("96", t_)
def bold(t_: str)   -> str: return clr("1",  t_)
def dim(t_: str)    -> str: return clr("2",  t_)

def clear_screen() -> None:
    os.system("cls" if sys.platform == "win32" else "clear")

def print_banner() -> None:
    print(cyan(BANNER))
    print(f"    {dim(_get_credits())}")
    print(dim("    " + "━" * 56))

def print_menu() -> None:
    print()
    print(f"    {cyan(' [1] ')} {bold(t('menu_option_1'))}    {dim('— ' + t('menu_option_1_desc'))}")
    print(f"    {red(' [Q] ')} {bold(t('menu_option_q'))}           {dim('— ' + t('menu_option_q_desc'))}")
    print(f"    {dim('━' * 25)}")

def ask_menu() -> str:
    return input(bold(f"\n    {t('menu_prompt')}: ")).strip().lower()

def section(title: str) -> None:
    print()
    print(dim("    " + "═" * 56))
    print(f"    {bold('>> ' + title.upper())}")
    print(dim("    " + "═" * 56))

# ─────────────────────────────────────────────
#  Selección de idioma
# ─────────────────────────────────────────────

def select_language() -> None:
    global _LANG
    clear_screen()
    print(cyan(BANNER))
    print(f"    {dim(_get_credits())}")
    print(dim("    " + "━" * 56))
    print()
    print(dim("    " + "═" * 56))
    # Título fijo en los 3 idiomas para que cualquier usuario lo entienda
    print(f"    {bold('>> LANGUAGE / IDIOMA / IDIOMA')}")
    print(dim("    " + "═" * 56))
    print()

    lang_list = list(LANGUAGES.items())
    for i, (code, name) in enumerate(lang_list, start=1):
        print(f"    {cyan(f'[{i}]')} {bold(name)}")

    print()
    while True:
        try:
            raw = input(bold("    >> ")).strip()
        except (EOFError, KeyboardInterrupt):
            _LANG = "es"
            return

        if raw in ("1", "es", "español", "espanol"):
            _LANG = "es"; return
        if raw in ("2", "en", "english"):
            _LANG = "en"; return
        if raw in ("3", "pt", "português", "portugues"):
            _LANG = "pt"; return

        # Intento por número genérico
        try:
            idx = int(raw) - 1
            if 0 <= idx < len(lang_list):
                _LANG = lang_list[idx][0]
                return
        except ValueError:
            pass

# ─────────────────────────────────────────────
#  Lógica de Sistema y Riot
# ─────────────────────────────────────────────

@dataclass
class LockfileData:
    name: str; pid: str; port: int; password: str; protocol: str

def parse_lockfile(path: Path) -> LockfileData:
    raw = path.read_text(encoding="utf-8").strip()
    parts = raw.split(":")
    if len(parts) < 5:
        raise ValueError(t("lockfile_error"))
    return LockfileData(parts[0], parts[1], int(parts[2]), parts[3], parts[4])

def basic_auth_header(password: str) -> str:
    token = base64.b64encode(f"riot:{password}".encode()).decode("ascii")
    return f"Basic {token}"

def _subprocess_run_win(args: list[str], **kwargs: Any) -> subprocess.CompletedProcess[str]:
    if sys.platform == "win32":
        kwargs.setdefault("creationflags", getattr(subprocess, "CREATE_NO_WINDOW", 0))
    kwargs.update({"capture_output": True, "text": True, "timeout": 25, "encoding": "utf-8", "errors": "replace"})
    return subprocess.run(args, **kwargs)

def is_valorant_process_running() -> bool:
    if sys.platform != "win32": return True
    ps_script = "$p = Get-Process -ErrorAction SilentlyContinue | Where-Object { $_.ProcessName -match '(?i)valorant' }; if ($p) { exit 0 } else { exit 1 }"
    try:
        if _subprocess_run_win(["powershell.exe", "-NoProfile", "-Command", ps_script]).returncode == 0: return True
    except: pass
    return False

# ─────────────────────────────────────────────
#  Lógica de Red y Endpoints
# ─────────────────────────────────────────────

def wait_until_valorant_ready(local: requests.Session, log: logging.Logger, wait_interval: float) -> LockfileData:
    local_app = os.environ.get("LOCALAPPDATA")
    if not local_app: sys.exit(1)
    lock_path = Path(local_app) / LOCKFILE_REL
    log.info(t("waiting_valorant"))
    while True:
        if not lock_path.is_file():
            time.sleep(wait_interval)
            continue
        try:
            lock = parse_lockfile(lock_path)
            get_entitlements(local, lock, log, quiet=True)
            sessions = get_external_sessions(local, lock)
            if find_valorant_session(sessions) or is_valorant_process_running():
                log.info(t("connected"))
                return lock
        except:
            time.sleep(wait_interval)

def fetch_playable_agents(log: logging.Logger) -> list[dict[str, Any]]:
    r = requests.get(AGENTS_URL, timeout=30).json()
    agents = [a for a in r["data"] if a.get("isPlayableCharacter") and a.get("displayName")]
    agents.sort(key=lambda x: str(x["displayName"]).lower())
    return agents

def prompt_agent_choice(agents: list[dict[str, Any]], default_name: Optional[str] = None) -> int:
    if default_name:
        needle = default_name.lower()
        for i, a in enumerate(agents, start=1):
            if needle in str(a["displayName"]).lower():
                print(green(f"    [+] {t('agent_selected')}: {a['displayName']}"))
                return i
    section(t("agent_section"))
    cols = 3
    for i, a in enumerate(agents, start=1):
        print(f"    {cyan(str(i)):>2} {a['displayName']:<15}", end="\n" if i % cols == 0 else "")
    if len(agents) % cols != 0: print()
    while True:
        raw = input(bold(f"\n    >> {t('agent_prompt')}: ")).strip()
        if not raw: continue
        try:
            n = int(raw)
            if 1 <= n <= len(agents): return n
        except: pass
        matches = [i for i, a in enumerate(agents, 1) if raw.lower() in a["displayName"].lower()]
        if len(matches) == 1: return matches[0]

def get_entitlements(session, lock, log, quiet=False):
    r = session.get(f"https://127.0.0.1:{lock.port}/entitlements/v1/token", headers={"Authorization": basic_auth_header(lock.password)}, timeout=15)
    r.raise_for_status()
    return r.json()

def get_external_sessions(session, lock):
    return session.get(f"https://127.0.0.1:{lock.port}/product-session/v1/external-sessions", headers={"Authorization": basic_auth_header(lock.password)}, timeout=15).json()

def get_chat_presence(session, lock):
    return session.get(f"https://127.0.0.1:{lock.port}/chat/v4/presences", headers={"Authorization": basic_auth_header(lock.password)}, timeout=15).json()

def find_valorant_session(sessions):
    for info in sessions.values():
        if isinstance(info, dict) and str(info.get("productId")).lower() == "valorant": return info
    return None

def resolve_region_shard(sessions, log):
    vs = find_valorant_session(sessions)
    if vs:
        args = (vs.get("launchConfiguration") or {}).get("arguments") or []
        m = GLZ_URL_RE.search(" ".join([str(a) for a in args]))
        if m: return (m.group(1).lower(), m.group(2).lower())
    local = os.environ.get("LOCALAPPDATA")
    if local:
        log_path = Path(local) / SHOOTER_LOG_REL
        if log_path.is_file():
            try:
                with log_path.open("r", errors="ignore") as f:
                    content = f.read()[-500000:]
                    m = GLZ_URL_RE.search(content)
                    if m: return (m.group(1).lower(), m.group(2).lower())
            except: pass
    raise RuntimeError(t("region_error"))

def resolve_client_version(sessions, log):
    vs = find_valorant_session(sessions)
    if vs and vs.get("version"): return str(vs["version"]).strip()
    return requests.get(VERSION_URL, timeout=25).json()["data"]["riotClientVersion"]

def riot_headers(at, ej, cv):
    return {"Authorization": f"Bearer {at}", "X-Riot-Entitlements-JWT": ej, "X-Riot-ClientVersion": cv, "X-Riot-ClientPlatform": DEFAULT_CLIENT_PLATFORM, "Content-Type": "application/json"}

# ─────────────────────────────────────────────
#  Bucle de Insta-Lock
# ─────────────────────────────────────────────

def run_polling_loop(local, glz, lock, base, puuid, agent_id, agent_name, sessions_ref, poll_interval, log) -> bool:
    lock_attempted = False
    last_status = None
    last_check = 0
    ent = get_entitlements(local, lock, log, quiet=True)
    at, ej = ent["accessToken"], ent["token"]
    cv = resolve_client_version(sessions_ref[0], log)

    log.info(f"Insta-Lock → {agent_name}")

    while True:
        time.sleep(poll_interval)
        try:
            h = riot_headers(at, ej, cv)
            r = glz.get(f"{base}/pregame/v1/players/{puuid}", headers=h, timeout=10)

            if r.status_code == 401:
                ent = get_entitlements(local, lock, log, quiet=True)
                at, ej = ent["accessToken"], ent["token"]
                continue

            if r.status_code == 404:
                lock_attempted = False
                now = time.monotonic()
                if (now - last_check) > 1.2:
                    last_check = now
                    try:
                        presences = get_chat_presence(local, lock)
                        player = next((p for p in presences.get("presences", []) if str(p.get("puuid")).lower() == str(puuid).lower()), None)

                        if player and "private" in player:
                            try:
                                private_raw = player["private"]
                                private_raw += "=" * ((4 - len(private_raw) % 4) % 4)
                                data = json.loads(base64.b64decode(private_raw).decode("utf-8"))

                                party_state = str(data.get("partyState")).upper()
                                loop_state  = str(data.get("sessionLoopState")).upper()

                                if "MATCHMAKING" in party_state:
                                    status = t("state_searching")
                                elif loop_state == "INGAME":
                                    status = t("state_ingame")
                                else:
                                    status = t("state_waiting")

                                if status != last_status:
                                    log.info(status)
                                    last_status = status
                            except: pass
                    except: pass
                continue

            pdata = r.json()
            match_id = pdata.get("MatchID")
            if not match_id or match_id == EMPTY_MATCH_ID: continue

            if last_status != t("match_found"):
                log.info(t("match_found"))
                last_status = t("match_found")

            rm = glz.get(f"{base}/pregame/v1/matches/{match_id}", headers=h, timeout=poll_interval * 5)
            if rm.ok and rm.json().get("PregameState") == "character_select_active" and not lock_attempted:
                log.info(t("lobby_detected_lock"))
                if glz.post(f"{base}/pregame/v1/matches/{match_id}/lock/{agent_id}", headers=h, json={}).ok:
                    print(green(f"\n    [!] {t('lock_success', agent=agent_name)}"))
                    return True
                lock_attempted = True
        except: pass

def run_instalock(local, glz, log, wi, pi, pt, da) -> None:
    section(t("section_instalock"))
    try:
        lock   = wait_until_valorant_ready(local, log, wi)
        agents = fetch_playable_agents(log)
        idx    = prompt_agent_choice(agents, da)
        agent  = agents[idx - 1]
        ent    = get_entitlements(local, lock, log)
        puuid  = ent["subject"]
        region, shard = resolve_region_shard(get_external_sessions(local, lock), log)
        base   = f"https://glz-{region}-1.{shard}.a.pvp.net"

        print(cyan(f"\n    [*] {t('waiting_match', agent=agent['displayName'])}"))
        print(dim(f"    [*] {t('ctrl_c_hint')}"))

        while True:
            if run_polling_loop(local, glz, lock, base, puuid, agent["uuid"], agent["displayName"], [get_external_sessions(local, lock)], pi, log):
                print(dim(f"\n    {t('selection_done')}"))

                time.sleep(15)

                match_active = True
                while match_active:
                    time.sleep(5)
                    try:
                        if not is_valorant_process_running(): return

                        headers    = {"Authorization": basic_auth_header(lock.password)}
                        r_presence = local.get(f"https://127.0.0.1:{lock.port}/chat/v4/presences", headers=headers, timeout=15)

                        if r_presence.status_code == 401:
                            ent = get_entitlements(local, lock, log, quiet=True)
                            continue

                        presences = r_presence.json()
                        player = next((p for p in presences.get("presences", []) if str(p.get("puuid")).lower() == str(puuid).lower()), None)

                        if player and "private" in player:
                            private_raw  = player["private"]
                            private_raw += "=" * ((4 - len(private_raw) % 4) % 4)
                            data         = json.loads(base64.b64decode(private_raw).decode("utf-8"))
                            loop_state   = str(data.get("sessionLoopState")).upper()

                            if loop_state not in ["INGAME", "PREGAME"]:
                                print(yellow(f"\n    [!] {t('lobby_restart')}"))
                                match_active = False
                                time.sleep(2)
                        else:
                            print(yellow(f"\n    [!] {t('session_ended')}"))
                            match_active = False
                    except:
                        pass
            else:
                break
    except (KeyboardInterrupt, EOFError):
        print(yellow(f"\n    [!] {t('process_stopped')}"))

# ─────────────────────────────────────────────
#  Main
# ─────────────────────────────────────────────

def main() -> None:
    try:
        p = argparse.ArgumentParser(description="Junior Instalock Professional")
        p.add_argument("--agent",         default=None)
        p.add_argument("--lang",          default=None, choices=list(LANGUAGES.keys()),
                       help="Language code: es | en | pt")
        p.add_argument("--poll-interval", type=float, default=0.2)
        p.add_argument("--wait-interval", type=float, default=2.0)
        p.add_argument("--log-level",     default="INFO")
        args = p.parse_args()

        logging.basicConfig(level=getattr(logging, args.log_level),
                            format="%(asctime)s [%(levelname)s] %(message)s",
                            datefmt="%H:%M:%S")
        log = logging.getLogger("junior_instalock")
        urllib3.disable_warnings(InsecureRequestWarning)

        local, glz = requests.Session(), requests.Session()
        local.verify = False

        # ── Selección de idioma ──────────────────────────────────
        if args.lang:
            global _LANG
            _LANG = args.lang
        else:
            select_language()
        # ────────────────────────────────────────────────────────

        quit_keys = set(t("menu_quit_keys").split(","))

        while True:
            clear_screen()
            print_banner()
            print_menu()

            try:
                c = ask_menu()
            except (EOFError, KeyboardInterrupt):
                print(cyan(f"\n\n    {_get_credits()}"))
                print(bold(f"    >> {t('app_exit')}"))
                os._exit(0)

            if c == "1":
                run_instalock(local, glz, log, args.wait_interval, args.poll_interval, 0, args.agent)
                try:
                    input(dim(f"\n    {t('press_enter')}"))
                except (EOFError, KeyboardInterrupt):
                    print(cyan(f"\n\n    {_get_credits()}"))
                    print(bold(f"    >> {t('app_exit')}"))
                    os._exit(0)
            elif c in quit_keys:
                print(cyan(f"\n    {t('closing')}"))
                break

    except (KeyboardInterrupt, EOFError):
        print(cyan(f"\n\n    {_get_credits()}"))
        print(bold(f"    >> {t('app_exit')}"))
        os._exit(0)

if __name__ == "__main__":
    main()