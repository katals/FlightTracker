# Evidencia 04 - Bootstrap exitoso

**Fecha:** 2026-08-25  
**Punto del plan:** `G1. bootstrap.sh`

## Comando ejecutado en Cloud Shell

```bash
bash infrastructure/scripts/bootstrap.sh \
  --project-id flighttracker-505314 \
  --skip-docker-check
```

## Resultado observado

```text
[bootstrap] Active gcloud account: jsospinam@eafit.edu.co
[bootstrap] Project id      : flighttracker-505314
[bootstrap] Data region     : us-central1
[bootstrap] Batch region    : us-east1
[bootstrap] State bucket    : flighttracker-terraform-state-flighttracker-505314
[bootstrap] Terraform dir   : /home/jsospinam/Sicard/infrastructure/terraform
[bootstrap] Enabling required foundational APIs
Operation "...finished successfully."
[bootstrap] Terraform backend bucket already exists: gs://flighttracker-terraform-state-flighttracker-505314
[bootstrap] Bootstrap completed successfully.
```

## Conclusión

- `bootstrap.sh` funciona en Cloud Shell
- valida autenticación y proyecto activo
- habilita APIs fundacionales
- confirma el backend remoto de Terraform
- no crea recursos de negocio fuera de Terraform

## Estado

**Completado** para Sprint 1.
