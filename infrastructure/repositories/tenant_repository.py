from dataclasses import dataclass

@dataclass
class Tenant:
    id: str
    name: str
    client_id: str
    client_secret: str

class TenantRepository:
    """Repositorio de tenants (demo). Sustituir por BD real."""
    def get_active_tenants(self) -> list[Tenant]:
        # DEMO: devuelve 2 tenants ficticios
        return [
            Tenant(id="tenant-01", name="Acme Corp", client_id="ACME_CLIENT_ID", client_secret="ACME_CLIENT_SECRET"),
            Tenant(id="tenant-02", name="Umbrella Inc", client_id="UMB_CLIENT_ID", client_secret="UMB_CLIENT_SECRET"),
        ]
