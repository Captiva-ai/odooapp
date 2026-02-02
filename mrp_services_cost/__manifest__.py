# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    "name": "MRP Services Cost",
    "version": "18.0.1.0",
    "category": "Manufacturing",
    "summary": "Include service costs from BoM into MO valuation",
    "author": "Captiva-ai, Ramy Shalaby",
    "icon": "/mrp_services_cost/static/description/icon.png",
    "website": "",
    "license": "LGPL-3",
    "depends": ["mrp", "stock_account"],
    "data": [
        "security/ir.model.access.csv",
        "views/mrp_production_views.xml",
        "views/mrp_bom_views.xml",
        "views/product_views.xml",
        "views/res_config_settings_views.xml",
    ],
    "installable": True,
    "application": False,
}
