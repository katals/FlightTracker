# Evidencia 08 - Guardrails de destroy workflow

**Fecha:** 2026-08-25  
**Punto del plan:** `G4. destroy.sh`

## Comando ejecutado en Cloud Shell

```bash
bash infrastructure/scripts/destroy.sh --help
```

## Resultado observado

La ayuda del script expone correctamente:

- `--env <dev|test|prod>`
- `--project-id <id>`
- `--allow-prod`
- `--delete-state-backend`
- `--confirm <phrase>`

Y documenta las barreras de seguridad:

- rechazo de `prod` sin `--allow-prod`
- preservacion del backend remoto por defecto
- limpieza limitada a `.artifacts/`

## Decision de validacion

No se ejecuto `terraform destroy` sobre `flighttracker-505314`, porque el propio plan indica que este workflow no debe probarse primero sobre produccion.

La validacion aceptada para Sprint 1 fue:

- implementacion del script
- revision de su interfaz
- verificacion explicita de guardrails

## Estado

**Completado** para Sprint 1 como workflow seguro documentado.
