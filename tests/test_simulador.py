"""Pruebas de semántica, validación y archivos; solo usan la biblioteca estándar."""

import io  # Simula un archivo de texto para inspeccionar la salida de las pruebas.
import itertools  # Genera cadenas cortas para verificar la máquina exhaustivamente.
import tempfile  # Crea archivos aislados que se eliminan al terminar cada prueba.
import unittest  # Organiza y ejecuta las verificaciones automáticas.
from dataclasses import replace  # Cambia la entrada sin alterar la descripción original.
from pathlib import Path

from simulador import Cinta, cargar_maquina, simular


# La ruta se calcula desde este archivo para no depender del directorio de ejecución.
RAIZ = Path(__file__).resolve().parents[1]


class PruebasSimulador(unittest.TestCase):
    """Comprueba que el simulador aplica las reglas y detecta archivos incorrectos."""

    @classmethod
    def setUpClass(cls):
        """Carga una sola vez el ejemplo válido para compartirlo entre las pruebas."""
        cls.texto = (RAIZ / "ejemplos" / "aceptacion.txt").read_text(encoding="utf-8")
        cls.maquina = cargar_maquina(RAIZ / "ejemplos" / "aceptacion.txt")

    def ejecutar(self, entrada, limite=1000):
        """Ejecuta una entrada y devuelve el resumen y el texto de configuraciones."""
        salida = io.StringIO()
        resultado = simular(replace(self.maquina, entrada=entrada), salida, limite)
        return resultado, salida.getvalue()

    def cargar_texto(self, texto):
        """Permite probar especificaciones inválidas sin modificar los ejemplos."""
        with tempfile.TemporaryDirectory() as carpeta:
            ruta = Path(carpeta) / "maquina.txt"
            ruta.write_text(texto, encoding="utf-8")
            return cargar_maquina(ruta)

    def test_lenguaje_en_todas_las_cadenas_binarias_hasta_longitud_8(self):
        """Contrasta 511 cadenas con la definición matemática, sin usar la MT como oráculo."""
        for longitud in range(9):
            for simbolos in itertools.product("01", repeat=longitud):
                entrada = "".join(simbolos)
                n = longitud // 2
                esperado = "ACEPTADA" if n >= 1 and entrada == "0" * n + "1" * n else "RECHAZADA"
                with self.subTest(entrada=entrada):
                    resultado, _ = self.ejecutar(entrada)
                    self.assertEqual(resultado.motivo, esperado)

    def test_traza_exacta_de_01(self):
        """Verifica escritura, movimiento izquierdo, blanco implícito y estado final."""
        resultado, texto = self.ejecutar("01")
        configuraciones = [linea for linea in texto.splitlines() if linea.startswith(("C0:", "⊢"))]
        self.assertEqual(configuraciones, [
            "C0: q0 01",
            "⊢ C1: X qBusca1 1",
            "⊢ C2: qRegresa XY",
            "⊢ C3: qRegresa _XY",
            "⊢ C4: q0 XY",
            "⊢ C5: X q0 Y",
            "⊢ C6: XY qVerifica _",
            "⊢ C7: XY_ qAcepta _",
        ])
        self.assertEqual((resultado.motivo, resultado.pasos), ("ACEPTADA", 7))

    def test_ciclo_oscilante_y_limite(self):
        """El ejemplo cíclico repite C1 en C3; el simulador solo reporta su límite."""
        resultado, texto = self.ejecutar("2", 6)
        self.assertEqual(resultado.motivo, "LIMITE_ALCANZADO")
        self.assertEqual(resultado.pasos, 6)
        self.assertIn("⊢ C1: 2 qIda _", texto)
        self.assertIn("⊢ C3: 2 qIda _", texto)
        self.assertIn("NO demuestra un ciclo infinito", texto)
        for longitud in range(4):
            for cola in itertools.product("012", repeat=longitud):
                with self.subTest(cola=cola):
                    resumen, _ = self.ejecutar("2" + "".join(cola), 10)
                    self.assertEqual(resumen.motivo, "LIMITE_ALCANZADO")

    def test_dos_fuera_de_la_primera_posicion_rechaza(self):
        """Un 2 intercalado no debe activar el ciclo reservado para entradas que empiezan con 2."""
        for entrada in ("02", "012", "00112", "102", "0002111"):
            with self.subTest(entrada=entrada):
                self.assertEqual(self.ejecutar(entrada)[0].motivo, "RECHAZADA")

    def test_estado_final_tiene_prioridad_sobre_limite(self):
        """Aceptar o rechazar en la última transición permitida sigue siendo una parada."""
        self.assertEqual(self.ejecutar("01", 7)[0].motivo, "ACEPTADA")
        self.assertEqual(self.ejecutar("1", 1)[0].motivo, "RECHAZADA")
        self.assertEqual(self.ejecutar("01", 6)[0].motivo, "LIMITE_ALCANZADO")

    def test_limite_cero_y_negativo(self):
        """Con cero no se aplica δ; un límite negativo es inválido."""
        resultado, texto = self.ejecutar("01", 0)
        self.assertEqual((resultado.pasos, resultado.estado), (0, "q0"))
        self.assertNotIn("⊢ C1:", texto)
        with self.assertRaises(ValueError):
            self.ejecutar("01", -1)

    def test_cinta_negativa_y_borrado(self):
        """La cinta crece a la izquierda y una escritura blanca realmente borra."""
        cinta = Cinta("01", "_")
        cinta.escribir(-3, "X")
        self.assertEqual(cinta.leer(-3), "X")
        cinta.escribir(-3, "_")
        self.assertEqual(cinta.leer(-3), "_")
        self.assertNotIn(-3, cinta.celdas)
        self.assertEqual(cinta.leer(10000), "_")

    def test_archivos_de_ejemplo_coinciden_con_salidas(self):
        """Los archivos entregados deben ser reproducibles con el código actual."""
        for nombre, limite in (("aceptacion", 1000), ("rechazo", 1000), ("ciclo", 12)):
            with self.subTest(nombre=nombre):
                maquina = cargar_maquina(RAIZ / "ejemplos" / f"{nombre}.txt")
                salida = io.StringIO()
                simular(maquina, salida, limite)
                esperado = (RAIZ / "salidas" / f"{nombre}.txt").read_text(encoding="utf-8")
                self.assertEqual(salida.getvalue(), esperado)

    def test_especificaciones_invalidas(self):
        """Rechaza errores de sintaxis, componentes, determinismo y completitud."""
        casos = {
            "campo ausente": ("blanco: _\n", ""),
            "campo duplicado": ("blanco: _", "blanco: _\nblanco: _"),
            "campo desconocido": ("blanco: _", "vacio: _"),
            "sin sección": ("transiciones:", ""),
            "estado inexistente": ("inicial: q0", "inicial: qFantasma"),
            "estado con nombre ambiguo": ("estados: q0", "estados: 9q"),
            "estado duplicado": ("estados: q0", "estados: q0 q0"),
            "alfabeto duplicado": ("alfabeto_entrada: 0 1 2", "alfabeto_entrada: 0 1 2 0"),
            "blanco en entrada": ("alfabeto_entrada: 0 1 2", "alfabeto_entrada: 0 1 2 _"),
            "blanco fuera de cinta": ("blanco: _", "blanco: B"),
            "sigma fuera de gamma": ("alfabeto_entrada: 0 1 2", "alfabeto_entrada: 0 1 2 3"),
            "símbolo largo": ("alfabeto_cinta: 0 1 2 X Y _", "alfabeto_cinta: 0 1 2 XX Y _"),
            "entrada ajena a sigma": ("entrada: 0011", "entrada: 03"),
            "estados finales iguales": ("rechazo: qRechaza", "rechazo: qAcepta"),
            "regla incompleta": ("q0 0 -> qBusca1 X R", "q0 0 -> qBusca1 X"),
            "movimiento inválido": ("q0 0 -> qBusca1 X R", "q0 0 -> qBusca1 X S"),
            "destino desconocido": ("q0 0 -> qBusca1 X R", "q0 0 -> qFantasma X R"),
            "origen desconocido": ("q0 0 -> qBusca1 X R", "qFantasma 0 -> qBusca1 X R"),
            "escritura fuera de gamma": ("q0 0 -> qBusca1 X R", "q0 0 -> qBusca1 Z R"),
            "lectura fuera de gamma": ("q0 0 -> qBusca1 X R", "q0 Z -> qBusca1 X R"),
            "delta incompleta": ("q0 0 -> qBusca1 X R", ""),
            "delta no determinista": ("q0 0 -> qBusca1 X R", "q0 0 -> qBusca1 X R\nq0 0 -> qRechaza 0 R"),
        }
        for nombre, (original, reemplazo) in casos.items():
            with self.subTest(error=nombre):
                with self.assertRaises(ValueError):
                    self.cargar_texto(self.texto.replace(original, reemplazo))
        with self.assertRaises(ValueError):
            self.cargar_texto(self.texto + "\nqAcepta _ -> qAcepta _ R\n")
        with self.assertRaises(ValueError):
            self.cargar_texto(self.texto + "\nq0 0 -> qBusca1 X R\n")


if __name__ == "__main__":
    unittest.main()  # Permite ejecutar el archivo directamente si se desea.
