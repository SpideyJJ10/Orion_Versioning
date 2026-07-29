"""
deploy_prod.py — Flujo de despliegue a producción Orion POS v3

Ejecutar con: python scripts/deploy_prod.py
Prerrequisito: git configurado, rama develop/main sincronizadas

Este script:
1. Ejecuta los tests de desarrollo contra el servidor local
2. Verifica el estado del repositorio git
3. Genera un checklist de pre-deploy
4. Solicita confirmación manual
5. Realiza merge develop → main y push
6. Muestra instrucciones de verificación post-deploy
"""
import sys
import os
import subprocess
import json
from datetime import datetime

# ── Config ────────────────────────────────────────────────────────
PROD_URL   = "https://tizon-mvp-version-2.onrender.com"
RENDER_ID  = "srv-d7hcv358nd3s73ajlvp0"
GIT_BRANCH_DEV  = "develop"
GIT_BRANCH_PROD = "main"

# Colores
class C:
    OK   = "\033[92m"
    FAIL = "\033[91m"
    WARN = "\033[93m"
    INFO = "\033[94m"
    BOLD = "\033[1m"
    DIM  = "\033[2m"
    END  = "\033[0m"


def run_cmd(cmd, capture=True):
    """Ejecuta un comando shell y retorna stdout"""
    try:
        result = subprocess.run(
            cmd, shell=True, capture_output=capture, text=True, timeout=30
        )
        return result.returncode, result.stdout.strip(), result.stderr.strip()
    except subprocess.TimeoutExpired:
        return 1, "", "Timeout"
    except Exception as e:
        return 1, "", str(e)


def section(title):
    print(f"\n{C.BOLD}{'=' * 60}{C.END}")
    print(f"{C.BOLD}  {title}{C.END}")
    print(f"{C.BOLD}{'=' * 60}{C.END}")


def check(condition, msg_ok, msg_fail):
    if condition:
        print(f"  [OK] {C.OK}{msg_ok}{C.END}")
        return True
    else:
        print(f"  [!!] {C.FAIL}{msg_fail}{C.END}")
        return False


# ══════════════════════════════════════════════════════════════════
#  PRE-FLIGHT CHECKS
# ══════════════════════════════════════════════════════════════════

def preflight_checks():
    section("1. PRE-FLIGHT CHECKS")
    all_ok = True
    
    # 1.1 Git está disponible
    code, out, _ = run_cmd("git --version")
    all_ok &= check(code == 0, f"Git: {out}", "Git no disponible")
    
    # 1.2 Estamos en el directorio correcto
    code, out, _ = run_cmd("git rev-parse --show-toplevel")
    is_repo = code == 0 and "Tizon_MVP_Version_2" in out
    all_ok &= check(is_repo, f"Repo: {out.split(os.sep)[-1]}", "No estamos en el repo correcto")
    
    # 1.3 Rama actual
    code, branch, _ = run_cmd("git branch --show-current")
    all_ok &= check(code == 0, f"Rama actual: {branch}", "No se pudo determinar la rama")
    
    # 1.4 No hay cambios sin commit
    code, status, _ = run_cmd("git status --porcelain")
    is_clean = code == 0 and len(status.strip()) == 0
    if not is_clean:
        print(f"  [??] {C.WARN}Hay cambios sin commit:{C.END}")
        for line in status.split("\n")[:10]:
            print(f"      {C.DIM}{line}{C.END}")
    all_ok &= check(is_clean, "Directorio de trabajo limpio", "Hay cambios sin commit — haz commit primero")
    
    # 1.5 Verificar archivos críticos existen
    critical_files = [
        "backend/main.py",
        "frontend/index.html",
        "frontend/login.html",
        "frontend/register.html",
        "frontend/js/core/app-shell.js",
        "frontend/js/core/api-client.js",
        "frontend/js/core/tutorial-manager.js",
        "frontend/css/main.css",
        "requirements.txt",
    ]
    
    missing = [f for f in critical_files if not os.path.exists(f)]
    all_ok &= check(len(missing) == 0,
        f"Archivos críticos: {len(critical_files)} OK",
        f"Faltan archivos: {', '.join(missing)}")
    
    return all_ok, branch


