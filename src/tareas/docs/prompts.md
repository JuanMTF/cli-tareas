# Prompts clave del proyecto

##2026-10-27 Primera orden:Comprobar funcionamiento
**Herramienta:** OpenCode 1.18.35 · modelo centro/qwen3.8-flash-next
**Prompt del plan (agente plan):** Hola 
**Qué corregí del plan:** Nada me respondio en que puedo ayudarte 
**Diffs que rechacé o deshice (/undo) y por qué:** Ninguna
**Funcionaba a la primera:** si Qué fallo le expliqué: se conecto en la ia del centro
**Qué aprendí:** Ha conectar opencode a la  ia del centro y como crear el fichero de configuracion.

## 2026-10-30 Primera orden despues configurar el proyecto: creacion proyecto
**Herramienta:** OpenCode 1.18.35 · modelo centro/qwen3.8-flash-next
**Prompt del plan (agente plan):**  es el prompt que paso el profesor para crear las rutas del proyecto:
Lee @README.md y @pyproject.toml. Quiero src/tareas/cli.py (app de Typer llamada app) y src/tareas/__main__.py con dos órdenes: version y listar [CARPETA].
No escribas código todavía: dime qué ficheros crearías, qué funciones tendría cada uno y cómo tratarías la carpeta inexistente, la vacía, los nombres con corchetes y los ficheros que no se pueden leer.

Criterio de aceptación:
- uv run tareas sin argumentos muestra la ayuda, en español y sin autocompletado.
- version imprime «tareas 0.1.0» leyendo __version__ del paquete.
- listar (por defecto la carpeta actual, acepta ~) pinta una tabla Rich: Nombre, Tipo (extensión o «carpeta»), Tamaño legible, Modificado (AAAA-MM-DD HH:MM). Carpetas primero, luego alfabético sin distinguir mayúsculas.
- Carpeta inexistente o que no es carpeta: mensaje en stderr, sin traza, código 1. Carpeta vacía: aviso en vez de tabla vacía.
- pathlib, sin os.system ni subprocess, sin dependencias nuevas. uv run python -m tareas también funciona.  

**Qué corregí del plan:** Nada  

**Diffs que rechacé o deshice (/undo) y por qué:** Ninguna

**Funcionaba a la primera:** si Qué fallo le expliqué:creo la ruta ytal cual explico el profesor

**Qué aprendí:** a defenir el criterio para que nos cree los comandos.

## 2026-10-30 Comprobacion del codigo orden:Comprobar codigo con el que ma da el profesor.

**Herramienta:** MiM0-V2.6-F1ash Free OpenCode

**Prompt del plan (agente Build):** En cli.py en esta linea en nuestro codigo sale from typing import NoReturn; y el profesor pone from typing import Annotated   explicamelo cada cosa y cual es mejor

**Qué corregí del plan:** despues de explicar se opta por las dos opciones ya que mejora el comportamiento y no influye en el resultado final.

**Diffs que rechacé o deshice (/undo) y por qué:** Ninguna

**Funcionaba a la primera:** si Qué fallo le expliqué: 

**Qué aprendí:** que hay varias formas de programar.

## 2026-10-30 Comprobacion del codigo orden:Comprobar codigo con el que ma da el profesor.

**Herramienta:** MiM0-V2.6-F1ash Free OpenCode

**Prompt del plan (agente Build):** En cli.py este es el codigo del profe  def tamano_legible(n: int) -> str:
    """Convierte bytes en texto: 532 B, 1.2 KB, 3.4 MB..."""
    if n < 1024:
        return f"{n} B"
    tamano = float(n)
    unidad = "B"
    for unidad in ("KB", "MB", "GB", "TB"):
        tamano /= 1024
        if tamano < 1024:
            break
    return f"{tamano:.1f} {unidad}"   y este el tuyo comparalos  y dime cual es mejor

**Qué corregí del plan:** Despues de la explicacion se opta por cambiar al codigo del profesor porque era mas simple y mas acorde con la norma.

**Diffs que rechacé o deshice (/undo) y por qué:** Reprogramo para poner un codigo propuesto por el profesor.

**Funcionaba a la primera:** si Qué fallo le expliqué: 

**Qué aprendí:** que hay varias formas de programar.

## 2026-10-31 Comprobacion Funcionamiento Tareas:Comprobar tareas ya instalado y en Carpetas con espacios.

**Herramienta:** MiM0-V2.6-F1ash Free OpenCode

**Prompt del plan (agente Build):** al pasasr este test de la guia ¿Y con una ruta con espacios? tareas listar "~/pruebas-tareas/carpeta con espacios" (créala antes). Ojo: entre comillas, ~ no lo expande la terminal; lo tiene que hacer tu código con expanduser().  me dice que no encuentra la carpeta pero la he creado yo , dice algo de expanduser()
   

**Qué corregí del plan:** Despues de la explicacion El agente hace comprobacion de expanduser(), y indica que esta todo ok

**Diffs que rechacé o deshice (/undo) y por qué:** Borro y vuelvo a crear carpeta y ya pasa los test ok
**Funcionaba a la primera:** no Qué fallo le expliqué: no reconocia carpeta con espacios se tubo que revisar el codigo expanduser() y ya funciono.

**Qué aprendí:** Es muy importante hacer los test completos para detectar fallos.