# -*- coding: utf-8 -*-

from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    mrp_services_overhead_account_id = fields.Many2one(
        comodel_name="account.account",
        string="Manufacturing Services Overhead Account",
        config_parameter="mrp.services.overhead_account_id",
        domain="[('deprecated', '=', False), ('company_ids', 'in', company_id), ('account_type', 'in', ('expense', 'expense_direct_cost'))]",
    )
