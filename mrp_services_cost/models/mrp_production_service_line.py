# -*- coding: utf-8 -*-

from odoo import api, fields, models


class MrpProductionServiceLine(models.Model):
    _name = "mrp.production.service.line"
    _description = "Manufacturing Service Line"

    production_id = fields.Many2one(
        comodel_name="mrp.production",
        required=True,
        ondelete="cascade",
    )
    product_id = fields.Many2one(
        comodel_name="product.product",
        required=True,
        domain=[("type", "=", "service")],
    )
    quantity = fields.Float(default=1.0, digits="Product Unit of Measure")
    uom_id = fields.Many2one(
        comodel_name="uom.uom",
        related="product_id.uom_id",
        readonly=True,
    )
    unit_cost = fields.Float(digits="Product Price")
    subtotal = fields.Float(compute="_compute_subtotal", store=True, digits="Product Price")
    account_id = fields.Many2one(comodel_name="account.account")
    analytic_account_id = fields.Many2one(comodel_name="account.analytic.account")

    @api.onchange("product_id")
    def _onchange_product_id(self):
        for line in self:
            if line.product_id:
                line.unit_cost = line.product_id.standard_price

    @api.depends("quantity", "unit_cost")
    def _compute_subtotal(self):
        for line in self:
            line.subtotal = line.quantity * line.unit_cost

    def action_reload_services_from_bom(self):
        productions = self.mapped("production_id")
        productions.action_reload_services_from_bom()
        return True
