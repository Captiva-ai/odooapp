# -*- coding: utf-8 -*-

from odoo import models


class ReportMoOverview(models.AbstractModel):
    _inherit = "report.mrp.report_mo_overview"

    def _get_report_data(self, production_id):
        data = super()._get_report_data(production_id)
        production = self.env["mrp.production"].browse(production_id)
        service_cost = production.services_total_cost
        currency = data.get("summary", {}).get("currency") or production.company_id.currency_id
        rounded_cost = currency.round(service_cost)
        if currency.is_zero(rounded_cost):
            return data

        summary = data.get("summary", {})
        summary["mo_cost"] = summary.get("mo_cost", 0.0) + rounded_cost
        summary["bom_cost"] = summary.get("bom_cost", 0.0) + rounded_cost
        summary["real_cost"] = summary.get("real_cost", 0.0) + rounded_cost
        data["summary"] = summary

        extras = data.get("extras", {})
        qty = summary.get("quantity") or 1.0
        extras["unit_mo_cost"] = currency.round(summary.get("mo_cost", 0.0) / qty)
        extras["unit_bom_cost"] = currency.round(summary.get("bom_cost", 0.0) / qty)
        extras["unit_real_cost"] = currency.round(summary.get("real_cost", 0.0) / qty)
        if production.state == "done":
            extras["total_mo_cost"] = extras.get("total_mo_cost", 0.0) + rounded_cost
            extras["total_bom_cost"] = extras.get("total_bom_cost", 0.0) + rounded_cost
            extras["total_real_cost"] = extras.get("total_real_cost", 0.0) + rounded_cost
            extras["unit_mo_cost"] = currency.round(extras["total_mo_cost"] / qty)
            extras["unit_bom_cost"] = currency.round(extras["total_bom_cost"] / qty)
            extras["unit_real_cost"] = currency.round(extras["total_real_cost"] / qty)
        data["extras"] = extras

        return data
