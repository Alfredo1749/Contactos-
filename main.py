"""Agenda de Contactos con Acceso Aleatorio - interfaz PyQt5 con barra lateral."""
import sys

from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtWidgets import (
    QApplication, QButtonGroup, QFormLayout, QFrame, QHBoxLayout, QLabel,
    QLineEdit, QMainWindow, QMessageBox, QPlainTextEdit, QPushButton,
    QStackedWidget, QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget,
    QAbstractItemView, QHeaderView,
)

from almacenamiento import Agenda, ErrorAgenda, TAM_REGISTRO, CAMPOS

ESTILO = """
QMainWindow, #contenido { background: #f4f6fb; }
#barra { background: #1f2a44; }
#titulo { color: #ffffff; font-size: 20px; font-weight: bold; padding: 22px 18px 4px 18px; }
#subtitulo { color: #8fa0c4; padding: 0 18px 18px 18px; }
#barra QPushButton {
    color: #c9d3ec; background: transparent; border: none;
    text-align: left; padding: 13px 18px; font-size: 14px;
    border-left: 4px solid transparent;
}
#barra QPushButton:hover { background: #2a3858; }
#barra QPushButton:checked {
    color: #ffffff; background: #2a3858; border-left: 4px solid #2ec4b6; font-weight: bold;
}
QLabel#h1 { font-size: 22px; font-weight: bold; color: #1f2a44; }
QLabel#nota { color: #5b6786; }
QLineEdit { padding: 7px; border: 1px solid #c5cde0; border-radius: 4px; background: white; }
QLineEdit:focus { border: 1px solid #2ec4b6; }
QPushButton.accion {
    background: #2ec4b6; color: white; border: none; border-radius: 4px;
    padding: 9px 16px; font-weight: bold;
}
QPushButton.accion:hover { background: #26a89b; }
QPushButton.secundario {
    background: white; color: #1f2a44; border: 1px solid #c5cde0; border-radius: 4px; padding: 9px 16px;
}
QPushButton.secundario:hover { background: #eaeef8; }
QTableWidget { background: white; border: 1px solid #c5cde0; gridline-color: #e3e8f3; }
QHeaderView::section { background: #1f2a44; color: white; padding: 6px; border: none; }
#log {
    background: #1f2a44; color: #bfeee8; font-family: Consolas, monospace;
    border: none; border-radius: 4px;
}
"""


def boton(texto, estilo="accion"):
    b = QPushButton(texto)
    b.setProperty("class", estilo)
    b.setCursor(Qt.PointingHandCursor)
    return b


