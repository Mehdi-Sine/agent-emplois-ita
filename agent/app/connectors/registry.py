from __future__ import annotations

from app.connectors.acta import ActaConnector
from app.connectors.arvalis import ArvalisConnector
from app.connectors.armeflhor import ArmeflhorConnector
from app.connectors.astredhor import AstredhorConnector
from app.connectors.base import BaseConnector
from app.connectors.ceva import CevaConnector
from app.connectors.cnpf import CnpfConnector
from app.connectors.ctifl import CtiflConnector
from app.connectors.idele import IdeleConnector
from app.connectors.ifip import IfipConnector
from app.connectors.inov3pt import Inov3ptConnector
from app.connectors.iteipmai import IteipmaiConnector
from app.connectors.itavi import ItaviConnector
from app.connectors.terres_inovia import TerresInoviaConnector
from app.models import SourceConfig


CONNECTOR_REGISTRY: dict[str, type[BaseConnector]] = {
    "acta": ActaConnector,
    "arvalis": ArvalisConnector,
    "armeflhor": ArmeflhorConnector,
    "astredhor": AstredhorConnector,
    "ceva": CevaConnector,
    "cnpf": CnpfConnector,
    "ctifl": CtiflConnector,
    "idele": IdeleConnector,
    "ifip": IfipConnector,
    "inov3pt": Inov3ptConnector,
    "iteipmai": IteipmaiConnector,
    "itavi": ItaviConnector,
    "terres_inovia": TerresInoviaConnector,
}


def build_connector(source: SourceConfig) -> BaseConnector:
    connector_cls = CONNECTOR_REGISTRY.get(source.slug)
    if connector_cls is None:
        raise KeyError(f"Aucun connecteur enregistré pour {source.slug}")
    return connector_cls(source)
