# Evidencia 12 - Diagnostico de conectividad hacia OpenSky

**Fecha:** 2026-08-25  
**Punto del plan:** diagnostico de conectividad externa hacia `opensky-network.org`

## Objetivo

Acotar la causa del timeout ya conocido al consultar OpenSky desde el entorno de Google Cloud, mediante una prueba comparativa desde dos origenes distintos.

## Prueba comparativa

| Origen | Resultado |
|---|---|
| Cloud Shell (Google Cloud) | `http_code=000` - conexion nunca establecida, timeout a 20 s |
| Red residencial | El servidor responde (`http_code=403` en la raiz del sitio) |

## Interpretacion

Un `http_code=000` significa que no hubo respuesta HTTP de ningun tipo: no es limite de tasa (daria `429`) ni restriccion de endpoint (`401`/`403`). El servidor si responde desde una red residencial, por lo que la causa no esta en la configuracion del servicio desplegado.

El pendiente tecnico pasa de "algo falla en nuestra configuracion" a "la fuente externa no acepta trafico desde nuestro proveedor de nube" - una restriccion externa, diagnosticada con evidencia comparativa.

## Limite del diagnostico

La evidencia no permite afirmar la causa raiz especifica (bloqueo dirigido, politica de red del proveedor u otra). Solo permite afirmar que la conexion directa por `curl` desde Cloud Shell hacia `opensky-network.org` no se establece en el momento de la prueba.

## Verificacion adicional 2026-08-25 - el snapshot en `live_flights` no es ingesta activa

Una primera lectura de `live_flights` parecia mostrar datos reales entrando de forma activa (aeronaves sobre Bolivia, Paraguay y Ecuador). Dos verificaciones adicionales descartan esa lectura:

**1. La posicion de esas aeronaves no cambia entre consultas.** Dos llamadas a `/live/flights?limit=5` con ~10 minutos de diferencia devolvieron, para los mismos `icao24` (`e94c8e`, `e8810a`, `e84071`), el mismo `observed_at` y las mismas coordenadas/velocidad exactas. Solo `processed_at` avanzaba. Una aeronave real en vuelo no permanece en la misma posicion 10 minutos: es un snapshot antiguo que algo sigue reescribiendo, no una posicion fresca.

**2. Los logs del productor solo muestran invocaciones periodicas, sin distincion de resultado.**

```bash
gcloud logging read 'resource.type="cloud_run_revision" AND resource.labels.service_name="opensky-producer"' \
  --project=flighttracker-505314 \
  --limit=20 \
  --format="table(timestamp, textPayload)"
```

Las ultimas 20 entradas (ventana 21:15-22:00 UTC) muestran `GET / HTTP/1.1" 200` cada 5 minutos - esa es la ruta que hace el fetch a OpenSky y publica a Pub/Sub, no un healthcheck aparte.

## Causa raiz confirmada 2026-08-25 - el servicio desplegado no coincide con el codigo versionado

Invocacion directa del productor:

```bash
curl -sS https://opensky-producer-sxdhziwvca-uc.a.run.app/
```

```json
{"duration_ms":2431,"observed_at":1787666730,"schema_version":"opensky.state.v1","source":"opensky (snapshot)","states_published":13155,"states_received":13155,"states_skipped":0,"status":"success","topic":"opensky-states-v1"}
```

El campo `"source":"opensky (snapshot)"` no existe en ninguna version de `pipelines/streaming/productor_opensky/main.py` (ni `pipelines/streaming/opensky_producer/main.py` antes del renombre) - se reviso todo el historial de git del archivo y el codigo versionado siempre publica `"source": "opensky"` sin sufijo, obteniendo los datos con un fetch en vivo, sin ningun mecanismo de snapshot ni de reintento.

**Esto significa que el servicio `opensky-producer` desplegado en Cloud Run ejecuta codigo distinto al que esta en el repositorio.** En algun momento se desplego una version parcheada (probablemente con `gcloud run deploy` desde codigo local, sin comitear) que agrega un mecanismo de respaldo: cuando el fetch real a OpenSky falla, en vez de devolver error, reproduce un snapshot estatico guardado (13.155 estados, `observed_at=1787666730` fijo) y lo publica igual, etiquetandolo como `opensky (snapshot)`. Esto explica el `200 success` constante, la cifra identica de estados y el `observed_at` congelado.

**Consecuencia para reproducibilidad:** si el servicio `opensky-producer` se redespliega desde el codigo del repositorio (por ejemplo durante una validacion desde clon nuevo), este mecanismo de respaldo desaparece y `live_flights` dejaria de recibir incluso el snapshot de respaldo, porque no esta versionado.

**Nota sobre la cifra de `/live/count`:** el endpoint esta implementado en `backend/api/get_flights/main.py` como `list_live_flights(500)` seguido de `len(results)` - es decir, esta topeado en 500 y no es un conteo real de la coleccion. El resultado debe leerse como "al menos 500 documentos", nunca como una cifra exacta.

## Estado

**Diagnosticado con causa raiz confirmada** para Sprint 1: la conectividad real hacia OpenSky sigue sin funcionar (`curl` directo da `http_code=000`). El servicio desplegado no se queda sin datos porque ejecuta una version parcheada, no versionada, que reproduce un snapshot estatico como respaldo transparente (`source: "opensky (snapshot)"`) - no es ingesta activa ni prueba de conectividad resuelta. Pendientes para Sprint 2: comitear (o retirar) ese mecanismo de respaldo para que el repositorio refleje lo que realmente esta desplegado, resolver la conectividad real (posiblemente configurando `OPENSKY_USERNAME`/`OPENSKY_PASSWORD`, que hoy nunca se configuran en ningun script de despliegue), corregir `/live/count`, y decidir si el snapshot de respaldo se documenta como comportamiento intencional o se elimina.
