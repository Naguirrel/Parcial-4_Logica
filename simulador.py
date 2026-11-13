"""Simulador educativo de una máquina de Turing determinista de una cinta.

La máquina solo utiliza su cinta como memoria de trabajo. El programa anfitrión
mantiene la descripción fija de la máquina, el estado y la posición del cabezal.
Las configuraciones se escriben al archivo sin guardar un historial en memoria.
"""

# argparse permite recibir las rutas y el límite de pasos desde la terminal.
import argparse
# re comprueba que los nombres de los estados tengan un formato inequívoco.
import re
# dataclass agrupa los datos relacionados sin escribir constructores a mano.
from dataclasses import dataclass
# Path facilita abrir archivos y comparar sus rutas en Windows y otros sistemas.
from pathlib import Path
# TextIO describe un archivo de texto abierto; sirve para documentar el parámetro.
from typing import TextIO


@dataclass(frozen=True)
class Maquina:
    """Descripción fija de M = (Q, Σ, Γ, δ, q0, qacepta, qrechaza).

    El blanco se declara aparte como un elemento distinguido de Γ.
    Una transición tiene la forma (estado, leído): (destino, escrito, movimiento).
    Esta tabla es el programa de la máquina, no una memoria auxiliar de cálculo.
    """

    estados: frozenset[str]  # Q: todos los estados de la máquina.
    alfabeto_entrada: frozenset[str]  # Σ: símbolos permitidos en la entrada.
    alfabeto_cinta: frozenset[str]  # Γ: entrada, marcas y blanco.
    blanco: str  # Símbolo que representa una celda vacía.
    inicial: str  # Estado en que empieza la ejecución.
    aceptacion: str  # Estado final que acepta la entrada.
    rechazo: str  # Estado final que rechaza la entrada.
    entrada: str  # Cadena inicial; puede ser vacía.
    transiciones: dict[tuple[str, str], tuple[str, str, str]]  # Función δ.


@dataclass(frozen=True)
class Resultado:
    """Resumen de la ejecución; no almacena las configuraciones anteriores."""

    motivo: str  # ACEPTADA, RECHAZADA o LIMITE_ALCANZADO.
    pasos: int  # Cantidad de transiciones que realmente se ejecutaron.
    estado: str  # Estado al terminar o interrumpir la simulación.


