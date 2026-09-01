# Evidencia 01 - Conectividad OpenSky: OAuth2 y bloqueo desde GCP

**Fecha:** 2026-09-01
**Punto del plan:** Sprint 2 / cierre del pendiente tecnico heredado de `docs/sprint1/evidencias/12-diagnostico-conectividad-opensky.md`

## Objetivo

Cerrar el diagnostico abierto en la evidencia 12 de Sprint 1, que dejo tres
pendientes: resolver la conectividad real hacia OpenSky, verificar si configurar
`OPENSKY_USERNAME` / `OPENSKY_PASSWORD` resolvia el acceso, y decidir el destino
del mecanismo de respaldo no versionado.

## Punto de partida

Al reconstruir el entorno en `flighttracker-506923` desde el codigo del
repositorio, el mecanismo de respaldo descrito en la evidencia 12 desaparecio, tal
como esa evidencia anticipaba. En consecuencia `live_flights` esta vacia y el
snapshot estatico de 13.155 estados ya no se reproduce. Esto no es una regresion:
es el comportamiento correcto del codigo versionado.

## Hallazgo 1 - la autenticacion basica ya no existe

OpenSky retiro la autenticacion basica con usuario y contrasena el 18 de marzo de
2026. El acceso autenticado usa ahora el flujo OAuth2 client credentials.

Esto descarta el pendiente planteado en la evidencia 12: configurar
`OPENSKY_USERNAME` / `OPENSKY_PASSWORD` no habria resuelto el acceso en ningun
caso, porque ese esquema ya no es aceptado por el proveedor.

El productor debe migrar a OAuth2: se crea un API client en la cuenta de OpenSky,
se obtiene `client_id` y `client_secret`, y se solicita un token en
`https://auth.opensky-network.org/auth/realms/opensky-network/protocol/openid-connect/token`.
El token expira a los 30 minutos y debe cachearse y renovarse.

## Hallazgo 2 - el bloqueo es de red, no de Cloud Run

### Prueba A - conexion desde GCP

```
* Host auth.opensky-network.org:443 was resolved.
* IPv6: (none)
* IPv4: 194.209.200.34
*   Trying 194.209.200.34:443...
* connect to 194.209.200.34 port 443 from 10.88.0.3 port 59058 failed: Connection timed out
* Failed to connect to auth.opensky-network.org port 443 after 134303 ms
curl: (28)
exit code: 28
```

Contra ambos hosts de OpenSky:

```
auth: 000 en 135.774461s
api:  000 en 135.155012s
```

El DNS resuelve, pero el puerto 443 nunca abre. El fallo ocurre al establecer la
conexion TCP, antes de TLS y antes de cualquier intercambio HTTP. Forzar IPv4 con
`-4` no cambia el resultado.

### Prueba B - control con otros destinos

Desde el mismo entorno, `https://www.google.com/` y `https://github.com/`
respondieron con codigo HTTP normal en menos de 1 segundo.

La salida a internet del entorno funciona. La restriccion es especifica de
OpenSky.

### Prueba C - las mismas credenciales desde red residencial

```
$ echo "${TOKEN:0:30}..."
eyJhbGciOiJSUzI1NiIsInR5cCIgOi...
```

```json
{"time":1788298438,"states":[
  ["4401e9","EJU3980 ","Austria",1788298438,1788298438,8.505,47.2797,10066.02,false,217.62,180.41,0,null,10469.88,"0730",false,0],
  ["4401dc","EJU38QA ","Austria",1788298438,1788298438,7.2468,46.2989,10965.18,false,207.98,296.76,0.33,null,11414.76,"1000",false,0]
]}
```

Token OAuth2 obtenido y estados en vivo recibidos. El campo `icao24` (`4401e9`,
`4401dc`) corresponde a la clave natural ya definida en el modelo logico para
`live_flights`.

## Interpretacion

La evidencia 12 acoto el problema a "la fuente externa no acepta trafico desde
nuestro proveedor de nube" y dejo constancia de que no podia afirmar la causa
raiz. Las pruebas A, B y C permiten ahora afirmar dos cosas:

1. El bloqueo no es especifico de Cloud Run. Alcanza a todo el entorno de GCP
   probado, incluida Cloud Shell. Cualquier depuracion dentro de Cloud Run, Cloud
   Functions o Dataproc habria fallado igual.
2. La fuente de datos reales es viable. Las credenciales sirven y los datos
   llegan, siempre que la llamada no salga desde GCP.

La documentacion de OpenSky advierte que pueden bloquear AWS y otros hyperscalers
por abuso generalizado desde esas IPs, lo que es consistente con lo observado.

## Limite del diagnostico

No se puede afirmar si el bloqueo cubre todo el rango de Google Cloud o solo
ciertos prefijos. La prueba A se ejecuto desde Cloud Shell; una IP de salida
distinta dentro de GCP podria comportarse de otro modo. Eso es lo que evalua la
opcion 1 de abajo.

## Opciones

| # | Opcion | Ventaja | Riesgo |
|---|---|---|---|
| 1 | Cloud NAT con IP estatica de salida | Todo sigue en GCP | La IP sigue siendo de rango Google; probablemente tambien bloqueada |
| 2 | Ingestor fuera de GCP que publica a Pub/Sub | Datos reales; el resto del pipeline no cambia | Introduce un componente fuera de la nube del proyecto |
| 3 | Cambiar de fuente (FlightAware / ADS-B Exchange) | Es la mitigacion ya prevista en la matriz de riesgos de Sprint 0 | Rehacer el productor y el contrato de datos |

**Recomendacion:** opcion 2. El contrato de datos, los topicos, el proyector,
Firestore y los endpoints `/live/*` quedan intactos: solo cambia donde corre la
llamada HTTP. La opcion 1 es barata de probar y se descarta rapido si falla. La
opcion 3 queda como respaldo.

## Estado

**Diagnostico cerrado.** La fuente entrega datos reales; la restriccion es de red
desde GCP. Pendiente de Sprint 2: implementar la opcion elegida, migrar el
productor a OAuth2 y corregir `/live/count`, que sigue topeado en 500 como
senalo la evidencia 12.

## Nota de seguridad

El `client_secret` usado en las primeras pruebas quedo expuesto durante la
depuracion y fue regenerado. El vigente se almacena en Secret Manager como
`opensky-client-secret` y no aparece en el repositorio ni en esta evidencia.
