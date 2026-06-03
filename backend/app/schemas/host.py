from pydantic import BaseModel, ConfigDict, Field


class HostCreate(BaseModel):
    branch_id: int | None = None
    name: str = Field(min_length=1, max_length=128)
    hostname: str = Field(min_length=1, max_length=255)
    username: str = Field(min_length=1, max_length=128)
    password: str = Field(min_length=1)
    port: int = 443
    verify_ssl: bool = False
    active: bool = True
    snmp_enabled: bool = False
    snmp_community: str | None = None
    snmp_port: int = 161


class HostUpdate(BaseModel):
    branch_id: int | None = None
    name: str | None = None
    hostname: str | None = None
    username: str | None = None
    password: str | None = None
    port: int | None = None
    verify_ssl: bool | None = None
    active: bool | None = None
    snmp_enabled: bool | None = None
    snmp_community: str | None = None
    snmp_port: int | None = None


class HostOut(BaseModel):
    id: int
    branch_id: int | None
    branch_name: str | None = None
    name: str
    hostname: str
    username: str
    port: int
    verify_ssl: bool
    active: bool
    snmp_enabled: bool
    snmp_community: str | None
    snmp_port: int

    model_config = ConfigDict(from_attributes=True)
