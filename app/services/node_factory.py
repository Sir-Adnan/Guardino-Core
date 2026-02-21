# app/services/node_factory.py
from app.models import Node, PanelType
from app.services.marzban_adapter import MarzbanAdapter
from app.services.pasarguard_adapter import PasarguardAdapter
from app.services.wgdashboard_adapter import WGDashboardAdapter

class NodeFactory:
    @staticmethod
    def get_adapter(node: Node):
        """
        این تابع، نوع نود را از دیتابیس می‌خواند و آداپتور مخصوص به آن را برمی‌گرداند.
        """
        if node.panel_type == PanelType.MARZBAN:
            return MarzbanAdapter(node)
        elif node.panel_type == PanelType.PASARGUARD:
            return PasarguardAdapter(node)
        elif node.panel_type == PanelType.WGDASHBOARD:
            return WGDashboardAdapter(node)
        else:
            raise ValueError(f"Unknown panel type: {node.panel_type}")
