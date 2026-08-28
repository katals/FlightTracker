# Evidencia 01 - KPI batch validado en BigQuery

**Fecha:** 2026-08-25  
**Punto del plan:** KPI batch verificable

## Consulta ejecutada

```sql
SELECT
  da.iata_code AS airline,
  ao_airport.iata_code AS origin_iata,
  ad_airport.iata_code AS dest_iata,
  ao.total_flights,
  ao.on_time_flights,
  ROUND(ao.on_time_percentage, 2) AS on_time_percentage,
  ROUND(ao.avg_arr_delay, 2) AS avg_arr_delay
FROM `flighttracker-505314.flighttracker_gold.agg_on_time_performance` ao
LEFT JOIN `flighttracker-505314.flighttracker_gold.dim_airline` da
  ON ao.airline_key = da.airline_key
LEFT JOIN `flighttracker-505314.flighttracker_gold.dim_airport` ao_airport
  ON ao.origin_key = ao_airport.airport_key
LEFT JOIN `flighttracker-505314.flighttracker_gold.dim_airport` ad_airport
  ON ao.dest_key = ad_airport.airport_key
WHERE ao.total_flights >= 100
ORDER BY on_time_percentage DESC, total_flights DESC
LIMIT 10;
```

## Resultado observado

```text
+---------+-------------+-----------+---------------+-----------------+--------------------+---------------+
| airline | origin_iata | dest_iata | total_flights | on_time_flights | on_time_percentage | avg_arr_delay |
+---------+-------------+-----------+---------------+-----------------+--------------------+---------------+
| WN      | HOU         | MAF       |           110 |             107 |              97.27 |         -7.56 |
| AS      | SNA         | PDX       |           116 |             112 |              96.55 |        -14.31 |
| UA      | IAH         | FLL       |           170 |             163 |              95.88 |         -9.78 |
| WN      | SNA         | SJC       |           210 |             201 |              95.71 |         -12.5 |
| WN      | BUR         | SMF       |           186 |             178 |               95.7 |        -11.01 |
| WN      | BUR         | SJC       |           156 |             149 |              95.51 |        -14.33 |
| UA      | PHX         | IAH       |           154 |             147 |              95.45 |         -3.31 |
| UA      | IAH         | MCO       |           235 |             224 |              95.32 |        -13.49 |
| UA      | SEA         | DEN       |           128 |             122 |              95.31 |         -7.48 |
| DL      | GSP         | ATL       |           189 |             180 |              95.24 |        -13.39 |
+---------+-------------+-----------+---------------+-----------------+--------------------+---------------+
```

## Interpretacion valida para Sprint 1

- BigQuery Gold ya responde preguntas de negocio reales sobre puntualidad historica
- los joins con `dim_airline` y `dim_airport` ya producen codigos IATA interpretables
- el KPI se apoya en la reconstruccion limpia de Gold y no en la version duplicada anterior

## Estado

**Completado** para Sprint 1.
