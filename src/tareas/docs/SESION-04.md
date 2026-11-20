# Sesión 04 — pasos (control personal)

Guía: https://aulaenlanube.com/programacion-ia/cli/sesion-04/

Marca con `x` lo que ya tienes hecho. Lo que queda sin marcar es lo que te falta.
Al terminar cada paso, escribe la fecha entre paréntesis.

Entrega: **viernes 20 de noviembre** — URL del repo en la Entrega 2 · CLI del aula,
con la etiqueta `v1.0.0`.

## Pasos

- [x] paso-1 (pytest y la caja de arena: conftest.py) (17-11-2026)
- [x] paso-2 (config y acciones: casos feos con parametrize) (17-11-2026)
- [x] paso-3 (la prueba que prueba: romper el código a propósito) (19-11-2026)
- [x] paso-4 (la IA sin red: ProveedorFalso) (17-11-2026)
- [x] paso-5 (la CLI desde fuera: CliRunner, códigos 0-4) (17-11-2026)
- [ ] paso-6 (GitHub Actions en tres sistemas) — el workflow YA está commitear; falta push y Actions en verde
- [x] paso-7 (opencode run: scripts/revisar.sh) (17-11-2026)
- [ ] paso-8 (release: rama, PR, CHANGELOG y etiqueta v1.0.0)
- [ ] paso-9 (instalación cruzada: la prueba de otra persona)

## Detalle de cada paso

### paso-1 (pytest y la caja de arena)

- [x] `uv add --dev pytest` (pytest y pytest-cov en `pyproject.toml`).
- [x] `tests/conftest.py` con la fixture `aislado` (`autouse=True`): `monkeypatch.chdir(tmp_path)`,
  `HOME` y `USERPROFILE` a `tmp_path`, y fuera `CENTRO_IA_URL`, `CENTRO_IA_KEY` y `CENTRO_IA_CA`.
- [x] Fixture `descargas`: carpeta con ficheros feos (tildes, espacios, mayúsculas y uno viejo de 40 días).
- [x] Fixture `escribir_config`: escribe un `acciones.json` y devuelve su ruta.
- [x] `ProveedorFalso(ProveedorIA)` y fixture `modelo_falso`. *(ya con uso: Prompt 21)*
- [x] Terminar con: `uv run pytest` → **174 passed** (verificado 19-11, tras ADR-0015).

### paso-2 (config y acciones: casos feos con parametrize)

- [x] `tests/test_config.py`: camino feliz + casos feos (JSON roto, fichero inexistente,
  tipo desconocido, campo obligatorio faltante, `max_caracteres` fuera de rango con
  `@pytest.mark.parametrize`).
- [x] `tests/test_acciones.py`: `destino_libre` (nunca sobrescribe), plantillas,
  fábrica desde la configuración, describir filtro.
- [x] Ninguna prueba toca carpetas reales: todo en `tmp_path` (lo garantiza `aislado`).
- [x] Cada prueba con nombre que diga qué comprueba.

### paso-3 (la prueba que prueba: romper el código a propósito)

- [x] Elegir una prueba que protege algo que te importe (p. ej. `--simular` no toca el disco).
- [x] Romper el código a propósito (19-11, a mano): en `Mover.preparar` se quitó el
      `.mkdir` de la línea → quedó `self._destino_final(destino)(parents=True,
      exist_ok=True)` → `TypeError: 'WindowsPath' object is not callable` (`acciones.py:390`).
- [x] `uv run pytest` → **7 en ROJO** de 174: `test_menu_propone_la_carpeta_del_json`
      (test_cli, `exit_code` 1 en vez de 0) y 6 de `test_usuario` (`tu_origen_manda`,
      `tu_destino_manda`, `sin_nada_tuyo_manda`, `extensiones_entran_en_filtros`,
      `la_opcion_de_la_cli_manda`, `extensiones_no_tochan`). La batería
      (`pruebas/ejecutartareas.bat`) lo confirmó: 48 pasos, 4 fallos (pytest + los 3 de
      `mover` real: primera vuelta, segunda vuelta y nombre repetido).
