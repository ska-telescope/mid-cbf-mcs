from . import ska_tables


def setup(app):
    app.add_directive("cbf-controller-table", ska_tables.CbfControllerTable)
    app.add_directive("cbf-subarray-table", ska_tables.CbfSubarrayTable)
    app.add_directive("subscription-points-table", ska_tables.SubscriptionPointsTable)
    return {"version": "0.1.0"}
