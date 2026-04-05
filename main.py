from scorecard.cli import app
from sandbox.cli import sandbox_app

app.add_typer(sandbox_app, name="sandbox")

if __name__ == "__main__":
    app()
