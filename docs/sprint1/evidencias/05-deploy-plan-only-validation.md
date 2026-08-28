# Evidencia 05 - Deploy workflow validado en modo seguro

**Fecha:** 2026-08-25  
**Punto del plan:** `G2. deploy.sh`

## Comando ejecutado en Cloud Shell

```bash
bash infrastructure/scripts/deploy.sh \
  --project-id flighttracker-505314 \
  --skip-api-build
```

## Resultado validado

El script completo correctamente:

- validacion de cuenta activa de `gcloud`
- empaquetado de funciones gestionadas desde el repo
- carga de artefactos a `gs://flighttracker-function-sources`
- `terraform init`
- `terraform validate`
- `terraform plan`

El plan quedo guardado en:

```text
/home/jsospinam/Sicard/.artifacts/tfplan.dev
```

## Lectura de la evidencia

Esta evidencia confirma que `deploy.sh` sirve como workflow controlado de infraestructura para Sprint 1.

La evidencia complementaria del plan alineado con el estado validado se documenta en:

- `docs/sprint1/evidencias/06-terraform-plan-clean.md`

## Estado

- `deploy.sh`: **completado**
- workflow de plan controlado: **validado**
