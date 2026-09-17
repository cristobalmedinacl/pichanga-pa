# Pichanga Puente Alto

Página de inscripción a partidos (fútbol 7) con cartas tipo FIFA, puntos, temporada de 15 fechas, recintos de Puente Alto y panel admin.

## Cómo correrlo en Visual Studio Code

1. Copia esta carpeta `pichanga-pa` a tu computador.
2. Ábrela en VS Code: **File → Open Folder**.
3. En la terminal:

```bash
npm install
npm start
```

4. Entra a [http://localhost:3000](http://localhost:3000)

## Claves

- Admin inicial: `admin123` (cámbiala en el panel).
- Cada jugador crea su propia clave al anotarse para poder salirse.

## Qué guarda el backend

Archivo `data/db.json`:

- configuración del partido (recinto, fecha, hora, cupo, puntos)
- perfiles (nombre, foto, puntos, clave de salida)
- plantel del partido actual

## API

| Método | Ruta | Uso |
|---|---|---|
| GET | `/api/state` | Partido + plantel + recintos |
| POST | `/api/signup` | Inscribirse |
| POST | `/api/leave` | Salirse con clave |
| POST | `/api/lookup` | Recuperar foto/apodo por nombre |
| POST | `/api/admin/login` | Entrar al admin |
| GET | `/api/admin/players?pin=` | Lista de jugadores |
| POST | `/api/admin/config` | Guardar recinto/fecha/cupo |
| POST | `/api/admin/next-match` | Siguiente partido / reset a los 15 |
| POST | `/api/admin/reset-season` | Puntos a 0 |
| POST | `/api/admin/player` | Agregar jugador |
| POST | `/api/admin/player-action` | +50 / al partido / borrar |

## Estructura

```
pichanga-pa/
  public/index.html   ← frontend
  server.js           ← backend Express
  data/db.json        ← base de datos local
  package.json
```