def cargar_maquina(ruta: Path) -> Maquina:
    """Lee el archivo .txt, construye la máquina y verifica su especificación.

    Los errores incluyen la línea cuando pueden localizarse durante la lectura.
    Los comentarios empiezan con # y los campos se separan con dos puntos.
    """
    # Estas claves son obligatorias y solo pueden declararse una vez.
    claves = {
        "estados", "alfabeto_entrada", "alfabeto_cinta", "blanco", "inicial",
        "aceptacion", "rechazo", "entrada",
    }
    campos: dict[str, str] = {}  # Datos de la descripción, no de la cinta.
    transiciones: dict[tuple[str, str], tuple[str, str, str]] = {}
    leyendo_transiciones = False  # Indica si ya apareció la sección final.

    # utf-8-sig admite archivos UTF-8 normales y los que incluyen una marca BOM.
    with ruta.open("r", encoding="utf-8-sig") as archivo:
        # enumerate cuenta las líneas desde 1 para dar mensajes fáciles de ubicar.
        for numero, original in enumerate(archivo, start=1):
            # Quitamos el comentario y los espacios de los extremos.
            linea = original.split("#", 1)[0].strip()
            if not linea:  # Las líneas vacías o que solo tienen comentarios se omiten.
                continue

            if not leyendo_transiciones:
                if linea == "transiciones:":
                    leyendo_transiciones = True
                    continue
                if ":" not in linea:
                    raise ValueError(f"Línea {numero}: se esperaba 'campo: valor'.")
                # Solo se divide en el primer separador para poder detectar valores inválidos.
                clave, valor = (parte.strip() for parte in linea.split(":", 1))
                if clave not in claves:
                    raise ValueError(f"Línea {numero}: campo desconocido '{clave}'.")
                if clave in campos:
                    raise ValueError(f"Línea {numero}: campo repetido '{clave}'.")
                campos[clave] = valor
                continue

            # Cada regla tiene seis partes: origen, leído, ->, destino, escrito y L/R.
            partes = linea.split()
            if len(partes) != 6 or partes[2] != "->":
                raise ValueError(
                    f"Línea {numero}: use 'origen leído -> destino escrito L/R'."
                )
            origen, leido, _, destino, escrito, movimiento = partes
            clave_transicion = (origen, leido)
            if clave_transicion in transiciones:
                # Incluso dos reglas idénticas se rechazan: cada par se declara una vez.
                raise ValueError(
                    f"Línea {numero}: transición repetida para {clave_transicion}; "
                    "cada par (estado, símbolo) debe tener una sola regla."
                )
            transiciones[clave_transicion] = (destino, escrito, movimiento)

    faltantes = claves - campos.keys()  # Diferencia entre lo requerido y lo leído.
    if faltantes:
        raise ValueError(f"Faltan campos: {', '.join(sorted(faltantes))}.")
    if not leyendo_transiciones:
        raise ValueError("Falta la sección 'transiciones:'.")

    def leer_conjunto(nombre: str) -> frozenset[str]:
        """Convierte una lista de tokens en conjunto y detecta duplicados."""
        elementos = campos[nombre].split()
        if len(elementos) != len(set(elementos)):
            raise ValueError(f"El campo '{nombre}' tiene elementos repetidos.")
        return frozenset(elementos)

    # Los nombres de los argumentos corresponden a los componentes formales.
    maquina = Maquina(
        estados=leer_conjunto("estados"),
        alfabeto_entrada=leer_conjunto("alfabeto_entrada"),
        alfabeto_cinta=leer_conjunto("alfabeto_cinta"),
        blanco=campos["blanco"],
        inicial=campos["inicial"],
        aceptacion=campos["aceptacion"],
        rechazo=campos["rechazo"],
        entrada=campos["entrada"],
        transiciones=transiciones,
    )
    validar_maquina(maquina)  # No ejecutamos una especificación inconsistente.
    return maquina


def validar_maquina(maquina: Maquina) -> None:
    """Verifica conjuntos, estados, entrada y una función δ total y determinista.

    Se exige una regla para cada símbolo de Γ en cada estado no final. Los
    estados de aceptación y rechazo no tienen reglas salientes.
    """
    if not maquina.estados:
        raise ValueError("El conjunto de estados no puede estar vacío.")
    for estado in maquina.estados:
        if not re.fullmatch(r"[A-Za-z][A-Za-z0-9_]*", estado):
            raise ValueError(f"Nombre de estado inválido: '{estado}'.")

    if not maquina.alfabeto_cinta:
        raise ValueError("El alfabeto de cinta no puede estar vacío.")
    for simbolo in maquina.alfabeto_entrada | maquina.alfabeto_cinta:
        # Un carácter equivale a una celda; # y : se reservan para el formato.
        if len(simbolo) != 1 or simbolo.isspace() or simbolo in "#:":
            raise ValueError(f"Símbolo inválido: '{simbolo}'; use un carácter sin # ni :.")
    if not maquina.alfabeto_entrada <= maquina.alfabeto_cinta:
        raise ValueError("El alfabeto de entrada debe estar incluido en el de cinta.")
    if maquina.blanco not in maquina.alfabeto_cinta:
        raise ValueError("El blanco debe pertenecer al alfabeto de cinta.")
    if maquina.blanco in maquina.alfabeto_entrada:
        raise ValueError("El blanco no puede pertenecer al alfabeto de entrada.")

    # Los tres estados distinguidos deben existir y ser distintos en este modelo.
    distinguidos = (maquina.inicial, maquina.aceptacion, maquina.rechazo)
    if any(estado not in maquina.estados for estado in distinguidos):
        raise ValueError("Los estados inicial, de aceptación y de rechazo deben pertenecer a Q.")
    if len(set(distinguidos)) != 3:
        raise ValueError("Los estados inicial, de aceptación y de rechazo deben ser distintos.")
    if any(simbolo not in maquina.alfabeto_entrada for simbolo in maquina.entrada):
        raise ValueError("La entrada contiene símbolos que no pertenecen a Σ.")

    finales = {maquina.aceptacion, maquina.rechazo}
    for (origen, leido), (destino, escrito, movimiento) in maquina.transiciones.items():
        if origen not in maquina.estados or destino not in maquina.estados:
            raise ValueError(f"La transición ({origen}, {leido}) utiliza un estado fuera de Q.")
        if origen in finales:
            raise ValueError(f"El estado final '{origen}' no puede tener transiciones salientes.")
        if leido not in maquina.alfabeto_cinta or escrito not in maquina.alfabeto_cinta:
            raise ValueError(f"La transición ({origen}, {leido}) utiliza un símbolo fuera de Γ.")
        if movimiento not in {"L", "R"}:
            raise ValueError(f"Movimiento inválido '{movimiento}': use L o R.")

    # Se exige completitud para que una regla ausente sea un error de descripción,
    # en lugar de inventar un rechazo que el archivo no especifica.
    for estado in sorted(maquina.estados - finales):
        for simbolo in sorted(maquina.alfabeto_cinta):
            if (estado, simbolo) not in maquina.transiciones:
                raise ValueError(f"Falta la transición para ({estado}, {simbolo}).")


