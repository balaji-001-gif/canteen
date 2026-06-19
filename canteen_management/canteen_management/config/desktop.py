# -*- coding: utf-8 -*-
from __future__ import unicode_literals
from frappe import _


def get_data():
    return [
        {
            "module_name": "Canteen Management",
            "category": "Modules",
            "label": _("Canteen Management"),
            "color": "#28A745",
            "icon": "octicon octicon-home",
            "type": "module",
            "description": "Manage canteen operations including menu items, orders, billing, inventory, and employee wallets.",
        }
    ]
