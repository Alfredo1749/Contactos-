<<<<<<< HEAD
# Agenda de Contactos con Acceso Aleatorio

Laboratorio No. 2 - Manejo de archivos (Python + PyQt5).

Aplicación de escritorio que guarda contactos en un archivo de **registros de tamaño fijo**
y accede a ellos directamente con `seek()` y `tell()`, sin leer el archivo completo.

## Instalación y uso

```bash
pip install -r requirements.txt
python main.py
```

## Archivos

| Archivo | Descripción |
|---|---|
| `main.py` | Interfaz gráfica (barra lateral, PyQt5) |
| `almacenamiento.py` | Toda la lógica de archivos |
| `contactos.dat` | Registros de tamaño fijo |
| `indice.json` | Índice primario `{id: número de registro}` |
| `contactos.sha256` | Hash SHA-256 de `contactos.dat` |
| `contactos.json` / `reporte_contactos.pdf` | Exportaciones |
| `respaldo_*.zip` | Respaldo de datos e índice |

## Estructura del registro (100 bytes)

| Campo | Largo |
|---|---|
| id | 6 |
| nombre | 30 |
| teléfono | 12 |
| correo | 32 |
| ciudad | 19 |
| salto de línea | 1 |
| **Total** | **100** |

Cada campo se rellena con espacios hasta su largo. Posición de un registro = `número × 100`.

## Cómo funciona

- **Agregar:** se escribe al final del archivo y se actualizan el índice y el hash.
- **Buscar:** se consulta `indice.json`, luego `seek(registro * 100)` y se lee un solo registro.
- **Modificar:** `seek()` al registro y se sobrescribe solo ese registro.
- **Integridad:** al iniciar se recalcula el SHA-256 y se compara con `contactos.sha256`.
- **Respaldo:** ZIP con `contactos.dat` e `indice.json`, mostrando tamaño original y comprimido.
- **Errores:** archivos faltantes, corruptos o sin permisos se avisan sin cerrar la app.

El panel inferior de la ventana muestra cada `seek()` y `tell()` realizado.
=======
# Contactos-
>>>>>>> a198479427ac6ef9613546ff29c9f07d546a5dfe