def run_dev_tests():
    """Ejecutar test suite de desarrollo"""
    section("2. TESTS DE DESARROLLO")
    
    print(f"  {C.INFO}Ejecutando test_dev.py contra servidor local...{C.END}")
    print(f"  {C.DIM}(Asegúrate de que el servidor esté corriendo en localhost:8000){C.END}")
    print()
    
    code, out, err = run_cmd(f"{sys.executable} scripts/test_dev.py")
    
    # Mostrar output del test
    for line in out.split("\n"):
        print(f"  {line}")
    
    if code != 0:
        print(f"\n  [!!] {C.FAIL}Tests fallaron. Corrige los errores antes de deploy.{C.END}")
        return False
    
    print(f"\n  [OK] {C.OK}Todos los tests pasaron{C.END}")
    return True


def git_log_preview():
    """Mostrar los commits que se van a deployar"""
    section("3. COMMITS PENDIENTES DE DEPLOY")
    
    code, out, _ = run_cmd(f"git log {GIT_BRANCH_PROD}..{GIT_BRANCH_DEV} --oneline --no-decorate -20")
    
    if code != 0 or not out.strip():
        print(f"  {C.WARN}No hay commits nuevos entre {GIT_BRANCH_DEV} y {GIT_BRANCH_PROD}{C.END}")
        code2, out2, _ = run_cmd(f"git log --oneline --no-decorate -5")
        if out2:
            print(f"  {C.INFO}Últimos 5 commits:{C.END}")
            for line in out2.split("\n"):
                print(f"    {C.DIM}{line}{C.END}")
        return True
    
    commit_count = len(out.strip().split("\n"))
    print(f"  {C.INFO}{commit_count} commits para deploy:{C.END}")
    for line in out.split("\n"):
        print(f"    {C.DIM}{line}{C.END}")
    
    return True


def deploy_checklist():
    """Checklist manual de pre-deploy"""
    section("4. CHECKLIST PRE-DEPLOY")
    
    items = [
        "Tests de desarrollo pasaron exitosamente",
        "No hay cambios sin commit en el repo",
        "Variables de entorno en Render actualizadas (DATABASE_URL, SECRET_KEY, etc.)",
        "Migraciones de BD aplicadas (backfill V3 en startup)",
        "Assets estáticos verificados (logo, CSS, JS)",
        "Flujo de login/register probado manualmente",
        "Flujo de POS probado manualmente",
        "No hay console.log de debug en código de producción",
    ]
    
    for i, item in enumerate(items, 1):
        print(f"  [{i}] {item}")
    
    print(f"\n  {C.BOLD}Destino: {PROD_URL}{C.END}")
    print(f"  {C.BOLD}Render:  {RENDER_ID}{C.END}")
    print(f"  {C.BOLD}Fecha:   {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}{C.END}")
    
    return True


def confirm_deploy():
    """Solicitar confirmación del usuario"""
    section("5. CONFIRMACIÓN")
    
    print(f"  {C.WARN}[!!] Estás a punto de deployar a PRODUCCIÓN{C.END}")
    print(f"  {C.WARN}   Rama: {GIT_BRANCH_DEV} -> {GIT_BRANCH_PROD}{C.END}")
    print(f"  {C.WARN}   URL:  {PROD_URL}{C.END}")
    print()
    
    try:
        answer = input(f"  {C.BOLD}¿Proceder con el deploy? (yes/no): {C.END}").strip().lower()
    except (KeyboardInterrupt, EOFError):
        print(f"\n  {C.WARN}Deploy cancelado por el usuario{C.END}")
        return False
    
    return answer in ("yes", "y", "si", "sí")


def execute_deploy(current_branch):
    """Ejecutar merge y push a producción"""
    section("6. EJECUTANDO DEPLOY")
    
    steps = [
        (f"git checkout {GIT_BRANCH_PROD}", "Cambiando a rama main"),
        (f"git merge {GIT_BRANCH_DEV} --no-edit", "Merge develop → main"),
        (f"git push origin {GIT_BRANCH_PROD}", "Push a origin/main"),
        (f"git checkout {current_branch}", f"Volviendo a rama {current_branch}"),
    ]
    
    for cmd, desc in steps:
        print(f"  ... {desc}...")
        code, out, err = run_cmd(cmd)
        
        if code != 0:
            print(f"  [!!] {C.FAIL}Error: {err or out}{C.END}")
            print(f"  {C.WARN}Restaurando rama: git checkout {current_branch}{C.END}")
            run_cmd(f"git checkout {current_branch}")
            return False
        
        print(f"  [OK] {C.OK}{desc} -- OK{C.END}")
        if out and len(out) < 200:
            print(f"     {C.DIM}{out}{C.END}")
    
    return True