- [x] Detalle a guardar: `--simular` siguió **VERDE** (el `if not simular` salta la
      línea): esta línea la protegen las pruebas de movimiento real, no las de simulación.
- [x] `git restore src/tareas/acciones.py` → **174 passed** otra vez (verificado 19-11).
- [x] Apuntado en `docs/prompts.md` (Prompt 22).

### paso-4 (la IA sin red: ProveedorFalso)

- [x] `tests/test_ia.py`: `a_nombre_seguro` con parametrize (tildes, rutas peligrosas,
  extensión duplicada, vacío), 401/429/formato raro → mensaje humano, y
  `test_proveedor_centro_no_llega_a_una_url_muerta_da_4` (con `http://127.0.0.1:9/v1`
  → «No llego»). Además `test_acciones_ia.py`: respuesta vacía del modelo y
  `--simular` con `modelo_falso.llamadas == []`; resumir con `modelo_falso` escribe
  el `.md` con la cabecera y el `<documento>`; sin-clasificar fuera de lista.
- [x] `tests/test_acciones_ia.py`: resumir/renombrar-ia/clasificar con `ProveedorFalso`;
  `--simular` no pregunta al modelo; inyección → «saltado» o «sin-clasificar».
- [x] Camino feliz de `resumir` con `modelo_falso`: el `.resumen.md` se escribe, la
  cabecera y el `<documento>` en la pregunta (19-11, ADR-0015).
- [x] Sin red, sin clave y sin gastar un token: ningún test sale al servidor.
- [x] El modelo REAL solo se prueba con `cliWork comprobar-ia` (fuera de pytest).

### paso-5 (la CLI desde fuera: CliRunner, códigos 0-4)

- [x] `tests/test_cli.py` con `typer.testing.CliRunner`.
- [x] Una prueba por código de salida: `test_codigo_0_todo_va_bien`, `_1_` (acción inexistente),
  `_2_` (mal uso), `_3_` (JSON roto), `_4_` (sin config de IA).
- [x] Comprueba `exit_code` y una frase de `r.output` (sin traceback).

### paso-6 (GitHub Actions en tres sistemas)

- [x] `.github/workflows/pruebas.yml` creado: matriz `ubuntu-latest`, `macos-latest`,
  `windows-latest` con `fail-fast: false`, `checkout`, `setup-uv` (Python 3.12) y `uv run pytest`.
- [x] Commit de `.github/workflows/pruebas.yml` (ya está en el repo; verificado 19-11:
      ya no aparece `?? .github/` en `git status`).
- [ ] Push y abrir la pestaña **Actions**: las tres máquinas en verde.
- [ ] Si algo se pone en rojo en Windows o macOS: leer el error y arreglar (las 6 reglas
      multiplataforma). Ese arreglo es uno de los mejores commits de la semana.

### paso-7 (opencode run: scripts/revisar.sh)

- [x] `scripts/revisar.sh`: diff por la entrada estándar, `--agent revisor`, `timeout 180`,
  veredicto convertido en código de salida (0/1).
- [x] Sin `--auto`: los permisos exactos viven en `opencode.json` (`uv run pytest *`).
- [ ] (Opcional) Borrador del CHANGELOG con `opencode run --agent plan` y `>` a un fichero,
      auditado a mano antes de pegarlo (el borrador del ejemplo traía 3 errores:
      inventaba cosas, incluía `/nueva-accion` y venía con marcas).

### paso-8 (release: rama, PR, CHANGELOG y etiqueta v1.0.0)

Estado verificado 19-11 (tras el paso 3): `CHANGELOG.md` ya tiene las entradas
`[1.0.0]` y `[1.1.0]`, y el repo está casi todo commiteado (último commit:
«guardado antes de paso 3»); solo quedan sin commitear los docs de hoy
(`SESION-04.md`, `prompts.md`). Pero **no hay ninguna etiqueta git**
(`git tag` vacío), no existe la rama `release-1.0` ni PR.