class Ventana(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Agenda de Contactos - Acceso Aleatorio")
        self.resize(1000, 650)
        self.agenda = Agenda()

        raiz = QWidget()
        self.setCentralWidget(raiz)
        layout = QHBoxLayout(raiz)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        layout.addWidget(self._crear_barra())

        derecha = QWidget()
        derecha.setObjectName("contenido")
        col = QVBoxLayout(derecha)
        col.setContentsMargins(24, 20, 24, 16)
        self.paginas = QStackedWidget()
        self.paginas.addWidget(self._pagina_contactos())
        self.paginas.addWidget(self._pagina_exportar())
        self.paginas.addWidget(self._pagina_herramientas())
        self.paginas.addWidget(self._pagina_ayuda())
        col.addWidget(self.paginas, 1)

        self.consola = QPlainTextEdit()
        self.consola.setObjectName("log")
        self.consola.setReadOnly(True)
        self.consola.setMaximumHeight(95)
        col.addWidget(self.consola)
        layout.addWidget(derecha, 1)

    # ---------- Construccion de la interfaz ----------
    def _crear_barra(self):
        barra = QFrame()
        barra.setObjectName("barra")
        barra.setFixedWidth(200)
        lay = QVBoxLayout(barra)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)

        titulo = QLabel("Agenda")
        titulo.setObjectName("titulo")
        sub = QLabel("Registros de %d bytes" % TAM_REGISTRO)
        sub.setObjectName("subtitulo")
        lay.addWidget(titulo)
        lay.addWidget(sub)

        grupo = QButtonGroup(self)
        grupo.setExclusive(True)
        opciones = ["Contactos", "Exportar", "Herramientas", "Ayuda"]
        for i, texto in enumerate(opciones):
            b = QPushButton(texto)
            b.setCheckable(True)
            b.setCursor(Qt.PointingHandCursor)
            if i == 0:
                b.setChecked(True)
            grupo.addButton(b, i)
            lay.addWidget(b)
        grupo.buttonClicked[int].connect(self._cambiar_pagina)
        lay.addStretch()
        return barra

    def _cambiar_pagina(self, indice):
        self.paginas.setCurrentIndex(indice)
        if indice == 0:
            self.refrescar_tabla()

    def _pagina_contactos(self):
        w = QWidget()
        lay = QVBoxLayout(w)
        titulo = QLabel("Contactos")
        titulo.setObjectName("h1")
        lay.addWidget(titulo)

        form = QFormLayout()
        self.campos = {}
        etiquetas = {"id": "ID", "nombre": "Nombre", "telefono": "Teléfono",
                     "correo": "Correo", "ciudad": "Ciudad"}
        for nombre, largo in CAMPOS:
            edit = QLineEdit()
            edit.setPlaceholderText(f"máx. {largo} caracteres")
            self.campos[nombre] = edit
            form.addRow(etiquetas[nombre], edit)
        lay.addLayout(form)

        fila = QHBoxLayout()
        b_agregar = boton("Agregar contacto")
        b_buscar = boton("Buscar por ID", "secundario")
        b_modificar = boton("Guardar cambios", "secundario")
        b_limpiar = boton("Limpiar", "secundario")
        b_agregar.clicked.connect(self.agregar)
        b_buscar.clicked.connect(self.buscar)
        b_modificar.clicked.connect(self.modificar)
        b_limpiar.clicked.connect(self.limpiar)
        for b in (b_agregar, b_buscar, b_modificar, b_limpiar):
            fila.addWidget(b)
        fila.addStretch()
        lay.addLayout(fila)

        self.tabla = QTableWidget(0, 5)
        self.tabla.setHorizontalHeaderLabels(["ID", "Nombre", "Teléfono", "Correo", "Ciudad"])
        self.tabla.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.tabla.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.tabla.verticalHeader().hide()
        self.tabla.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.tabla.cellClicked.connect(self._llenar_desde_tabla)
        lay.addWidget(self.tabla, 1)
        return w

    def _pagina_exportar(self):
        w = QWidget()
        lay = QVBoxLayout(w)
        titulo = QLabel("Exportar")
        titulo.setObjectName("h1")
        nota = QLabel("Guarda todos los contactos en contactos.json y genera el reporte PDF "
                      "a partir de ese JSON.")
        nota.setObjectName("nota")
        nota.setWordWrap(True)
        b_json = boton("Exportar a JSON")
        b_pdf = boton("Generar reporte PDF", "secundario")
        b_json.clicked.connect(self.exportar_json)
        b_pdf.clicked.connect(self.exportar_pdf)
        for x in (titulo, nota, b_json, b_pdf):
            lay.addWidget(x, 0, Qt.AlignLeft)
        lay.addStretch()
        return w

    def _pagina_herramientas(self):
        w = QWidget()
        lay = QVBoxLayout(w)
        titulo = QLabel("Herramientas")
        titulo.setObjectName("h1")
        nota = QLabel("Revisa que contactos.dat no haya sido alterado, crea un respaldo "
                      "comprimido o consulta los datos del archivo.")
        nota.setObjectName("nota")
        nota.setWordWrap(True)
        b_int = boton("Verificar integridad")
        b_zip = boton("Crear respaldo ZIP", "secundario")
        b_inf = boton("Información del archivo", "secundario")
        b_int.clicked.connect(self.verificar)
        b_zip.clicked.connect(self.respaldo)
        b_inf.clicked.connect(self.info_archivo)
        for x in (titulo, nota, b_int, b_zip, b_inf):
            lay.addWidget(x, 0, Qt.AlignLeft)
        lay.addStretch()
        return w

    def _pagina_ayuda(self):
        w = QWidget()
        lay = QVBoxLayout(w)
        titulo = QLabel("Ayuda")
        titulo.setObjectName("h1")
        texto = QLabel("Esta sección es simulada.\n\n"
                       "• Contactos: agrega, busca por ID o modifica un contacto.\n"
                       "• Exportar: genera el JSON y el reporte PDF.\n"
                       "• Herramientas: integridad, respaldo e información del archivo.")
        texto.setObjectName("nota")
        b = boton("Acerca de", "secundario")
        b.clicked.connect(lambda: QMessageBox.about(
            self, "Acerca de", "Agenda de Contactos con Acceso Aleatorio\nLaboratorio No. 2"))
        lay.addWidget(titulo)
        lay.addWidget(texto)
        lay.addWidget(b, 0, Qt.AlignLeft)
        lay.addStretch()
        return w

    # ---------- Utilidades ----------
    def log(self, texto):
        self.consola.appendPlainText("> " + texto)

    def error(self, texto):
        self.log("ERROR: " + texto)
        QMessageBox.warning(self, "Aviso", texto)

    def info(self, texto):
        self.log(texto)
        QMessageBox.information(self, "Listo", texto)

    def datos_formulario(self):
        return {n: e.text() for n, e in self.campos.items()}

    def llenar_formulario(self, c):
        for nombre, edit in self.campos.items():
            edit.setText(str(c[nombre]))

    def limpiar(self):
        for e in self.campos.values():
            e.clear()

    def _llenar_desde_tabla(self, fila, _col):
        for i, (nombre, _) in enumerate(CAMPOS):
            self.campos[nombre].setText(self.tabla.item(fila, i).text())

    def refrescar_tabla(self):
        try:
            contactos = self.agenda.listar()
        except ErrorAgenda as e:
            self.error(str(e))
            return
        self.tabla.setRowCount(len(contactos))
        for fila, c in enumerate(contactos):
            for col, (nombre, _) in enumerate(CAMPOS):
                self.tabla.setItem(fila, col, QTableWidgetItem(str(c[nombre])))

    # ---------- Arranque ----------
    def chequeo_inicial(self):
        try:
            for aviso in self.agenda.iniciar():
                self.error(aviso)
            ok, mensaje = self.agenda.verificar_integridad()
            self.log(mensaje)
            if not ok:
                QMessageBox.critical(self, "Integridad", mensaje)
        except ErrorAgenda as e:
            self.error(str(e))
        self.refrescar_tabla()

    # ---------- Acciones de Contactos ----------
    def agregar(self):
        try:
            self.agenda.agregar(self.datos_formulario())
        except ErrorAgenda as e:
            return self.error(str(e))
        self.log(self.agenda.ultimo_acceso)
        self.limpiar()
        self.refrescar_tabla()

    def buscar(self):
        try:
            c = self.agenda.buscar(self.campos["id"].text())
        except ErrorAgenda as e:
            return self.error(str(e))
        self.llenar_formulario(c)
        self.log(self.agenda.ultimo_acceso)

    def modificar(self):
        try:
            self.agenda.modificar(self.datos_formulario())
        except ErrorAgenda as e:
            return self.error(str(e))
        self.log(self.agenda.ultimo_acceso)
        self.refrescar_tabla()

    # ---------- Acciones de Exportar ----------
    def exportar_json(self):
        try:
            n = self.agenda.exportar_json()
        except ErrorAgenda as e:
            return self.error(str(e))
        self.info(f"Se exportaron {n} contactos a contactos.json")

    def exportar_pdf(self):
        try:
            n = self.agenda.exportar_pdf()
        except ErrorAgenda as e:
            return self.error(str(e))
        self.info(f"Reporte PDF generado con {n} contactos (reporte_contactos.pdf)")

    # ---------- Acciones de Herramientas ----------
    def verificar(self):
        try:
            ok, mensaje = self.agenda.verificar_integridad()
        except ErrorAgenda as e:
            return self.error(str(e))
        self.log(mensaje)
        if ok:
            QMessageBox.information(self, "Integridad", mensaje)
        else:
            QMessageBox.critical(self, "Integridad", mensaje)

    def respaldo(self):
        try:
            nombre, original, comprimido = self.agenda.crear_respaldo()
        except ErrorAgenda as e:
            return self.error(str(e))
        self.info(f"Respaldo creado: {nombre}\n\nTamaño original: {original} bytes\n"
                  f"Tamaño comprimido (ZIP): {comprimido} bytes")

    def info_archivo(self):
        try:
            d = self.agenda.informacion_archivo()
        except ErrorAgenda as e:
            return self.error(str(e))
        si_no = lambda v: "Sí" if v else "No"
        QMessageBox.information(
            self, "Información del archivo",
            f"Archivo: {d['archivo']}\nTamaño: {d['tamano']} bytes\n"
            f"Registros: {d['registros']}\nÚltima modificación: {d['modificado']}\n"
            f"Permiso de lectura: {si_no(d['lectura'])}\n"
            f"Permiso de escritura: {si_no(d['escritura'])}")


def main():
    app = QApplication(sys.argv)
    app.setStyleSheet(ESTILO)
    ventana = Ventana()
    ventana.show()
    QTimer.singleShot(0, ventana.chequeo_inicial)
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()