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


## 2026-11-04 Comprobacion Funcionamiento Tareas: Compruebo tareas antes de empezar y esta ok, sigo sesion 2

**Herramienta:** MiM0-V2.6-F1ash Free OpenCode

**Prompt del plan (agente Build):** 
Le pido que me exolique este paso y le paso este prompt en plan
{
      "nombre": "limpiar-temporales",
      "descripcion": "Borra .tmp con más de 30 días",
      "tipo": "borrar",
      "filtro": { "patron": ".*\\.tmp$", "mas_antiguo_que_dias": 30 },
      "confirmar": true
    }
      {
      "nombre": "abertura-edge",
      "descripcion": "Abre el edge al iniciar sesion.",
      "tipo": "abre el edge y me posicion",
      "filtro": { "patron": ".*\\.tmp$", "mas_antiguo_que_dias": 30 },
      "confirmar": true
    }  esto es el patron del fichero acciones json explicamelo como lo rellenarias la ultima accion para abrir el edge de forma automatica y se abran las ventanas 1._ https://mi-es.solutions30.com 2.-http://webmail.atroningenieros.com/ 3.https://support2.epson.net/esup_v3/Login.do 4 https://support.epson-europe.com/partners/. revisalo como se aria y me lo explicas
   

**Qué corregí del plan:** Despues de la explicacion Me da la explicacion y relleno el accion. y le pido para crear rama en git para no tocar main.

**Diffs que rechacé o deshice (/undo) y por qué:** Se realiza en plan y desarrolla el codigo  esta ok

**Funcionaba a la primera:** Al hacer el test me he dado cuenta que no funciona biemn y los nombres son muy largos y dificil de recordar. Mañana me pondre en ello.

**Qué aprendí:** Es muy importante hacer los test completos para detectar fallos.


## 2026-11-05 Comprobacion Funcionamiento Tareas: Compruebo tareas antes de empezar y esta mal, sigo sesion 2

**Herramienta:** MiM0-V2.6-F1ash Free OpenCode

**Prompt del plan (agente Build):** 
Le pido que me exolique este paso y le paso este prompt en plan
le paso los errores que me da los test  se los paso con las correcciones a cambiar 
PS C:\manuales\Programar\Grado Superior\Semipresencial DAM\Programacion\Opencode pruebas\cli-tareas> uv run tareas acciones
                                Acciones de src\tareas\docs\acciones.json
