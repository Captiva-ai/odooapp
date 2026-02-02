# -*- coding: utf-8 -*-

from odoo import models
from odoo.tools import float_round


class ProductProduct(models.Model):
    _inherit = "product.product"

    def _compute_bom_price(self, bom, boms_to_recompute=False, byproduct_bom=False):
        self.ensure_one()
        if not bom:
            return 0
        if not boms_to_recompute:
            boms_to_recompute = []

        total = 0
        for opt in bom.operation_ids:
            if opt._skip_operation_line(self):
                continue
            duration_expected = (
                opt.workcenter_id._get_expected_duration(self)
                + opt.time_cycle * 100 / opt.workcenter_id.time_efficiency
            )
            total += (duration_expected / 60) * opt._total_cost_per_hour()

        def _get_line_cost(line):
            if line.child_bom_id and line.child_bom_id in boms_to_recompute:
                child_total = line.product_id._compute_bom_price(
                    line.child_bom_id, boms_to_recompute=boms_to_recompute
                )
                return line.product_id.uom_id._compute_price(
                    child_total, line.product_uom_id
                ) * line.product_qty
            return (
                line.product_id.uom_id._compute_price(
                    line.product_id.standard_price, line.product_uom_id
                )
                * line.product_qty
            )

        for line in bom.bom_line_ids:
            if line._skip_bom_line(self) or line.product_id.type == "service":
                continue
            total += _get_line_cost(line)

        for line in bom.bom_line_ids:
            if line._skip_bom_line(self) or line.product_id.type != "service":
                continue
            total += _get_line_cost(line)

        if byproduct_bom:
            byproduct_lines = bom.byproduct_ids.filtered(
                lambda b: b.product_id == self and b.cost_share != 0
            )
            product_uom_qty = 0
            for line in byproduct_lines:
                product_uom_qty += line.product_uom_id._compute_quantity(
                    line.product_qty, self.uom_id, round=False
                )
            byproduct_cost_share = sum(byproduct_lines.mapped("cost_share"))
            if byproduct_cost_share and product_uom_qty:
                return total * byproduct_cost_share / 100 / product_uom_qty
        else:
            byproduct_cost_share = sum(bom.byproduct_ids.mapped("cost_share"))
            if byproduct_cost_share:
                total *= float_round(
                    1 - byproduct_cost_share / 100, precision_rounding=0.0001
                )
            return bom.product_uom_id._compute_price(total / bom.product_qty, self.uom_id)