class Cinta:
    """Una sola cinta, ilimitada en ambos sentidos y con blanco implícito.

    El diccionario representa LAS celdas de la cinta, no una segunda memoria.
    Solo almacena las celdas no blancas: las demás se leen como blanco.
    """

    def __init__(self, entrada: str, blanco: str) -> None:
        """Coloca la entrada en las posiciones 0, 1, 2, ... de la cinta."""
        self.blanco = blanco
        self.celdas = {
            posicion: simbolo
            for posicion, simbolo in enumerate(entrada)
            if simbolo != blanco
        }

    def leer(self, posicion: int) -> str:
        """Lee una celda; get devuelve blanco si la posición no está almacenada."""
        return self.celdas.get(posicion, self.blanco)

    def escribir(self, posicion: int, simbolo: str) -> None:
        """Sobrescribe una celda; escribir blanco equivale a borrar su contenido."""
        if simbolo == self.blanco:
            self.celdas.pop(posicion, None)  # No falla si la celda ya estaba vacía.
        else:
            self.celdas[posicion] = simbolo

    def escribir_configuracion(self, archivo: TextIO, estado: str, cabezal: int) -> None:
        """Escribe α q β: q aparece justo antes de la celda que está leyendo.

        Muestra el intervalo mínimo que contiene el cabezal y todas las celdas
        no blancas. Los blancos fuera del intervalo quedan implícitos. La salida
        se escribe celda por celda y nunca se consulta para decidir transiciones.
        """
        # Con cinta vacía, el intervalo contiene solamente la celda del cabezal.
        izquierda = min(cabezal, min(self.celdas, default=cabezal))
        derecha = max(cabezal, max(self.celdas, default=cabezal))
        for posicion in range(izquierda, derecha + 1):
            if posicion == cabezal:
                # El espacio entre q y el símbolo distingue el estado de la cinta.
                archivo.write(f"{estado} ")
            archivo.write(self.leer(posicion))
            if posicion == cabezal - 1:
                archivo.write(" ")  # Separa α del nombre del estado.
        archivo.write("\n")