┏━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃ Nombre               ┃ Tipo        ┃ Descripción                                                      ┃
┡━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┩
│ abertura-edge        │ abrir       │ Abre el edge con 4 Paginas.                                      │
│ borrar-descargas     │ mover       │ Borra de la carpeta descarga los .pdf, .exe, .Zip, .jpg ,.docx,  │
│                      │             │ con mas de 30 dias.                                              │
│ limpiar-temporales   │ borrar      │ Borra .tmp con más de 30 días                                    │
│ ordenar-descargas    │ mover       │ Mueve los PDF y documentos de Descargas a Documentos/PDF         │
│ renombrar-fotos      │ renombrar   │ Renombra fotos con su fecha: 2026-10-26_001.jpg                  │
│ transformar-pdf-html │ transformar │ transforma los Ficheros Pdf en Html, para Visualizar en el       │
│                      │             │ navegador .                                                      │
└──────────────────────┴─────────────┴──────────────────────────────────────────────────────────────────┘
PS C:\manuales\Programar\Grado Superior\Semipresencial DAM\Programacion\Opencode pruebas\cli-tareas> tareas acciones abertura-edge
Usage: tareas acciones [OPTIONS]
Try 'tareas acciones --help' for help.
╭─ Error ───────────────────────────────────────────────────────────────────────────────────────────────╮
│ Got unexpected extra argument(s) (abertura-edge)                                                      │
╰────────────────────────────────────────────────────────────────────────────────────────────────────tareas acciones abertura-edge^Cado Superior\Semipresencial DAM\Programacion\Opencode pruebas\cli-tareas>
PS C:\manuales\Programar\Grado Superior\Semipresencial DAM\Programacion\Opencode pruebas\cli-tareas> tareas acciones abertura-edge > errores.txt
Usage: tareas acciones [OPTIONS]
Try 'tareas acciones --help' for help.
┌─ Error ──────────────────────────────────────────────────────────────────────────────────────────────┐
│ Got unexpected extra argument(s) (abertura-edge)                                                     │
└──────────────────────────────────────────────────────────────────────────────────────────────────────┘
PS C:\manuales\Programar\Grado Superior\Semipresencial DAM\Programacion\Opencode pruebas\cli-tareas> tareas acciones borrar-Descarga > errores.txt
Usage: tareas acciones [OPTIONS]
Try 'tareas acciones --help' for help.
┌─ Error ──────────────────────────────────────────────────────────────────────────────────────────────┐
│ Got unexpected extra argument(s) (borrar-Descarga)                                                   │
└──────────────────────────────────────────────────────────────────────────────────────────────────────┘
PS C:\manuales\Programar\Grado Superior\Semipresencial DAM\Programacion\Opencode pruebas\cli-tareas> tareas acciones limpiar -temporales > errores.txt
Usage: tareas acciones [OPTIONS]
Try 'tareas acciones --help' for help.
┌─ Error ──────────────────────────────────────────────────────────────────────────────────────────────┐
│ No such option: -t                                                                                   │
└──────────────────────────────────────────────────────────────────────────────────────────────────────┘
PS C:\manuales\Programar\Grado Superior\Semipresencial DAM\Programacion\Opencode pruebas\cli-tareas>
 mira lo que pasa al ejecutar tareas el primer problema es que tengo qu poner tareas Acciones para encontrar lo que quiero es que sea como tarea listar . y he cambiado el nombre de abreme-edge a abrir-nav abriria por defecto conlas cuatro paginas esas si no le digo nada mas y podria ser abrir-nav -G para Google , abrir-nav -f para firefox o abrir-nav -e para edge y si añadiomos una url detras del -e, -g o -f como https://Epson.com que nos habra ahi. 

**Qué corregí del plan:** Despues de la explicacion crea ul plan y me hace tres 
¿Dónde van las opciones -g / -f / -e y la URL?
Como opción de ejecutar (Recomendado)
detras del comando 
Sin ninguna opción (-g/-f/-e), ¿qué navegador se usa?
Explorador del sistema (Recomendado) si no se pone nada se abre navegador de defecto.

¿Qué querías decir con «que sea como tareas listar» para el listado de acciones?
Aceptar un nombre opcional
esta esta mal redactada por mi parte y se cancelo

**Diffs que rechacé o deshice (/undo) y por qué:** La ia me hace varias preguntas y despues de leer las contesto.

**Funcionaba a la primera:** Al hacer el test me he dado cuenta que no funciona bien y le he pasado los fallos 

**Qué aprendí:** Es muy importante hacer los test completos para detectar fallos. 


### Prompt 2


**Herramienta:** MiM0-V2.6-F1ash Free OpenCode

**Prompt del plan (agente Build):** 
Al hacer test me da estos errores PS C:\manuales\Programar\Grado Superior\Semipresencial DAM\Programacion\Opencode pruebas\cli-tareas> tareas validar
OK: 6 acciones válidas en src\tareas\docs\acciones.json.
PS C:\manuales\Programar\Grado Superior\Semipresencial DAM\Programacion\Opencode pruebas\cli-tareas> tareas acciones
                                Acciones de src\tareas\docs\acciones.json
