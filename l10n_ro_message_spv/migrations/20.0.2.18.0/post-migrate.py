# Copyright (C) 2026 Terrabit
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

import logging

from odoo import SUPERUSER_ID, api

_logger = logging.getLogger(__name__)

BATCH_SIZE_PARAM = "l10n_ro_message_spv.migration_batch_size"
DEFAULT_BATCH_SIZE = 500


def migrate(cr, version):
    """Link the received SPV messages left without an invoice to their
    vendor bill, with the matching fixed in 20.0.2.18.0: a message with
    code 751 (in_receipt) now finds the regular vendor bill, and an empty
    draft no longer hides the real bill. The same as pressing "Get
    Invoice" on every unlinked received message."""
    if not version:
        return
    env = api.Environment(cr, SUPERUSER_ID, {"tracking_disable": True})
    batch_size = (
        env["ir.config_parameter"].sudo().get_int(BATCH_SIZE_PARAM)
        or DEFAULT_BATCH_SIZE
    )

    messages = env["l10n.ro.message.spv"].search(
        [
            ("invoice_id", "=", False),
            ("message_type", "in", ("in_invoice", "in_receipt")),
            ("ref", "!=", False),
        ]
    )
    total = len(messages)
    for start in range(0, total, batch_size):
        batch = messages[start : start + batch_size]
        for company, company_messages in batch.grouped("company_id").items():
            if company:
                company_messages = company_messages.with_company(company)
            company_messages.get_invoice_from_move()
        env.invalidate_all()
    linked = messages.filtered("invoice_id")
    _logger.info(
        "SPV messages linked to their vendor bill: %s of %s unlinked "
        "received messages (%s of them with code 751).",
        len(linked),
        total,
        len(linked.filtered(lambda m: m.message_type == "in_receipt")),
    )