- [ ] Commits pequeños en `main`/`Sesion-4`, uno por pieza (ver lista abajo).
- [ ] `git switch -c release-1.0` con CHANGELOG, README y versión.
- [ ] OJO: la versión en `pyproject.toml` y `__init__.py` ya está en **1.1.0**; la rúbrica
      pide la etiqueta `v1.0.0`. Decidir y dejarlo coherente (etiquetar el commit que fue
      1.0.0, o subir todo a 1.0.0 si aún no se publicó nada).
- [ ] `gh pr create --fill` → PR con las tres pruebas en verde → `gh pr merge --merge`.
- [ ] `git tag -a v1.0.0 -m "..."` + `git push --tags`.
- [ ] `gh release create v1.0.0 --title "cliWork 1.0.0" --notes-file CHANGELOG.md`.
- [ ] README: se instala con **una orden desde GitHub**:
      `uv tool install git+https://github.com/JuanMTF/cli-tareas@v1.0.0` y
      `cliWork version` debe decir `1.0.0` (hoy solo está `uv tool install .` y `git clone`).

### paso-9 (instalación cruzada: la prueba de otra persona)

- [ ] Por parejas (mejor con otro sistema): intercambiar solo la URL del repo.
- [ ] La otra persona instala con la orden del README desde otra carpeta:
      `cliWork --help` y `cliWork version`.
- [ ] Copia un `acciones.json`, cambia rutas a SU carpeta y ejecuta `--simular`.
- [ ] Prueba una acción con IA y otra sin red. ¿Se entienden los mensajes?
- [ ] Issues de la otra persona (`gh issue create`): qué hizo, qué esperaba, qué pasó.
- [ ] Arreglar con una prueba que lo demuestre → v1.0.1 → cerrar el issue.

## La rúbrica: hoja de ruta al 10,0

### Los 4 mínimos (si falla uno, no se evalúa)

- [ ] Se instala siguiendo el README y `--help` funciona. *(comprobar con la orden de GitHub)*
- [ ] Al menos 3 acciones propias en `acciones.json` funcionan. *(hecho: hay muchas más)*
- [ ] Ninguna clave ni secreto en el repo ni en su historial. *(revisar: `git log --all -- .env`)*
- [ ] Historial git real: mínimo 10 commits con mensajes que cuentan el proceso. *(hecho:
      hay más de 15; revisar que los de esta semana también queden)*

### Los dos criterios que se juegan enteros esta semana (25 puntos)

**Pruebas y calidad · 15 · Excelente (100 %) exige:**

- [ ] Camino feliz + **3 casos feos** con pytest. *(hecho: 176 pruebas; auditadas en
      ADR-0015 y completadas hoy con Prompt 23: capa IA sin red ni tokens)*
- [ ] En carpetas temporales, nunca sobre ficheros reales. *(hecho: fixture `aislado`)*
- [ ] Ejecutadas en **GitHub Actions** en los 3 sistemas. *(falta paso-6)*
- [ ] **Auditadas por ti**: sabes explicar cada `assert` y qué cambio lo pondría en rojo.
      *(paso-3 hecho 19-11: mutación de `Mover.preparar` → 7 en rojo; falta repasar los asserts)*

**Instalación, documentación y proceso · 10 · Excelente (100 %) exige:**

- [ ] Se instala con una orden siguiendo el README (desde GitHub, no desde la carpeta).
- [ ] Release **v1.0 etiquetada** con changelog. *(falta paso-8: no hay tags)*
- [ ] Historial con **ramas y PR legibles**. *(falta el PR de release)*

### Los demás criterios: ya están; hay que DEMOSTRARLOS en la defensa

| Criterio | Peso | Qué mira el profesor |
|---|---|---|
| Acciones predefinidas | 20 | 5+ acciones útiles, combinables, sin efectos sorpresa (`--simular` o confirmación) |
| Configuración externa | 15 | Añadir acción sin tocar código + ADR-0001 |
| Capa IA, secretos, sin red | 15 | 2+ acciones con IA; sin clave en el historial; sale con 4 y sigue sin IA |
| Robustez | 15 | Excepciones propias, mensajes humanos, ningún traceback previsible |
| Diseño | 10 | Interfaz, motor, acciones y proveedor separados |