┏━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃ Nombre               ┃ Tipo        ┃ Descripción                                                      ┃
┡━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┩
│ abrir-nav            │ abrir       │ Abre el explorador por defecto con 4 Paginas. -e edge, -g        │
│                      │             │ google, -f firefox, -url ponemos url como Https://epson.com      │
│ borrar-descargas     │ mover       │ Borra de la carpeta descarga los .pdf, .exe, .Zip, .jpg ,.docx,  │
│                      │             │ con mas de 30 dias.                                              │
│ limpiar-temporales   │ borrar      │ Borra .tmp con más de 30 días                                    │
│ ordenar-descargas    │ mover       │ Mueve los PDF y documentos de Descargas a Documentos/PDF         │
│ renombrar-fotos      │ renombrar   │ Renombra fotos con su fecha: 2026-10-26_001.jpg                  │
│ transformar-pdf-html │ transformar │ transforma los Ficheros Pdf en Html, para Visualizar en el       │
│                      │             │ navegador .                                                      │
└──────────────────────┴─────────────┴──────────────────────────────────────────────────────────────────┘
PS C:\manuales\Programar\Grado Superior\Semipresencial DAM\Programacion\Opencode pruebas\cli-tareas> tareas ejecutar limpiar-descargas
No existe la acción: limpiar-descargas
PS C:\manuales\Programar\Grado Superior\Semipresencial DAM\Programacion\Opencode pruebas\cli-tareas> tareas ejecutar ordenar-descargas
La acción «ordenar-descargas» es de tipo «mover» y todavía no está implementado (solo «abrir»).
PS C:\manuales\Programar\Grado Superior\Semipresencial DAM\Programacion\Opencode pruebas\cli-tareas> tareas ejecutar renombrar-fotos
La acción «renombrar-fotos» es de tipo «renombrar» y todavía no está implementado (solo «abrir»).
PS C:\manuales\Programar\Grado Superior\Semipresencial DAM\Programacion\Opencode pruebas\cli-tareas> tareas transformar-pdf-html
Usage: tareas [OPTIONS] COMMAND [ARGS]...
Try 'tareas --help' for help.
╭─ Error ───────────────────────────────────────────────────────────────────────────────────────────────╮
│ No such command 'transformar-pdf-html'.                                                               │
╰───────────────────────────────────────────────────────────────────────────────────────────────────────╯
PS C:\manuales\Programar\Grado Superior\Semipresencial DAM\Programacion\Opencode pruebas\cli-tareas> tareas ejecutar transformar-pdf-html
La acción «transformar-pdf-html» es de tipo «transformar» y todavía no está implementado (solo «abrir»).
PS C:\manuales\Programar\Grado Superior\Semipresencial DAM\Programacion\Opencode pruebas\cli-tareas>  y he creado otra accion de Comprimir carpetas o ficheros de mas de 400 dias.


**Qué corregí del plan:** Despues de la explicacion leo y indica que hay un error de una coma me pide permiso para correguirlo y ya funciona

**Diffs que rechacé o deshice (/undo) y por qué:** 
La Ia encuentra el fallo y pide permiso para resolverlo 

**Funcionaba a la primera:** Al hacer el test me he dado cuenta que no funciona bien y le he pasado los fallos la ia encuentra el fallo en fichero editado por mi Acciones json y lo corrigue y ya va.

**Qué aprendí:** Es muy importante hacer los test completos para detectar fallos. La ia escribe mejor que yo.

### Prompt 3
**Herramienta:** Flint 40B free

**Prompt del plan (agente Build):** 
este es pasado por Edu y se lo paso a IA

Carga la skill acciones-json y lee @acciones.json.
Quiero validar acciones.json ANTES de ejecutar nada:
- src/tareas/errores.py con TareasError, ConfigError y AccionNoValida;
- src/tareas/config.py con cargar(ruta) -> list[dict];
- la orden «tareas validar» en src/tareas/cli.py.
No toques nada todavía: dime qué ficheros crearías o cambiarías, qué clases
y funciones tendrán y qué casos de error vas a detectar.
   

**Qué corregí del plan:** Me da el plan y lo comparo con el prompt enviado y lo ha enetendido todo , se le aprueba build

**Diffs que rechacé o deshice (/undo) y por qué:** Se realiza en plan y desarrolla el codigo pero al testear da error

**Funcionaba a la primera:** no al haceer test da error y le paso el texto a la IA

**Qué aprendí:** Es muy importante hacer los test completos para detectar fallos.

### Prompt 4
**Herramienta:** Flint 40B free

**Prompt del plan (agente Build):** 
este es pasado por Edu y se lo paso a IA

CCarga la skill acciones-json. Crea src/tareas/acciones.py y src/tareas/motor.py:
1. acciones.py: dataclass Resultado(origen, destino, estado: hecho | simulado | saltado);
   clase base abstracta Accion con ejecutar(ficheros, simular) y aplicar(fichero, n, simular)
   abstracto; fábrica Accion.desde_config(dict) con un registro de subclases (nada de
   if/elif por tipo); subclases Mover, Copiar, Renombrar y Borrar (destructiva = True).