def post_deploy_info():
    """Instrucciones de verificación post-deploy"""
    section("7. POST-DEPLOY — Verificación")
    
    print(f"""
  {C.INFO}El deploy se ha iniciado en Render (auto-deploy desde main).{C.END}
  {C.INFO}Render tardará 2-5 minutos en construir y deployar.{C.END}
  
  {C.BOLD}Verificaciones manuales:{C.END}
  
  1. {C.INFO}Health check:{C.END}
     curl {PROD_URL}/api/health
  
  2. {C.INFO}Página de login:{C.END}
     Abrir: {PROD_URL}/login
  
  3. {C.INFO}Registro de cuenta:{C.END}
     Abrir: {PROD_URL}/register
  
  4. {C.INFO}App principal (requiere login):{C.END}
     Abrir: {PROD_URL}/
  
  5. {C.INFO}API docs:{C.END}
     Abrir: {PROD_URL}/docs
  
  6. {C.INFO}Legacy (respaldo):{C.END}
     Abrir: {PROD_URL}/legacy
  
  {C.BOLD}Monitorear logs en Render Dashboard:{C.END}
     https://dashboard.render.com/web/{RENDER_ID}/logs
  
  {C.BOLD}Ejecutar tests contra producción:{C.END}
     TEST_BASE_URL={PROD_URL} python scripts/test_dev.py
    """)


# ══════════════════════════════════════════════════════════════════
#  MAIN
# ══════════════════════════════════════════════════════════════════

def main():
    print(f"\n{C.BOLD}{'=' * 60}{C.END}")
    print(f"{C.BOLD} {C.INFO} ORION POS v3 -- Deploy Pipeline (Producción){C.END}")
    print(f"{C.BOLD}  Target: {PROD_URL}{C.END}")
    print(f"{C.BOLD}{'=' * 60}{C.END}")
    
    # Modo dry-run
    dry_run = "--dry-run" in sys.argv
    skip_tests = "--skip-tests" in sys.argv
    
    if dry_run:
        print(f"\n  {C.WARN} MODO DRY-RUN — No se ejecutará el deploy{C.END}")
    
    # Step 1: Pre-flight checks
    preflight_ok, current_branch = preflight_checks()
    if not preflight_ok and not dry_run:
        print(f"\n  {C.FAIL}STOP: Pre-flight checks fallaron. Corrige los errores.{C.END}\n")
        sys.exit(1)
    
    # Step 2: Tests (opcional con --skip-tests)
    if skip_tests:
        print(f"\n  {C.WARN}[??] Tests saltados con --skip-tests{C.END}")
    else:
        tests_ok = run_dev_tests()
        if not tests_ok and not dry_run:
            print(f"\n  {C.FAIL}STOP: Tests fallaron. Corrige antes de deploy.{C.END}\n")
            sys.exit(1)
    
    # Step 3: Preview commits
    git_log_preview()
    
    # Step 4: Checklist
    deploy_checklist()
    
    if dry_run:
        print(f"\n  {C.WARN} DRY-RUN completado. Usa sin --dry-run para deploy real.{C.END}\n")
        sys.exit(0)
    
    # Step 5: Confirm
    if not confirm_deploy():
        print(f"\n  {C.WARN}Deploy cancelado.{C.END}\n")
        sys.exit(0)
    
    # Step 6: Execute
    deploy_ok = execute_deploy(current_branch)
    if not deploy_ok:
        print(f"\n  {C.FAIL}STOP: Deploy fallo. Revisa los errores.{C.END}\n")
        sys.exit(1)
    
    # Step 7: Post-deploy
    post_deploy_info()
    
    print(f"\n  {C.OK}[OK] Deploy pipeline completado exitosamente{C.END}\n")


if __name__ == "__main__":
    main()
