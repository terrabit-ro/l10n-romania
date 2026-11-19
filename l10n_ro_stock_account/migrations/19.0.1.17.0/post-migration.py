import logging

from odoo.tools import SQL

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    """Clear the transfer account on the moves that are not stock transfers.

    Up to 19.0.1.16.0 the transfer account kept the category stock account on
    every move whose own account was different (a reception on a location with
    its own stock account, for example), and the storage sheet read it before
    the account of the move. Only the moves between two stock locations
    (internal or transit) keep a transfer account. Plain SQL: recomputing the
    accounts of the existing moves could change the account matched on their
    journal entries.
    """
    if not version:
        return
    cr.execute(
        SQL(
            """
            UPDATE stock_move sm
               SET l10n_ro_transfer_account_id = NULL
              FROM stock_location src, stock_location dest
             WHERE sm.location_id = src.id
               AND sm.location_dest_id = dest.id
               AND sm.l10n_ro_transfer_account_id IS NOT NULL
               AND NOT (
                    src.usage IN ('internal', 'transit')
                    AND dest.usage IN ('internal', 'transit')
               )
            """
        )
    )
    _logger.info(
        "l10n_ro_stock_account: transfer account cleared on %s moves", cr.rowcount
    )