2. motor.py: clase Motor(acciones) con seleccionar(carpeta, filtro) y
   ejecutar(nombre, carpeta, simular) -> list[Resultado]. Sin carpeta, usa "origen".
   Acción o carpeta inexistente → TareasError con mensaje humano.
Con simular=True no se toca NADA del disco (ni mkdir). Nunca sobrescribir: sufijo « (1)».
No toques cli.py y NO ejecutes ninguna acción: las pruebo yo.
Al terminar, dime qué pasa si ejecuto dos veces seguidas la misma acción de mover y por qué.
   

**Qué corregí del plan:** Desde este prompt Ha entrado en Bucle la ia da error de no implantado los comandos de mover, eliminar, le paso los errores parece que los soluciona pero no.

**Diffs que rechacé o deshice (/undo) y por qué:** no soluciona los errores la he reiniciado y he vuelto al primer prompts pero ya se ha quedado sin servicio mañana lo volvere a intentar .

**Funcionaba a la primera:** no al haceer test da error y le paso el texto a la IA y se ha bloqueado

**Qué aprendí:** Es muy importante hacer los test completos para detectar fallos. en este caso esta dando este error PS "c:\Manuales\Programar\Grado Superior\Semipresencial DAM\Programacion\Opencode pruebas\cli-tareas> tareas ejecutar borrar-descargas ~/pruebas-tareas
La acción «borrar-descargas» es de tipo «mover» y todavía no está implementado (solo «abrir»).
PS C:\Manuales\Programar\Grado Superior\Semipresencial DAM\Programacion\Opencode pruebas\cli-tareas>"

la IA no es capaz de solucionarlo.

##2026-11-06 al 08-11-2026
### Prompt 1
**Herramienta:** Flint 40B free, MiM0-V2.6-F1ash Free OpenCode

**Prompt del plan (agente Build):** 

   Errores encontrados en los test :
1 Después de recuperar los fallos:
.al ejecutar el auto completar solo va los comandos , se necesita que funcione con las opciones y las muestre. y bloquea el terminal ya no responde a los comandos se quedan en blaco y no van.
. Al testear tareas ejecutar abrir-nav -e abre el google cuando debería abrir el edge. Antes estaba funcionando ok fue al cambiar el error de https:// que nos daba desde ahi dejo de abrir edge
. Al comprimir-antiguos ¿ podemos cambiar el tiempo en menos días? 

2 pruebas después de IA hacer retoques
PS C:\Manuales> tareas.exe ejecutar comprimir-antiguos -an 10 ~/pruebas-tareas --simular
No hay ficheros que cumplan el filtro.
PS C:\Manuales> y si hay fiferos debería comprimir las carpetas y ficheros mas de 10 días en este caso y si no se pone nada debería ser ruta de defecto y 400 días.

PS C:\Manuales> tareas.exe ejecutar copiar-amtiguos -an 10 ~/pruebas-tareas --simular
No existe la acción: copiar-amtiguos. ¿Quisiste decir «copiar-antiguos»?
PS C:\Manuales>                      
y les falta opcional de directorio de salida par los dos comandos de comprimir y copiar 

al ejecutar transformar-pdf a html no da error pero crea los ficheros.
PS C:\WINDOWS\system32> tareas ejecutar transformar-pdf-html ~/documentos/pdf --simular
SIMULACIÓN: generaría «[borrador].html» para «[borrador].pdf»
SIMULACIÓN: generaría «apuntes-tema1.html» para «apuntes-tema1.pdf»
SIMULACIÓN: generaría «contrato.html» para «contrato.docx»
SIMULACIÓN: generaría «factura-octubre.html» para «factura-octubre.pdf»
SIMULACIÓN: generaría «mi fichero con espacios.html» para «mi fichero con espacios.pdf»
PS C:\WINDOWS\system32> tareas ejecutar transformar-pdf-html ~/documentos/pdf
¿Ejecutar «transformar-pdf-html» (transformar)? [y/N]: y
Transformado: «[borrador].pdf» → «[borrador].html»
Transformado: «apuntes-tema1.pdf» → «apuntes-tema1.html»
Transformado: «contrato.docx» → «contrato.html»
Transformado: «factura-octubre.pdf» → «factura-octubre.html»
Transformado: «mi fichero con espacios.pdf» → «mi fichero con espacios.html»
PS C:\WINDOWS\system32>                                        