def simular(maquina: Maquina, archivo: TextIO, max_pasos: int = 1000) -> Resultado:
    """Ejecuta δ y escribe la configuración inicial y cada configuración nueva.

    max_pasos es una protección del simulador anfitrión; no es parte de la MT.
    Alcanzarlo no significa aceptación, rechazo ni demostración de un ciclo.
    """
    if max_pasos < 0:
        raise ValueError("El límite de pasos no puede ser negativo.")
    validar_maquina(maquina)  # También protege llamadas desde otro programa.
    cinta = Cinta(maquina.entrada, maquina.blanco)
    estado = maquina.inicial
    cabezal = 0  # Primera celda de la entrada, o una celda blanca si está vacía.
    pasos = 0

    archivo.write("SIMULACIÓN DE MÁQUINA DE TURING DETERMINISTA\n")
    archivo.write(f"Entrada: {maquina.entrada or 'ε (cadena vacía)'}\n")
    archivo.write(f"Blanco: {maquina.blanco}\n")
    archivo.write("Notación: α q β; el cabezal lee el primer símbolo de β.\n")
    archivo.write("C0 es inicial; cada ⊢ representa una transición.\n\n")
    archivo.write("C0: ")
    cinta.escribir_configuracion(archivo, estado, cabezal)

    while True:
        # Revisamos los estados finales antes del límite: una última transición
        # que acepta o rechaza justo en el límite debe conservar ese resultado.
        if estado == maquina.aceptacion:
            motivo = "ACEPTADA"
            break
        if estado == maquina.rechazo:
            motivo = "RECHAZADA"
            break
        if pasos >= max_pasos:
            motivo = "LIMITE_ALCANZADO"
            break

        leido = cinta.leer(cabezal)  # 1. Leer únicamente la celda actual.
        destino, escrito, movimiento = maquina.transiciones[(estado, leido)]
        cinta.escribir(cabezal, escrito)  # 2. Escribir en esa misma celda.
        cabezal += 1 if movimiento == "R" else -1  # 3. Mover una celda.
        estado = destino  # 4. Entrar al estado indicado por δ.
        pasos += 1  # El contador solo controla el límite y el informe.
        archivo.write(f"⊢ C{pasos}: ")
        cinta.escribir_configuracion(archivo, estado, cabezal)

    archivo.write(f"\nResultado: {motivo}\n")
    archivo.write(f"Transiciones ejecutadas: {pasos}\nEstado final observado: {estado}\n")
    if motivo == "LIMITE_ALCANZADO":
        archivo.write(
            "Ejecución interrumpida por el límite. La máquina no se ha detenido.\n"
            "Este límite por sí solo NO demuestra un ciclo infinito.\n"
        )
    return Resultado(motivo, pasos, estado)


def entero_no_negativo(texto: str) -> int:
    """Valida el argumento de terminal --max-pasos y produce un error claro."""
    try:
        valor = int(texto)
    except ValueError as error:
        raise argparse.ArgumentTypeError("Debe ser un número entero.") from error
    if valor < 0:
        raise argparse.ArgumentTypeError("Debe ser mayor o igual que cero.")
    return valor


def main() -> int:
    """Recibe argumentos, valida el archivo y genera la salida de configuraciones."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("entrada", type=Path, help="Archivo .txt con la máquina y la cadena.")
    parser.add_argument("-o", "--salida", type=Path, default=Path("salida.txt"),
                        help="Archivo de configuraciones (predeterminado: salida.txt).")
    parser.add_argument("--max-pasos", type=entero_no_negativo, default=1000,
                        help="Máximo de transiciones; 0 solo muestra C0 (predeterminado: 1000).")
    argumentos = parser.parse_args()
    try:
        # Evitamos destruir la especificación por usar la misma ruta como salida.
        if argumentos.entrada.resolve() == argumentos.salida.resolve():
            raise ValueError("La entrada y la salida deben ser archivos distintos.")
        # samefile también detecta dos enlaces que señalan al mismo archivo.
        if argumentos.salida.exists() and argumentos.entrada.samefile(argumentos.salida):
            raise ValueError("La entrada y la salida señalan al mismo archivo.")
        maquina = cargar_maquina(argumentos.entrada)
        # La salida se abre solo después de validar toda la especificación.
        with argumentos.salida.open("w", encoding="utf-8") as archivo:
            resultado = simular(maquina, archivo, argumentos.max_pasos)
    except (OSError, UnicodeError, ValueError) as error:
        print(f"Error: {error}")
        return 1  # Código de error para la terminal; no es un rechazo de la MT.
    print(f"{resultado.motivo}: {resultado.pasos} transiciones.")
    print(f"Configuraciones guardadas en: {argumentos.salida.resolve()}")
    return 0  # Tanto aceptar como rechazar son ejecuciones válidas del simulador.

raise SystemExit(main())