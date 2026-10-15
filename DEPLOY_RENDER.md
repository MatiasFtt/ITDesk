# Desplegar ITDesk en Render

## Opción recomendada: Blueprint

1. Sube el proyecto a un repositorio Git privado o público, sin incluir `.env`.
2. En Render elige **New + Blueprint** y conecta ese repositorio.
3. Render leerá `render.yaml` y preparará el servicio web y PostgreSQL.
4. Cuando Render solicite `ITDESK_ADMIN_PASSWORD`, escribe la clave para el administrador de pruebas. Para pruebas locales puedes usar `admin1234`; para un servicio público, define una clave distinta y difícil de adivinar.
5. Confirma la creación y espera a que termine el deploy. La aplicación crea las tablas y el usuario administrador al arrancar.

## Si estás creando un Web Service manualmente

Configura estos campos:

| Campo | Valor |
| --- | --- |
| Runtime / Language | Python 3 |
| Root Directory | En blanco |
| Build Command | `pip install -r requirements.txt` |
| Start Command | `uvicorn app.main:app --host 0.0.0.0 --port $PORT` |
| Health Check Path | `/health` |

También crea una base **PostgreSQL** en la misma región que el servicio y define `DATABASE_URL` con su Internal Database URL. Configura estas variables de entorno:

| Variable | Valor |
| --- | --- |
| `DATABASE_URL` | Internal Database URL de Render PostgreSQL |
| `JWT_SECRET_KEY` | Secreto aleatorio largo y privado |
| `JWT_ALGORITHM` | `HS256` |
| `JWT_EXPIRE_MINUTES` | `60` |
| `ITDESK_ADMIN_EMAIL` | `admin@itdesk.local` o el correo que prefieras |
| `ITDESK_ADMIN_PASSWORD` | Contraseña privada del administrador |

La base de datos Free de Render sirve para probar, pero expira a los 30 días. Para conservar datos, usa un plan de PostgreSQL que no expire.
