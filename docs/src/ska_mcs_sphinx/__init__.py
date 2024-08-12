from . import ska_tables


def setup(app):
    app.add_directive("ska-tables", ska_tables.SkaTables)
    return {"version": "0.1.0"}
