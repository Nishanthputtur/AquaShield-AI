"""
Asset services and formatting helpers for AquaShield AI.
"""

from typing import Any

TYPE_DISPLAY_MAP = {
    "TreatmentFacility": "Treatment Facility",
    "Reservoir": "Reservoir",
    "PumpStation": "Pump Station",
    "Pipeline": "Pipeline",
    "Valve": "Valve",
}


def _display_name(asset: Any) -> str:
    """Format human-readable asset name from asset type and identifier.

    Example: "Treatment Facility C1-TF-001"
    """
    if hasattr(asset, "asset_type"):
        a_type = asset.asset_type
    elif isinstance(asset, dict):
        a_type = asset.get("type") or asset.get("asset_type", "")
    elif hasattr(asset, "type"):
        a_type = asset.type
    else:
        a_type = ""

    type_display = TYPE_DISPLAY_MAP.get(str(a_type), str(a_type))

    if hasattr(asset, "asset_name") and asset.asset_name:
        ident = asset.asset_name
    elif hasattr(asset, "asset_id") and not isinstance(asset.asset_id, int):
        ident = str(asset.asset_id)
    elif isinstance(asset, dict):
        ident = asset.get("asset_id") or asset.get("name") or ""
    elif hasattr(asset, "asset_id"):
        ident = str(asset.asset_id)
    else:
        ident = str(asset)

    return f"{type_display} {ident}".strip()
