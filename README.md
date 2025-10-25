# Falcon Jobs Multitenant (Demo)

Estructura completa con:
- Scheduler asíncrono
- Jobs registrables (RF-015 a RF-025)
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


## 016 No admite CIDR
FalconPy para buscar hosts por un CIDR (IPv4 e IPv6), con:
FQL generado automáticamente (wildcards para IPv4 “no limpios”, tandas de OR).
Paginación de IDs (after) y lotes de detalles.
Reintentos para 401/429.
Validación exacta del CIDR en cliente con ipaddress.
DTO con los campos que te pidieron en RF-016.
Encaja en tu FalconPyAdapter (asumo que tienes self.auth_manager.get_token() y self.auth_manager.refresh_after_401()).
```
import ipaddress
import time
from typing import List, Dict, Optional, Iterable
from falconpy import Hosts, APIError

class FalconPyAdapter:
    # ---------- Cliente Hosts ----------
    def _client_hosts(self) -> Hosts:
        return Hosts(bearer_token=self.auth_manager.get_token())

    # ---------- Helpers FQL (IPv4) ----------
    def _cidr_to_wildcards_ipv4(self, cidr: str) -> List[str]:
        """
        Devuelve TODOS los patrones A.B.C.* (/24) que cubren el CIDR IPv4.
        Para /8,/16,/24 devolverá 1 patrón. Para /23, /21, /20... devolverá varios.
        """
        net = ipaddress.ip_network(cidr, strict=False)
        if net.version != 4:
            return []
        first, last = int(net.network_address), int(net.broadcast_address)
        cur = first
        res = []
        while cur <= last:
            ip = ipaddress.IPv4Address(cur)
            octs = str(ip).split(".")
            res.append(f"{octs[0]}.{octs[1]}.{octs[2]}.*")
            # siguiente /24
            base24 = ipaddress.IPv4Address(".".join(octs[:3] + ["0"]))
            cur = int(base24) + 256
        return res

    def _build_or_fql(self, field: str, values: List[str]) -> str:
        parts = [f"{field}:'{v}'" for v in values if v]
        if not parts:
            return ""
        return parts[0] if len(parts) == 1 else "(" + " , ".join(parts) + ")"

    def _add_common_filters(self, fql: str, time_window: Optional[str], status: Optional[str], platform: Optional[str]) -> str:
        out = fql or ""
        if time_window:
            out = f"{out}+last_seen:>='{time_window}'" if out else f"last_seen:>='{time_window}'"
        if status:
            out = f"{out}+status:'{status}'" if out else f"status:'{status}'"
        if platform:
            out = f"{out}+platform_name:'{platform}'" if out else f"platform_name:'{platform}'"
        return out

    # ---------- Query IDs con paginación y reintentos ----------
    def _query_ids(self, fql: str, limit: int, retries: int = 3, backoff_base: float = 1.0) -> List[str]:
        api = self._client_hosts()
        all_ids = []
        after = None
        while True:
            for attempt in range(retries):
                try:
                    resp = api.query_devices_by_filter(filter=fql, limit=limit, after=after) or {}
                    ids = (resp.get("resources")
                           or (resp.get("body", {}) or {}).get("resources")
                           or [])
                    all_ids.extend(ids)
                    meta = (resp.get("meta") or {})
                    after = ((meta.get("pagination") or {}).get("after")
                             or (meta.get("pagination") or {}).get("next"))
                    break
                except APIError as e:
                    code = getattr(e, "code", None)
                    msg = str(e)
                    if code == 401 or "Unauthorized" in msg:
                        self.auth_manager.refresh_after_401()
                        time.sleep(backoff_base * (attempt + 1))
                        continue
                    if code == 429:
                        time.sleep(backoff_base * (attempt + 1) * 2)
                        continue
                    raise
            if not after:
                break
        # dedup
        return list(dict.fromkeys(all_ids))

    # ---------- Detalles por lotes ----------
    def _get_details(self, ids: List[str], chunk: int = 100, retries: int = 3, backoff_base: float = 1.0) -> List[dict]:
        api = self._client_hosts()
        out = []
        for i in range(0, len(ids), chunk):
            sub = ids[i:i + chunk]
            for attempt in range(retries):
                try:
                    det = api.get_device_details_v2(ids=sub) or {}
                    out.extend((det.get("resources")
                                or (det.get("body", {}) or {}).get("resources")
                                or []))
                    break
                except APIError as e:
                    code = getattr(e, "code", None)
                    msg = str(e)
                    if code == 401 or "Unauthorized" in msg:
                        self.auth_manager.refresh_after_401()
                        time.sleep(backoff_base * (attempt + 1))
                        continue
                    if code == 429:
                        time.sleep(backoff_base * (attempt + 1) * 2)
                        continue
                    raise
        return out

    # ---------- Función principal ----------
    def search_devices_by_cidr(
        self,
        cidr: str,
        *,
        time_window: str = "-30d",
        page_limit: int = 1000,
        wildcards_per_batch: int = 50,
        details_chunk: int = 100,
        status: Optional[str] = None,         # ej. 'online'
        platform: Optional[str] = None        # ej. 'Windows' | 'Mac' | 'Linux'
    ) -> List[Dict]:
        """
        RF-016: Dado un CIDR (IPv4 o IPv6), devuelve hosts cuya IP cae dentro del rango.
        - IPv4: genera OR de /24 en tandas → query IDs → detalles → validación exacta.
        - IPv6: filtra por tiempo/estado/plataforma → query IDs → detalles → validación exacta.
        """
        try:
            net = ipaddress.ip_network(cidr, strict=False)
        except ValueError:
            raise ValueError(f"CIDR inválido: {cidr}")

        # 1) Construir lista de FQLs para prefiltrar IDs
        fql_list: List[str] = []

        if net.version == 4:
            # CIDR limpios → 1 wildcard
            a, b, c, d = str(net.network_address).split(".")
            if net.prefixlen == 8 and b == c == d == "0":
                base = f"local_ip:'{a}.*'"
                fql_list = [self._add_common_filters(base, time_window, status, platform)]
            elif net.prefixlen == 16 and c == d == "0":
                base = f"local_ip:'{a}.{b}.*'"
                fql_list = [self._add_common_filters(base, time_window, status, platform)]
            elif net.prefixlen == 24 and d == "0":
                base = f"local_ip:'{a}.{b}.{c}.*'"
                fql_list = [self._add_common_filters(base, time_window, status, platform)]
            else:
                # No limpio → OR de /24 en tandas
                wildcards = self._cidr_to_wildcards_ipv4(cidr)
                if not wildcards:
                    # fallback raro, pero por si acaso
                    fql_list = [self._add_common_filters("", time_window, status, platform)]
                else:
                    for i in range(0, len(wildcards), wildcards_per_batch):
                        chunk = wildcards[i:i + wildcards_per_batch]
                        base = self._build_or_fql("local_ip", chunk)
                        fql_list.append(self._add_common_filters(base, time_window, status, platform))
        else:
            # IPv6 → no hay wildcard útil. Filtra por tiempo/estado/plataforma y valida 100% en cliente
            fql_list = [self._add_common_filters("", time_window, status, platform)]

        # 2) Obtener IDs (acumulando y deduplicando)
        all_ids = set()
        for fql in fql_list:
            ids = self._query_ids(fql=fql, limit=page_limit)
            all_ids.update(ids)
        if not all_ids:
            return []

        # 3) Traer detalles y validar EXACTO contra el CIDR
        details = self._get_details(list(all_ids), chunk=details_chunk)
        results: List[Dict] = []

        for d in details:
            lip = d.get("local_ip")
            eip = d.get("external_ip")
            matched_ip = matched_field = None

            for cand, field in ((lip, "local"), (eip, "external")):
                try:
                    if cand and ipaddress.ip_address(cand) in net:
                        matched_ip, matched_field = cand, field
                        break
                except ValueError:
                    pass
            if not matched_ip:
                continue

            # DTO RF-016
            results.append({
                "sensor_id": d.get("device_id") or d.get("aid"),
                "hostname": d.get("hostname") or d.get("device_name"),
                "matched_ip": matched_ip,
                "matched_field": matched_field,  # 'local' | 'external'
                "network_interfaces": (
                    [{"interface_name": None,
                      "ip_address": lip,
                      "mac_address": d.get("mac_address")}]
                    if lip or d.get("mac_address") else []
                ),
                "status": d.get("status"),
                "last_seen": d.get("last_seen"),
                "platform": d.get("platform_name"),
                "os_version": d.get("os_version"),
                "agent_version": d.get("agent_version"),
                "tags": d.get("tags") or [],
                "groups": d.get("groups") or []
            })

        return results
```



##  CIDR a rango de ip
```
def cidr_to_fql_filter(cidr: str, field: str = "local_ip") -> str:
    """
    Construye un filtro FQL compatible para Falcon (usando wildcards o lista de IPs).
    """
    net = ipaddress.ip_network(cidr, strict=False)
    if net.num_addresses <= 16:
        ips = [str(ip) for ip in net.hosts()]
        parts = [f"{field}:'{ip}'" for ip in ips]
        return " OR ".join(parts)
    elif net.prefixlen in (8, 16, 24):
        a, b, c, _ = str(net.network_address).split(".")
        if net.prefixlen == 8: pattern = f"{a}.*"
        elif net.prefixlen == 16: pattern = f"{a}.{b}.*"
        else: pattern = f"{a}.{b}.{c}.*"
        return f"{field}:'{pattern}'"
    else:
        blocks = cidr_to_wildcards(cidr)
        parts = [f"{field}:'{w}'" for w in blocks]
        return " OR ".join(parts)
```


