from . import ska_tables


def setup(app):
    app.add_directive("ska-command-table", ska_tables.SkaTables)
    app.add_directive("hello", ska_tables.HelloDirective)
    return {"version": "0.1.0"}
