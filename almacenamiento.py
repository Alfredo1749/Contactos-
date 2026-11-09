import hashlib
import json
import zipfile
from datetime import datetime

ARCHIVO_DATOS = "contactos.dat"
ARCHIVO_INDICE = "indice.json"
ARCHIVO_HASH = "contactos.sha256"
ARCHIVO_JSON = "contactos.json"
ARCHIVO_PDF = "reporte_contactos.pdf"

# Estructura del registro: (campo, largo en bytes)
CAMPOS = [("id", 6), ("nombre", 30), ("telefono", 12), ("correo", 32), ("ciudad", 19)]
# 6 + 30 + 12 + 32 + 19 = 99, mas 1 byte del salto de linea = 100
TAM_REGISTRO = sum(largo for _, largo in CAMPOS) + 1


class ErrorAgenda(Exception):
    """Error controlado: la interfaz lo muestra sin que la app se caiga."""


# ---------- Utilidades de registro ----------
def _ajustar(texto, largo):
    """Recorta/rellena con espacios para que el campo mida exactamente `largo` bytes."""
    datos = str(texto).strip().encode("utf-8")[:largo]
    datos = datos.decode("utf-8", "ignore").encode("utf-8")  # evita cortar un caracter a la mitad
    return datos + b" " * (largo - len(datos))


def empaquetar(contacto):
    """Convierte un contacto (dict) en un registro de TAM_REGISTRO bytes."""
    campos = b"".join(_ajustar(contacto[n], l) for n, l in CAMPOS)
    return campos + b"\n"


def desempaquetar(registro):
    """Convierte un registro de bytes en un contacto (dict)."""
    try:
        contacto, pos = {}, 0
        for nombre, largo in CAMPOS:
            contacto[nombre] = registro[pos:pos + largo].decode("utf-8").strip()
            pos += largo
        contacto["id"] = int(contacto["id"])
        return contacto
    except ValueError:
        raise ErrorAgenda("Se encontro un registro corrupto en contactos.dat.")