Preguntas de defensa (repasar): por qué el JSON (ADR-0001), qué viaja por la red,
qué pasa sin red (sale con 4), **qué comprueba un `assert` que te señalo**,
por qué un ProveedorFalso, y qué corregiste de lo que hizo el agente.

## Commits de la semana (lista de la guía)

- [ ] `pytest` como dependencia de desarrollo y `conftest` con carpeta temporal y modelo falso.
- [ ] Pruebas de config y acciones: casos feos en `tmp_path`, nunca en mis carpetas.
- [ ] Prueba de `a_nombre_seguro`: quitaba mal la extensión que añade el modelo.
- [ ] Pruebas de la CLI con CliRunner: códigos de salida 0, 1, 2, 3 y 4.
- [ ] GitHub Actions: pytest en Ubuntu, Windows y macOS en cada push.
- [ ] `scripts/revisar.sh`: el revisor con `opencode run` antes de cada commit.
- [ ] CHANGELOG revisado a mano, README con la orden de instalación y versión 1.0.0.

*(Los hace el responsable tras revisar el código, como en las sesiones anteriores.)*

## Secciones extra de la guía

- [x] #producto — al acabar la semana (qué debe haber en el repo)
- [x] #por-que — por qué pruebas automáticas y cómo funciona pytest
- [x] #metodo — el método: plan → build → audita → commit
- [x] #checklist — checklist de la semana (repasar al final)
- [x] #rubrica — rúbrica entera (los dos criterios de la semana: 25 puntos)
- [ ] #despues — qué viene después (con la v1.0.0 se cierra el proyecto 2)

## Notas

- (19-nov) Estado de partida verificado ejecutando: **172 tests en verde**
  (`uv run pytest -q`, 12,57 s). Hechos los pasos 1, 2, 4, 5 y 7: `conftest.py`
  completo (aislado autouse, descargas, escribir_config, ProveedorFalso),
  `test_config`, `test_acciones`, `test_ia`, `test_acciones_ia`, `test_cli`
  (códigos 0-4) y `scripts/revisar.sh`.
- (19-nov) Release, estado real tras el paso 3: `.github/workflows/pruebas.yml` YA está
  commiteado (en `412d812`, que aún **no está push** → Actions no ha corrido); **no hay
  ninguna etiqueta git** (`git tag` vacío), no existe la rama `release-1.0` ni PR, y la
  versión en `pyproject.toml` ya es `1.1.0` mientras la rúbrica pide `v1.0.0`: decidir
  cómo se cuadra antes del viernes 20.
- (19-nov) README: la instalación es `uv tool install .` (local); para el criterio
  «Excelente» hace falta la orden `uv tool install git+https://github.com/JuanMTF/cli-tareas@v1.0.0`.
- (19-nov) Paso-3 HECHO y documentado (Prompt 22 en `docs/prompts.md`): mutación de
  `Mover.preparar` → **7 tests en rojo** de 174 (más 4 pasos de la batería); `--simular`
  siguió verde porque el guard salta la línea. Restaurado con `git restore` → 174 passed.
  Es lo que más pesa en «auditadas por ti» de la rúbrica.
- (19-nov) Repo casi limpio tras el paso 3: solo `SESION-04.md` y `prompts.md` están
  modificados (los docs de hoy); el resto ya está commiteado hasta «guardado antes de
  paso 3» (rama `ahead 1`: falta push). Pasar los docs por el revisor y commitear.
- (19-nov) Prompt 21 + ADR-0015: auditoría del `escribir_config` del profe (no se
  sustituye: doble envoltura con dicts y `ensure_ascii` rompería/desvirtuaría 4
  tests) y de la tabla «fixtures y quién las pide» (describe la suite del profe, no
  esta). Fixes aplicados: camino feliz de `resumir` con `modelo_falso` (era código
  muerto), `resumir --simular` con `proveedor_que_rompe`, y firma limpia en
  `test_codigo_3_json_roto`. **174 passed**. Ficheros: `tests/test_acciones_ia.py`,
  `tests/test_cli.py`, `adr/0015-…`, `prompts.md`.
