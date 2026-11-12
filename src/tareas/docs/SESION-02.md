# Sesión 02 — pasos (control personal)

Guía: https://aulaenlanube.com/programacion-ia/cli/sesion-02/

Marca con `x` lo que ya tienes hecho. Lo que queda sin marcar es lo que te falta.
Al terminar cada paso, escribe la fecha entre paréntesis.

## Pasos

- [X] paso-2 (skill)
- [X] paso-3 (errores del JSON)
- [X] paso-4 (fábrica de acciones)
- [X] paso-5 (comando)
- [X] paso-6 (subagente revisor 11-11-2026)
- [ ] paso-7 (ADR)
- [ ] paso-8 (commits)

## Secciones extra de la guía

- [ ] #metodo — método de trabajo
- [ ] #checklist — checklist del profesor (repasar al final)
- [ ] #rubrica — rúbrica de evaluación
- [ ] #despues — qué hacer después

## Notas

- (12-nov) Verificado el hallazgo del revisor sobre la mutación de `accion.config`:
  aplicado el arreglo A en `src/tareas/motor.py` (Accion fresca por ejecución).
  Pendiente del informe del revisor: regex cruda (motor.py:38), «hecho» falso
  de «abrir» con 0 URLs, negativo de --antiguedad que silencia el filtro.
- (12-nov) 94 tests en verde (`uv run pytest -q --basetemp=<carpeta temporal>`).