class Agenda:
    def __init__(self):
        self.indice = {}           # {id: numero de registro}
        self.ultimo_acceso = ""    # texto con seek()/tell() para mostrar en la interfaz

    # ---------- Inicio ----------
    def iniciar(self):
        """Prepara los archivos. Devuelve una lista de avisos para el usuario."""
        avisos = []
        self._asegurar_archivo()
        try:
            with open(ARCHIVO_INDICE, "r", encoding="utf-8") as f:
                datos = json.load(f)
            self.indice = {int(k): int(v) for k, v in datos.items()}
        except FileNotFoundError:
            self.reconstruir_indice()
            if self.indice:
                avisos.append("No existia indice.json, se reconstruyo desde contactos.dat.")
            else:
                self.guardar_indice()
        except (ValueError, AttributeError):
            self.reconstruir_indice()
            self.guardar_indice()
            avisos.append("indice.json estaba corrupto, se reconstruyo desde contactos.dat.")
        except OSError as e:
            raise ErrorAgenda(f"No se pudo leer indice.json: {e}")
        return avisos

    def _asegurar_archivo(self):
        try:
            open(ARCHIVO_DATOS, "ab").close()  # lo crea si no existe
        except OSError as e:
            raise ErrorAgenda(f"No se puede acceder a contactos.dat (permisos?): {e}")

    # ---------- Indice ----------
    def reconstruir_indice(self):
        """Recorre el archivo UNA vez para reconstruir el indice (solo en recuperacion)."""
        self.indice = {}
        try:
            with open(ARCHIVO_DATOS, "rb") as f:
                numero = 0
                while True:
                    registro = f.read(TAM_REGISTRO)
                    if not registro:
                        break
                    if len(registro) < TAM_REGISTRO:
                        raise ErrorAgenda("contactos.dat esta incompleto o corrupto.")
                    self.indice[desempaquetar(registro)["id"]] = numero
                    numero += 1
        except FileNotFoundError:
            pass
        except OSError as e:
            raise ErrorAgenda(f"No se pudo leer contactos.dat: {e}")

    def guardar_indice(self):
        try:
            with open(ARCHIVO_INDICE, "w", encoding="utf-8") as f:
                json.dump(self.indice, f, indent=2)
        except OSError as e:
            raise ErrorAgenda(f"No se pudo guardar indice.json: {e}")

    # ---------- Hash SHA-256 ----------
    def calcular_hash(self):
        sha = hashlib.sha256()
        try:
            with open(ARCHIVO_DATOS, "rb") as f:
                for bloque in iter(lambda: f.read(4096), b""):
                    sha.update(bloque)
        except OSError as e:
            raise ErrorAgenda(f"No se pudo calcular el hash: {e}")
        return sha.hexdigest()

    def guardar_hash(self):
        try:
            with open(ARCHIVO_HASH, "w", encoding="utf-8") as f:
                f.write(self.calcular_hash())
        except OSError as e:
            raise ErrorAgenda(f"No se pudo guardar contactos.sha256: {e}")

    def verificar_integridad(self):
        """Devuelve (ok, mensaje)."""
        try:
            with open(ARCHIVO_HASH, "r", encoding="utf-8") as f:
                guardado = f.read().strip()
        except FileNotFoundError:
            if not self.indice:  # agenda vacia: se crea el hash inicial
                self.guardar_hash()
                return True, "Agenda vacia: se creo el hash inicial."
            return False, "No existe contactos.sha256, no se puede verificar el archivo."
        except OSError as e:
            raise ErrorAgenda(f"No se pudo leer contactos.sha256: {e}")

        if guardado == self.calcular_hash():
            return True, "El archivo esta integro: el hash SHA-256 coincide."
        return False, "El archivo contactos.dat fue modificado fuera de la aplicacion."

    # ---------- Contactos ----------
    def _validar(self, c):
        try:
            id_ = int(str(c["id"]).strip())
        except ValueError:
            raise ErrorAgenda("El ID debe ser un numero entero.")
        if not 0 < id_ <= 999999:
            raise ErrorAgenda("El ID debe estar entre 1 y 999999.")
        limpio = {"id": id_}
        for nombre, largo in CAMPOS[1:]:
            valor = str(c[nombre]).strip()
            if len(valor.encode("utf-8")) > largo:
                raise ErrorAgenda(f"El campo '{nombre}' excede {largo} caracteres.")
            limpio[nombre] = valor
        if not limpio["nombre"]:
            raise ErrorAgenda("El nombre es obligatorio.")
        return limpio

    def agregar(self, contacto):
        c = self._validar(contacto)
        if c["id"] in self.indice:
            raise ErrorAgenda(f"Ya existe un contacto con ID {c['id']}.")
        self._asegurar_archivo()
        try:
            with open(ARCHIVO_DATOS, "r+b") as f:
                f.seek(0, 2)                      # ir al final
                fin = f.tell()
                if fin % TAM_REGISTRO != 0:
                    raise ErrorAgenda("contactos.dat esta corrupto (tamano invalido).")
                numero = fin // TAM_REGISTRO
                f.seek(numero * TAM_REGISTRO)
                f.write(empaquetar(c))
                despues = f.tell()
        except OSError as e:
            raise ErrorAgenda(f"No se pudo escribir en contactos.dat: {e}")
        self.indice[c["id"]] = numero
        self.guardar_indice()
        self.guardar_hash()
        self.ultimo_acceso = (f"AGREGAR id={c['id']} -> registro #{numero} | "
                              f"seek({numero * TAM_REGISTRO}) | tell() = {despues}")

    def buscar(self, id_):
        try:
            id_ = int(str(id_).strip())
        except ValueError:
            raise ErrorAgenda("El ID debe ser un numero entero.")
        if id_ not in self.indice:                # 1) se consulta el indice
            raise ErrorAgenda(f"No existe un contacto con ID {id_}.")
        numero = self.indice[id_]
        try:
            with open(ARCHIVO_DATOS, "rb") as f:
                f.seek(numero * TAM_REGISTRO)     # 2) salto directo al registro
                antes = f.tell()
                registro = f.read(TAM_REGISTRO)
                despues = f.tell()
        except FileNotFoundError:
            raise ErrorAgenda("No existe contactos.dat.")
        except OSError as e:
            raise ErrorAgenda(f"No se pudo leer contactos.dat: {e}")
        if len(registro) < TAM_REGISTRO:
            raise ErrorAgenda("El registro esta incompleto: el archivo fue alterado.")
        self.ultimo_acceso = (f"BUSCAR id={id_} -> indice dice registro #{numero} | "
                              f"seek({numero * TAM_REGISTRO}) | tell() = {antes} -> {despues}")
        return desempaquetar(registro)

    def modificar(self, contacto):
        c = self._validar(contacto)
        if c["id"] not in self.indice:
            raise ErrorAgenda(f"No existe un contacto con ID {c['id']}.")
        numero = self.indice[c["id"]]
        try:
            with open(ARCHIVO_DATOS, "r+b") as f:
                f.seek(numero * TAM_REGISTRO)
                f.write(empaquetar(c))            # solo se sobrescribe este registro
                despues = f.tell()
        except OSError as e:
            raise ErrorAgenda(f"No se pudo modificar contactos.dat: {e}")
        self.guardar_hash()
        self.ultimo_acceso = (f"MODIFICAR id={c['id']} -> registro #{numero} | "
                              f"seek({numero * TAM_REGISTRO}) | tell() = {despues}")

    def listar(self):
        """Lee todos los registros (solo para mostrar la tabla y exportar)."""
        contactos = []
        try:
            with open(ARCHIVO_DATOS, "rb") as f:
                while True:
                    registro = f.read(TAM_REGISTRO)
                    if not registro:
                        break
                    if len(registro) < TAM_REGISTRO:
                        raise ErrorAgenda("contactos.dat esta incompleto o corrupto.")
                    contactos.append(desempaquetar(registro))
        except FileNotFoundError:
            pass
        except OSError as e:
            raise ErrorAgenda(f"No se pudo leer contactos.dat: {e}")
        return contactos

    # ---------- Exportar ----------
    def exportar_json(self):
        contactos = self.listar()
        try:
            with open(ARCHIVO_JSON, "w", encoding="utf-8") as f:
                json.dump(contactos, f, indent=2, ensure_ascii=False)
        except OSError as e:
            raise ErrorAgenda(f"No se pudo escribir {ARCHIVO_JSON}: {e}")
        return len(contactos)

    def exportar_pdf(self):
        """Genera el PDF a partir del JSON exportado."""
        try:
            from fpdf import FPDF
        except ImportError:
            raise ErrorAgenda("Falta la libreria fpdf2. Instalela con: pip install fpdf2")

        self.exportar_json()
        try:
            with open(ARCHIVO_JSON, "r", encoding="utf-8") as f:
                contactos = json.load(f)
        except (OSError, ValueError) as e:
            raise ErrorAgenda(f"No se pudo leer {ARCHIVO_JSON}: {e}")

        def txt(valor):  # las fuentes basicas del PDF solo soportan latin-1
            return str(valor).encode("latin-1", "replace").decode("latin-1")

        pdf = FPDF()
        pdf.add_page()
        pdf.set_font("Helvetica", "B", 16)
        pdf.cell(0, 10, "Reporte de contactos", new_x="LMARGIN", new_y="NEXT", align="C")
        pdf.set_font("Helvetica", "", 10)
        fecha = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
        pdf.cell(0, 8, f"Fecha de generacion: {fecha}", new_x="LMARGIN", new_y="NEXT", align="C")
        pdf.ln(4)

        anchos = [14, 50, 28, 60, 38]
        titulos = ["ID", "Nombre", "Telefono", "Correo", "Ciudad"]
        pdf.set_font("Helvetica", "B", 10)
        for ancho, titulo in zip(anchos, titulos):
            pdf.cell(ancho, 8, titulo, border=1)
        pdf.ln()
        pdf.set_font("Helvetica", "", 9)
        for c in contactos:
            fila = [c["id"], c["nombre"], c["telefono"], c["correo"], c["ciudad"]]
            for ancho, valor in zip(anchos, fila):
                pdf.cell(ancho, 7, txt(valor), border=1)
            pdf.ln()

        try:
            with open(ARCHIVO_PDF, "wb") as f:
                f.write(pdf.output())
        except OSError as e:
            raise ErrorAgenda(f"No se pudo escribir {ARCHIVO_PDF}: {e}")
        return len(contactos)

    # ---------- Herramientas ----------
    def crear_respaldo(self):
        """Crea un ZIP con contactos.dat e indice.json. Devuelve (nombre, original, comprimido)."""
        self.guardar_indice()
        nombre = f"respaldo_{datetime.now():%Y%m%d_%H%M%S}.zip"
        try:
            with zipfile.ZipFile(nombre, "w", zipfile.ZIP_DEFLATED) as z:
                z.write(ARCHIVO_DATOS)
                z.write(ARCHIVO_INDICE)
            with zipfile.ZipFile(nombre, "r") as z:
                original = sum(i.file_size for i in z.infolist())
            with open(nombre, "rb") as f:
                f.seek(0, 2)
                comprimido = f.tell()
        except (OSError, zipfile.BadZipFile) as e:
            raise ErrorAgenda(f"No se pudo crear el respaldo: {e}")
        return nombre, original, comprimido

    def informacion_archivo(self):
        """Tamano, fecha de modificacion y permisos (aqui si se usa el modulo os)."""
        import os
        try:
            datos = os.stat(ARCHIVO_DATOS)
        except OSError as e:
            raise ErrorAgenda(f"No se pudo obtener la informacion del archivo: {e}")
        return {
            "archivo": ARCHIVO_DATOS,
            "tamano": datos.st_size,
            "registros": datos.st_size // TAM_REGISTRO,
            "modificado": datetime.fromtimestamp(datos.st_mtime).strftime("%d/%m/%Y %H:%M:%S"),
            "lectura": os.access(ARCHIVO_DATOS, os.R_OK),
            "escritura": os.access(ARCHIVO_DATOS, os.W_OK),
        }
