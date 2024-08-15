from . import ska_tables


def setup(app):
    app.add_directive("cbf-controller-table", ska_tables.CbfControllerTable)
    app.add_directive("cbf-subarray-table", ska_tables.CbfSubarrayTable)
    return {"version": "0.1.0"}
