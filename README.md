# Simulador de máquina de Turing determinista

Proyecto en Python para cargar una máquina de Turing desde un archivo de texto,
validar sus componentes y guardar sus configuraciones paso a paso en otro archivo.
Incluye código comentado en español, un diagrama, tres entradas de ejemplo con
sus salidas y un [guion detallado para la exposición](Guion.md).

## Ejecutar

Necesitas **Python 3.10 o posterior**. El simulador y las pruebas solo utilizan
la biblioteca estándar: no hay paquetes que instalar.

Abre una terminal en esta carpeta y ejecuta:

```powershell
python simulador.py ejemplos/aceptacion.txt -o salidas/aceptacion.txt
python simulador.py ejemplos/rechazo.txt -o salidas/rechazo.txt
python simulador.py ejemplos/ciclo.txt -o salidas/ciclo.txt --max-pasos 12
```

Si Windows no reconoce `python`, puedes sustituirlo por `py`.

| Archivo de entrada | Cadena | Resultado | Transiciones |
|---|---|---|---|
| `ejemplos/aceptacion.txt` | `0011` | `ACEPTADA` | 19 |
| `ejemplos/rechazo.txt` | `001` | `RECHAZADA` | 10 |
| `ejemplos/ciclo.txt` | `2` | `LIMITE_ALCANZADO` | 12, por el límite elegido |

Las tres especificaciones describen **la misma máquina**; solo cambia `entrada:`.
Las salidas ya están generadas y se pueden reproducir con los comandos anteriores.
`-o` sobrescribe el archivo de salida indicado; su carpeta debe existir.

Ayuda y pruebas:

```powershell
python simulador.py --help
python -m unittest discover -s tests -v
```

## Archivos

```text
Parcial_4/
├── simulador.py              Código y comentarios de cada función/bloque
├── README.md                 Instrucciones de uso y descripción del proyecto
├── Guion.md                  Explicación extensa y demostración oral
├── diagrama.dot              Fuente editable del diagrama completo
├── diagrama.svg              Diagrama vectorial para ampliar o imprimir
├── diagrama.png              Diagrama como imagen
├── ejemplos/
│   ├── aceptacion.txt         Máquina y entrada 0011
│   ├── rechazo.txt            Máquina y entrada 001
│   └── ciclo.txt              Máquina y entrada 2
├── salidas/
│   ├── aceptacion.txt         Traza de aceptación
│   ├── rechazo.txt            Traza de rechazo
│   └── ciclo.txt              Prefijo finito de la ejecución infinita
└── tests/
    └── test_simulador.py      Pruebas de ejecución y validación
```

## Máquina de ejemplo

Acepta el lenguaje **L = {0ⁿ1ⁿ | n ≥ 1}**: primero uno o más ceros y después la
misma cantidad de unos. Por ejemplo: `01`, `0011` y `000111`.

Rechaza, entre otras, la cadena vacía, `0`, `1`, `001`, `011` y `0101`.
Las entradas que empiezan con `2` entran en un ciclo infinito. Un `2` en otra
posición provoca rechazo. Por ello, esta máquina reconoce L pero no es un
decisor sobre todo su alfabeto de entrada, pues no se detiene con todas las cadenas.

Formalmente se usa **M = (Q, Σ, Γ, δ, q0, qAcepta, qRechaza)**:

- Q = {q0, qBusca1, qRegresa, qVerifica, qIda, qVuelta, qAcepta, qRechaza}.
- Σ = {0, 1, 2}.
- Γ = {0, 1, 2, X, Y, _}; el blanco es `_` y no pertenece a Σ.
- δ contiene las 36 reglas de los archivos de ejemplo.
- q0 es inicial; qAcepta y qRechaza son finales, distintos y sin salidas.

La máquina marca cada `0` procesado con `X` y su `1` correspondiente con `Y`.
Regresa al inicio y repite. Cuando no quedan ceros, comprueba que solo queden
unos ya marcados antes del blanco. Toda la información del emparejamiento
está en las marcas de **una única cinta**.

## Diagrama y notación

![Diagrama completo de la máquina de Turing](diagrama.png)

También puedes abrir [el SVG](diagrama.svg) para ampliar sin perder calidad.
Cada etiqueta `a/b, R` significa «leer a, escribir b y mover una celda a la
derecha»; `L` significa izquierda. Una etiqueta `a/a, R; a en Γ` resume una
regla para **cada** símbolo de Γ. La flecha sin origen señala el estado inicial;
los dos estados finales tienen doble círculo y rótulos que distinguen su resultado.

El proyecto utiliza la notación estándar acordada para este trabajo: **α q β**.
El cabezal lee el primer símbolo de β; α es la parte de la cinta a su izquierda.
Los blancos externos se omiten, salvo los necesarios para mostrar el cabezal.
El símbolo **⊢** indica un paso de cómputo y ε representa la cadena vacía.

Ejemplo de salida:

```text
C0: q0 0011
⊢ C1: X qBusca1 011
⊢ C2: X0 qBusca1 11
⊢ C3: X qRegresa 0Y1
```

