# Falcon Jobs Multitenant (Demo)

Estructura completa con:
- Scheduler asíncrono
- Jobs registrables (RF-015 Hosts, RF-016 Detections)
- Adapter FalconPy con Auth Manager y TokenCache multiproceso
- TenantRepository de ejemplo

## Requisitos
Python 3.10+
```
pip install falconpy requests
```
*(Si no tienes falconpy, puedes comentar las partes del SDK y simular respuestas.)*

## Ejecutar (desde el directorio que contiene `falcon_app/`)
```
python -m falcon_app.scheduler.falcon_scheduler
```

## Notas
- El `TokenCache` usa `multiprocessing.Manager()` para compartir tokens entre procesos/hilos.
- Para cancelar ejecución: Ctrl+C
- Para adaptar a producción: sustituye `TenantRepository` por tu fuente real.
