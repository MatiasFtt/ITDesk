
from app.database import engine
from sqlalchemy import text

try:
    with engine.connect() as connection:
        resultado = connection.execute(text("SELECT 1"))
        print("Conexión exitosa:", resultado.scalar())

except Exception as error:
    print("Tipo de error:", type(error).__name__)
    print("Detalle:", str(error))