Los rótulos `C0`, `C1`, etc. numeran las configuraciones; no son símbolos de la
cinta. En `X qBusca1 011`, el cabezal lee el primer `0` que aparece después
de `qBusca1`. En la configuración final también se indica la celda del cabezal.

## Formato del archivo de entrada

El archivo es texto UTF-8. Los campos deben aparecer antes de `transiciones:`.
Se permiten líneas vacías y comentarios iniciados por `#`.

```text
estados: q0 qBusca1 qRegresa qVerifica qIda qVuelta qAcepta qRechaza
alfabeto_entrada: 0 1 2
alfabeto_cinta: 0 1 2 X Y _
blanco: _
inicial: q0
aceptacion: qAcepta
rechazo: qRechaza
entrada: 0011

transiciones:
# Aquí deben ir TODAS las reglas, como en ejemplos/aceptacion.txt.
```

Cada transición ocupa una línea con seis tokens:

```text
q0 0 -> qBusca1 X R
```

Los símbolos de los alfabetos se separan con espacios y cada uno debe ocupar un
carácter. La cadena de entrada se escribe seguida, **sin espacios**. Para probar
la cadena vacía, deja `entrada:` sin valor; no escribas literalmente `ε`.
Los símbolos `#`, `:` y los espacios están reservados para el formato y no se
permiten como símbolos de cinta. Los nombres de estados empiezan con una letra
ASCII y continúan con letras ASCII, dígitos o `_`.

## Validación

El programa verifica antes de crear la salida:

- Campos obligatorios, sin desconocidos ni repetidos; sección de transiciones presente.
- Estados y alfabetos sin elementos duplicados; nombres y símbolos válidos.
- Σ ⊆ Γ, blanco ∈ Γ y blanco ∉ Σ; entrada formada solo por símbolos de Σ.
- Estados inicial, de aceptación y de rechazo pertenecientes a Q y distintos.
- Origen/destino de cada regla en Q y símbolos leídos/escritos en Γ.
- Movimientos únicamente L o R; ninguna salida desde un estado final.
- Una única regla por par (estado, símbolo), incluso si se repite idéntica.
- Una regla para cada par de (Q sin estados finales) × Γ.

Se exige δ **total sobre los estados no finales**. Una regla ausente se reporta
como especificación inválida; no se interpreta como un rechazo implícito.
También se impide que la salida sobrescriba la propia entrada.

## Cinta, memoria y límite de pasos

Se utiliza una cinta ilimitada en ambos sentidos: el índice puede ser negativo.
Un diccionario representa sus celdas no blancas; una posición no almacenada
contiene blanco. El simulador no utiliza una segunda cinta, pila, cola ni contador
de ceros o unos para decidir las transiciones. La tabla δ es la descripción fija
del programa y el estado/cabezal son su control.

Las configuraciones se escriben progresivamente al archivo de salida; no se
almacena un historial ni se consulta la salida para calcular el siguiente paso.
Las pruebas sí capturan texto para comprobar resultados, pero no forman parte
de la máquina simulada. Python y el sistema operativo requieren memoria para
representar y ejecutar el simulador; la restricción se aplica al modelo simulado.

El límite predeterminado es de 1000 transiciones. Puedes cambiarlo con
`--max-pasos N`; con cero solo se registra la configuración inicial.
**Alcanzar el límite no demuestra que haya un ciclo**, ni equivale a rechazar.
Una entrada válida que necesite más pasos también puede alcanzar ese límite.

En el ejemplo `2`, sí hay una demostración específica: C1 y C3 tienen el mismo
estado, cinta y cabezal. Como δ es determinista, desde allí se repiten siempre
los mismos dos pasos. `salidas/ciclo.txt` contiene un prefijo de esa ejecución;
un archivo finito no puede contener una ejecución infinita completa.

## Material para presentar

| Inciso de la consigna | Material preparado |
|---|---|
| a: programa | `simulador.py` |
| b: diseño con aceptación, rechazo y ciclo | `diagrama.png`, `diagrama.svg`, `diagrama.dot` |
| c–d: entrada aceptada y configuraciones | `ejemplos/aceptacion.txt`, `salidas/aceptacion.txt` |
| e–f: entrada rechazada y configuraciones | `ejemplos/rechazo.txt`, `salidas/rechazo.txt` |
| g–h: entrada que cicla y configuraciones | `ejemplos/ciclo.txt`, `salidas/ciclo.txt` |
| Ejecución y revisión presencial | Comandos anteriores y `Guion.md` |

El inciso g menciona el inciso a; aquí se utiliza la misma máquina diseñada
para b y simulada por a, manteniendo consistentes las tres demostraciones.
La carga de los archivos a Canvas y la presentación presencial quedan a tu cargo.

El archivo `.dot` es opcional para ejecutar el proyecto. Si deseas editar y
regenerar el diagrama, necesitas Graphviz y estos comandos:

```powershell
dot -Tsvg diagrama.dot -o diagrama.svg
dot -Tpng diagrama.dot -o diagrama.png
```
