from __future__ import annotations

from app.connectors.arvalis import ArvalisConnector
from app.connectors.base import BaseConnector
from app.connectors.ctifl import CtiflConnector
from app.connectors.idele import IdeleConnector
from app.connectors.ifip import IfipConnector
from app.connectors.iteipmai import IteipmaiConnector
from app.connectors.itavi import ItaviConnector
from app.connectors.terres_inovia import TerresInoviaConnector
from app.models import SourceConfig


CONNECTOR_REGISTRY: dict[str, type[BaseConnector]] = {
    "arvalis": ArvalisConnector,
    "ctifl": CtiflConnector,
    "idele": IdeleConnector,
    "ifip": IfipConnector,
    "iteipmai": IteipmaiConnector,
    "itavi": ItaviConnector,
    "terres_inovia": TerresInoviaConnector,
}


def build_connector(source: SourceConfig) -> BaseConnector:
    connector_cls = CONNECTOR_REGISTRY.get(source.slug)
    if connector_cls is None:
        raise KeyError(f"Aucun connecteur enregistré pour {source.slug}")
    return connector_cls(source)