**Qué corregí del plan:** Al hacer test he encontado que al hacer -- simular el cli no responde, y un fallo que Espera una ruta https: en los comandos de mover enviar, pienso que es debido a el comando de abrir-nav que ese si pide Http: . Tras varios copia y pega del error deja de funcionar el comando de abrir-nav y funciona ya los de mover o copiar ficheros. Se le vuelve a pegar el fallo y tras casi tres horas builg se queda colgado, Pruebo con otro Modelo con una sesion nueva y deja peor el programa tras varias horas pensado , Dejo recuperar la IA mimo y al volver a conectar ella sola ya se resuelve el fallo tras 30 min.  

**Diffs que rechacé o deshice (/undo) y por qué:** no soluciona los errores la he reiniciado y con el ultimop fallo lo ha solucionado me ha hecho varias preguntas y esta operativo menos transforma-pdf-html.
Le he vuelto ha explicar lo que debe hacer este comando , en el directorio que se le indique buscar los pdf y convertirlos en html.
le he dicho que podrian ser varios pdf en la misma ruta y me ha propuesto hacer index.html, style.css , json para poder indexarlos asi poder acceder desde la pagina principal. yo le hedicho ok pero que se debe poder actualizar los ficheros pdf en esa ruta con el comando sin tocar nada mas.

**Funcionaba a la primera:** no al haceer test da error y le paso el texto a la IA y se bloqueado y al dia siguiente ya lo ha solucionado.

**Qué aprendí:** Es muy importante hacer los test completos para detectar fallos. y nuy importante leer y entenderlos antes de pegar en la IA, porque igual puede ser que te ponga que no existe la ruta y te falta una "s" o que te este dando la solucion sin que la IA tenga culpa.


### Prompt 2
**Herramienta:** MiM0-V2.6-F1ash Free OpenCode

**Prompt del plan (agente Build):** 

   enorabuena ya van todos menos este PS C:\manuales> tareas ejecutar transformar-pdf-html C:\Users\juant\Downloads\DAM --simular
SIMULACIÓN: generaría «DATOS.html» para «DATOS.pdf»
SIMULACIÓN: generaría «Documento sin título (1).html» para «Documento sin título.pdf»
PS C:\manuales> tareas ejecutar transformar-pdf-html C:\Users\juant\Downloads\DAM
¿Ejecutar «transformar-pdf-html» (transformar)? [y/N]: y
Transformado: «DATOS.pdf» → «DATOS.html»
Transformado: «Documento sin título.pdf» → «Documento sin título (1).html»
PS C:\manuales>  qu es el de transformar-pdf-html igual esta mal expresado lo que queria era Convertir del pdf a html (crear una carpeta con el nombre del Pdf , crear un ibdex.html, crear un css ( que podria ser generico si hay muchos pdf en la misma carpeta y script para crear interactividad. lo normal es que sean manuales de impresoras. y queria hacer una base de datos con estos ficheros .                         
La ia pregunta y se opta por hacer el script y CSS generico , un index.html de pagina principal y luego los demas con paginas creadas con  pymupdf asi saca los datos del fichero como imagen y se lo incrusta el texto. Asi si funciona con word podrias crear un pdf y de ese un html. 

**Qué corregí del plan:** El plan es sacar la informacion y pegarla . le he dicho que se debe poder actualizar los ficheros en el caso que se descargue algun pdf mas con un comando como --upgrade. 

**Diffs que rechacé o deshice (/undo) y por qué:** Me pregunta tres preguntas y optamos por usar  pymupdf para crear los html 

**Funcionaba a la primera:** 

**Qué aprendí:** Es muy importante hacer los test completos para detectar fallos. y nuy importante leer y entenderlos antes de pegar en la IA, porque igual puede ser que te ponga que no existe la ruta y te falta una "s" o que te este dando la solucion sin que la IA tenga culpa.


