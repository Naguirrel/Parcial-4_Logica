"""Pruebas del programa real por terminal; no importan simulador.py."""

import itertools
import os
import re
import subprocess
import sys
import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]


def ejecutar_texto(texto, limite=1000):
    """Ejecuta el archivo completo sin cambiar su llamada directa a main()."""
    with tempfile.TemporaryDirectory() as carpeta:
        entrada = Path(carpeta) / "entrada.txt"
        salida = Path(carpeta) / "salida.txt"
        entrada.write_text(texto, encoding="utf-8")
        entorno = dict(os.environ, PYTHONIOENCODING="utf-8")
        proceso = subprocess.run(
            [sys.executable, "-B", str(RAIZ / "simulador.py"), str(entrada),
             "-o", str(salida), "--max-pasos", str(limite)],
            capture_output=True, text=True, encoding="utf-8", env=entorno,
            timeout=15,
        )
        traza = salida.read_text(encoding="utf-8") if salida.exists() else ""
        return proceso, traza


class PruebasSimulador(unittest.TestCase):
    """Valida semántica, archivos y errores mediante la interfaz de entrega."""

    @classmethod
    def setUpClass(cls):
        cls.texto = (RAIZ / "ejemplos" / "aceptacion.txt").read_text(encoding="utf-8")

    def ejecutar(self, entrada, limite=1000):
        texto = self.texto.replace("entrada: 0011", "entrada: " + entrada)
        proceso, traza = ejecutar_texto(texto, limite)
        if proceso.returncode:
            raise AssertionError(proceso.stdout + proceso.stderr)
        motivo = re.search(r"^Resultado: (.+)$", traza, re.M).group(1)
        pasos = int(re.search(r"^Transiciones ejecutadas: (\d+)$", traza, re.M).group(1))
        return {"motivo": motivo, "pasos": pasos}, traza

    def test_lenguaje_en_todas_las_cadenas_binarias_hasta_longitud_8(self):
        """Contrasta las 511 cadenas con la definición matemática del lenguaje."""
        entradas = ["".join(s) for n in range(9) for s in itertools.product("01", repeat=n)]
        # Cada proceso tiene sus propios archivos temporales. Solo son pruebas.
        with ThreadPoolExecutor(max_workers=4) as grupo:
            for entrada, (resultado, _) in zip(entradas, grupo.map(self.ejecutar, entradas)):
                n = len(entrada) // 2
                esperado = "ACEPTADA" if n >= 1 and entrada == "0" * n + "1" * n else "RECHAZADA"
                with self.subTest(entrada=entrada):
                    self.assertEqual(resultado["motivo"], esperado)

    def test_traza_exacta_de_01(self):
        """Regresa a la X recién escrita, sin visitar una posición negativa."""
        resultado, texto = self.ejecutar("01")
        configuraciones = [l for l in texto.splitlines() if l.startswith(("C0:", "⊢"))]
        self.assertEqual(configuraciones, [
            "C0: q0 01",
            "⊢ C1: X qBusca1 1",
            "⊢ C2: qRegresa XY",
            "⊢ C3: X q0 Y",
            "⊢ C4: XY qVerifica _",
            "⊢ C5: XY_ qAcepta _",
        ])
        self.assertEqual(resultado, {"motivo": "ACEPTADA", "pasos": 5})

    def test_ciclo_oscilante_y_limite(self):
        resultado, texto = self.ejecutar("2", 6)
        self.assertEqual(resultado, {"motivo": "LIMITE_ALCANZADO", "pasos": 6})
        self.assertIn("⊢ C1: 2 qIda _", texto)
        self.assertIn("⊢ C3: 2 qIda _", texto)
        self.assertIn("NO demuestra un ciclo infinito", texto)
        for entrada in ("20", "21", "22", "201", "2102"):
            with self.subTest(entrada=entrada):
                self.assertEqual(self.ejecutar(entrada, 10)[0]["motivo"], "LIMITE_ALCANZADO")

    def test_dos_fuera_de_la_primera_posicion_rechaza(self):
        for entrada in ("02", "012", "00112", "102", "0002111"):
            with self.subTest(entrada=entrada):
                self.assertEqual(self.ejecutar(entrada)[0]["motivo"], "RECHAZADA")

    def test_estado_final_tiene_prioridad_sobre_limite(self):
        self.assertEqual(self.ejecutar("01", 5)[0]["motivo"], "ACEPTADA")
        self.assertEqual(self.ejecutar("1", 1)[0]["motivo"], "RECHAZADA")
        self.assertEqual(self.ejecutar("01", 4)[0]["motivo"], "LIMITE_ALCANZADO")

    def test_limite_cero_y_negativo(self):
        resultado, texto = self.ejecutar("01", 0)
        self.assertEqual(resultado["pasos"], 0)
        self.assertNotIn("⊢ C1:", texto)
        proceso, traza = ejecutar_texto(self.texto, -1)
        self.assertNotEqual(proceso.returncode, 0)
        self.assertEqual(traza, "")

    def maquina_pequena(self, regla_inicial, regla_paso):
        """Construye otra MT para comprobar el simulador independientemente del ejemplo."""
        cabecera = (
            "estados: q0 qPaso qAcepta qRechaza\n"
            "alfabeto_entrada: 0 1\nalfabeto_cinta: 0 1 _\nblanco: _\n"
            "inicial: q0\naceptacion: qAcepta\nrechazo: qRechaza\n"
            "entrada: 0\ntransiciones:\n"
        )
        reglas = []
        for estado in ("q0", "qPaso"):
            for simbolo in "01_":
                regla = f"{estado} {simbolo} -> qRechaza {simbolo} R"
                if (estado, simbolo) == ("q0", "0"):
                    regla = regla_inicial
                if (estado, simbolo) == ("qPaso", regla_paso.split()[1]):
                    regla = regla_paso
                reglas.append(regla)
        return cabecera + "\n".join(reglas) + "\n"

    def test_movimiento_izquierdo_desde_cero(self):
        """L en 0 conserva el cabezal, pero sí escribe y cambia de estado."""
        texto = self.maquina_pequena("q0 0 -> qPaso 1 L", "qPaso 1 -> qAcepta 0 R")
        proceso, traza = ejecutar_texto(texto)
        self.assertEqual(proceso.returncode, 0, proceso.stdout + proceso.stderr)
        self.assertIn("⊢ C1: qPaso 1\n", traza)
        self.assertIn("⊢ C2: 0 qAcepta _\n", traza)
        self.assertIn("Resultado: ACEPTADA", traza)

    def test_borrado_y_blancos_iniciales(self):
        """La configuración conserva la celda 0 aunque su símbolo sea blanco."""
        texto = self.maquina_pequena("q0 0 -> qPaso _ R", "qPaso _ -> qAcepta 1 R")
        proceso, traza = ejecutar_texto(texto)
        self.assertEqual(proceso.returncode, 0, proceso.stdout + proceso.stderr)
        self.assertIn("⊢ C1: _ qPaso _\n", traza)
        self.assertIn("⊢ C2: _1 qAcepta _\n", traza)

    def test_archivos_de_ejemplo_coinciden_con_salidas(self):
        for nombre, limite in (("aceptacion", 1000), ("rechazo", 1000), ("ciclo", 12)):
            with self.subTest(nombre=nombre):
                texto = (RAIZ / "ejemplos" / f"{nombre}.txt").read_text(encoding="utf-8")
                proceso, traza = ejecutar_texto(texto, limite)
                self.assertEqual(proceso.returncode, 0)
                self.assertEqual(traza, (RAIZ / "salidas" / f"{nombre}.txt").read_text(encoding="utf-8"))

    def test_especificaciones_invalidas(self):
        casos = {
            "campo ausente": ("blanco: _\n", ""),
            "campo duplicado": ("blanco: _", "blanco: _\nblanco: _"),
            "campo desconocido": ("blanco: _", "vacio: _"),
            "sin sección": ("transiciones:", ""),
            "estado inexistente": ("inicial: q0", "inicial: qFantasma"),
            "estado inválido": ("estados: q0", "estados: 9q"),
            "estado duplicado": ("estados: q0", "estados: q0 q0"),
            "alfabeto duplicado": ("alfabeto_entrada: 0 1 2", "alfabeto_entrada: 0 1 2 0"),
            "blanco en entrada": ("alfabeto_entrada: 0 1 2", "alfabeto_entrada: 0 1 2 _"),
            "blanco fuera de cinta": ("blanco: _", "blanco: B"),
            "sigma fuera de gamma": ("alfabeto_entrada: 0 1 2", "alfabeto_entrada: 0 1 2 3"),
            "símbolo largo": ("alfabeto_cinta: 0 1 2 X Y _", "alfabeto_cinta: 0 1 2 XX Y _"),
            "entrada inválida": ("entrada: 0011", "entrada: 03"),
            "finales iguales": ("rechazo: qRechaza", "rechazo: qAcepta"),
            "regla incompleta": ("q0 0 -> qBusca1 X R", "q0 0 -> qBusca1 X"),
            "movimiento inválido": ("q0 0 -> qBusca1 X R", "q0 0 -> qBusca1 X S"),
            "destino desconocido": ("q0 0 -> qBusca1 X R", "q0 0 -> qFantasma X R"),
            "origen desconocido": ("q0 0 -> qBusca1 X R", "qFantasma 0 -> qBusca1 X R"),
            "escritura inválida": ("q0 0 -> qBusca1 X R", "q0 0 -> qBusca1 Z R"),
            "lectura inválida": ("q0 0 -> qBusca1 X R", "q0 Z -> qBusca1 X R"),
            "delta incompleta": ("q0 0 -> qBusca1 X R", ""),
            "no determinismo": ("q0 0 -> qBusca1 X R", "q0 0 -> qBusca1 X R\nq0 0 -> qRechaza 0 R"),
        }
        invalidos = [(n, self.texto.replace(a, b)) for n, (a, b) in casos.items()]
        invalidos += [("salida de final", self.texto + "\nqAcepta _ -> qAcepta _ R\n"),
                      ("regla repetida", self.texto + "\nq0 0 -> qBusca1 X R\n")]
        for nombre, texto in invalidos:
            with self.subTest(error=nombre):
                proceso, traza = ejecutar_texto(texto)
                self.assertNotEqual(proceso.returncode, 0)
                self.assertIn("Error:", proceso.stdout)
                self.assertEqual(traza, "")


if __name__ == "__main__":
    unittest.main()
