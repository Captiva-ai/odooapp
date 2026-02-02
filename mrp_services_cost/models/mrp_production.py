# -*- coding: utf-8 -*-

from collections import defaultdict

from odoo import api, fields, models, _, Command
from odoo.exceptions import UserError
from odoo.tools import float_is_zero


class MrpProduction(models.Model):
    _inherit = "mrp.production"

    service_line_ids = fields.One2many(
        comodel_name="mrp.production.service.line",
        inverse_name="production_id",
        string="Services",
    )
    services_total_cost = fields.Float(
        compute="_compute_services_total_cost",
        store=True,
        digits="Product Price",
    )
    service_valuation_layer_id = fields.Many2one(
        comodel_name="stock.valuation.layer",
        readonly=True,
        copy=False,
    )

    @api.depends("service_line_ids.subtotal")
    def _compute_services_total_cost(self):
        for production in self:
            production.services_total_cost = sum(production.service_line_ids.mapped("subtotal"))

    @api.onchange("bom_id", "product_qty", "product_uom_id")
    def _onchange_bom_id_services(self):
        for production in self:
            if production.bom_id:
                production._set_service_lines_from_bom()
            else:
                production.service_line_ids = [Command.clear()]

    @api.model_create_multi
    def create(self, vals_list):
        productions = super().create(vals_list)
        for production, vals in zip(productions, vals_list):
            if production.bom_id and not vals.get("service_line_ids"):
                production._set_service_lines_from_bom()
        return productions

    def action_reload_services_from_bom(self):
        for production in self:
            if not production.bom_id:
                continue
            production._set_service_lines_from_bom()
        return True

    def write(self, vals):
        res = super().write(vals)
        if self.env.context.get("skip_service_line_update"):
            return res
        if "service_line_ids" in vals:
            return res
        if any(field in vals for field in ("bom_id", "product_qty", "product_uom_id")):
            productions = self.filtered(lambda p: p.bom_id and p.product_id and p.state == "draft")
            if productions:
                productions.with_context(skip_service_line_update=True)._set_service_lines_from_bom()
        return res

    def _set_service_lines_from_bom(self):
        for production in self:
            if not production.bom_id or not production.product_id:
                production.service_line_ids = [Command.clear()]
                continue
            factor = production.product_uom_id._compute_quantity(
                production.product_qty, production.bom_id.product_uom_id
            ) / production.bom_id.product_qty
            _boms, lines = production.bom_id.explode(
                production.product_id,
                factor,
                picking_type=production.bom_id.picking_type_id,
                never_attribute_values=production.never_product_template_attribute_value_ids,
            )
            service_commands = [Command.clear()]
            for bom_line, line_data in lines:
                if bom_line.child_bom_id and bom_line.child_bom_id.type == "phantom":
                    continue
                if bom_line.product_id.type != "service":
                    continue
                qty = bom_line.product_uom_id._compute_quantity(
                    line_data["qty"], bom_line.product_id.uom_id
                )
                service_commands.append(
                    Command.create(
                        {
                            "product_id": bom_line.product_id.id,
                            "quantity": qty,
                            "unit_cost": bom_line.product_id.standard_price,
                            "analytic_account_id": (
                                bom_line.analytic_account_id.id
                                or bom_line.product_id.product_tmpl_id.analytic_account_id.id
                            ),
                        }
                    )
                )
            production.service_line_ids = service_commands

    def _post_inventory(self, cancel_backorder=False):
        res = super()._post_inventory(cancel_backorder=cancel_backorder)
        self._create_services_valuation_layers()
        return res

    def _create_services_valuation_layers(self):
        svl_model = self.env["stock.valuation.layer"].sudo()
        for production in self:
            if production.service_valuation_layer_id:
                continue
            if float_is_zero(production.services_total_cost, precision_rounding=production.company_id.currency_id.rounding):
                continue
            qty = production.product_uom_id._compute_quantity(
                production.qty_produced, production.product_id.uom_id
            )
            if float_is_zero(qty, precision_rounding=production.product_id.uom_id.rounding):
                continue
            company = production.company_id
            value = company.currency_id.round(production.services_total_cost)
            if company.currency_id.is_zero(value):
                continue
            unit_cost = value / qty
            finished_move = production.move_finished_ids.filtered(
                lambda move: move.product_id == production.product_id and move.state == "done"
            )[:1]
            svl = svl_model.create(
                {
                    "company_id": company.id,
                    "product_id": production.product_id.id,
                    "description": _("Manufacturing Services Cost"),
                    "stock_move_id": finished_move.id if finished_move else False,
                    "stock_valuation_layer_id": finished_move.stock_valuation_layer_ids[:1].id if finished_move else False,
                    "quantity": 0.0,
                    "value": value,
                    "unit_cost": unit_cost,
                }
            )
            production.service_valuation_layer_id = svl.id
            if production.product_id.cost_method == "average":
                product = production.product_id.with_company(company.id)
                qty_svl = product.quantity_svl
                if not float_is_zero(qty_svl, precision_rounding=product.uom_id.rounding):
                    avg_cost = product.value_svl / qty_svl
                    product.with_context(disable_auto_svl=True).sudo().write(
                        {"standard_price": avg_cost}
                    )

            if production.product_id.valuation == "real_time":
                move = production._create_services_account_move(value, qty)
                svl.account_move_id = move.id

    def _create_services_account_move(self, value, qty):
        self.ensure_one()
        accounts = self.product_id.product_tmpl_id._get_product_accounts()
        stock_valuation_account = accounts.get("stock_valuation")
        if not stock_valuation_account:
            raise UserError(_("Please configure a stock valuation account for the product category."))

        stock_accounts = self.product_id.product_tmpl_id.get_product_accounts()
        stock_journal = stock_accounts.get("stock_journal")
        if not stock_journal:
            raise UserError(_("Please configure a stock journal for the product category."))

        credit_lines = self._prepare_service_credit_lines()
        debit_line = {
            "name": _("Manufacturing Services Cost"),
            "account_id": stock_valuation_account.id,
            "debit": value,
            "credit": 0.0,
            "product_id": self.product_id.id,
            "quantity": qty,
        }
        move_vals = {
            "journal_id": stock_journal.id,
            "date": fields.Date.context_today(self),
            "ref": self.name,
            "line_ids": [Command.create(debit_line)] + credit_lines,
        }
        move = self.env["account.move"].sudo().create(move_vals)
        move._post()
        return move

    def _prepare_service_credit_lines(self):
        self.ensure_one()
        overhead_account_id = int(
            self.env["ir.config_parameter"].sudo().get_param("mrp.services.overhead_account_id", 0)
        ) or False
        overhead_account = self.env["account.account"].browse(overhead_account_id) if overhead_account_id else False

        totals = defaultdict(float)
        for line in self.service_line_ids:
            account = line.account_id or overhead_account or line.product_id.product_tmpl_id.get_product_accounts().get("expense")
            if not account:
                raise UserError(
                    _("Please configure an overhead or expense account for service product %s.")
                    % line.product_id.display_name
                )
            key = (account.id, line.analytic_account_id.id if line.analytic_account_id else False)
            totals[key] += line.subtotal

        credit_lines = []
        for (account_id, analytic_id), amount in totals.items():
            if float_is_zero(amount, precision_rounding=self.company_id.currency_id.rounding):
                continue
            line_vals = {
                "name": _("Manufacturing Services Cost"),
                "account_id": account_id,
                "debit": 0.0,
                "credit": self.company_id.currency_id.round(amount),
            }
            if analytic_id:
                line_vals["analytic_account_id"] = analytic_id
            credit_lines.append(Command.create(line_vals))

        if not credit_lines:
            raise UserError(_("No service costs found to post."))

        return credit_lines
