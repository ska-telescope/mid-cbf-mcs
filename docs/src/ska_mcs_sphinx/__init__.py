from . import ska_tables


def setup(app):
    app.add_directive("generate-command-table", ska_tables.CommandTable)
    return {"version": "0.1.0"}
