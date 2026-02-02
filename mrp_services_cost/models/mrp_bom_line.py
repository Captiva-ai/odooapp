# -*- coding: utf-8 -*-

from odoo import fields, models


class MrpBomLine(models.Model):
    _inherit = "mrp.bom.line"

    analytic_account_id = fields.Many2one(
        comodel_name="account.analytic.account",
        string="Analytic Account",
        check_company=True,
        domain="[('company_id', 'in', (company_id, False))]",
    )
