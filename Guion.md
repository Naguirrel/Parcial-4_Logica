# Guion de exposición: simulador de máquina de Turing determinista

Este documento sirve para estudiar el proyecto y preparar una explicación oral
de unos 12 a 15 minutos. Los apartados de código y preguntas permiten ampliar
la presentación durante la revisión. Puedes adaptar las frases a tu forma de hablar.

## 1. Presentación del proyecto

**Puedes decir:**

> Mi proyecto es un simulador de una máquina de Turing determinista de una cinta,
> escrito en Python. Recibe un archivo de texto con los componentes de la máquina,
> verifica que estén bien definidos y genera otro archivo con sus configuraciones.
> Incluí una máquina que tiene tres comportamientos: aceptar, rechazar o continuar
> indefinidamente, según la cadena de entrada.

Abre `README.md` y muestra la estructura del proyecto. Distingue dos cosas:

- **El simulador** es `simulador.py`. Puede ejecutar distintas máquinas que respeten
  el modelo y el formato documentados.
- **La máquina de ejemplo** está definida en los `.txt`. Sus transiciones no están
  programadas dentro del bucle del simulador.

Cambiar el archivo de especificación cambia la máquina. Cambiar únicamente
`entrada:` permite probar distintas cadenas sobre la misma máquina.

## 2. Qué es una máquina de Turing

**Puedes decir:**

> Una máquina de Turing tiene un conjunto finito de estados, una cinta, un cabezal
> que lee y escribe una celda a la vez, y una función de transición. En cada paso,
> el estado actual y el símbolo leído determinan el nuevo estado, el símbolo que
> se escribe y la dirección del movimiento.

En este modelo, la cinta es ilimitada hacia la izquierda y hacia la derecha. No
significa que Python reserve memoria infinita: solo se representan las celdas
no blancas que se utilizan. Los índices negativos representan posiciones a la izquierda
de la posición inicial, no el acceso desde el final de una lista de Python.

La máquina es **determinista** porque para cada par `(estado, símbolo leído)` existe
exactamente una acción en los estados no finales. No elige entre alternativas.
Cuando entra a `qAcepta` o `qRechaza`, se detiene; esos estados no tienen salidas.

## 3. Componentes formales y decisiones del modelo

Usamos:

```text
M = (Q, Σ, Γ, δ, q0, qAcepta, qRechaza)
```

| Componente | Significado | Valor en el ejemplo |
|---|---|---|
| Q | Conjunto finito de estados | q0, qBusca1, qRegresa, qVerifica, qIda, qVuelta, qAcepta, qRechaza |
| Σ | Alfabeto de entrada | {0, 1, 2} |
| Γ | Alfabeto de cinta | {0, 1, 2, X, Y, _} |
| δ | Función de transición | 36 reglas de los archivos `.txt` |
| q0 | Estado inicial | q0 |
| qAcepta | Estado de aceptación | qAcepta |
| qRechaza | Estado de rechazo | qRechaza |

El blanco es `_`, pertenece a Γ y queda fuera de Σ. Se declara explícitamente
en el archivo. Las letras `X` y `Y` son marcas de trabajo: no se permiten en la
cadena de entrada, pero la máquina puede escribirlas en la cinta.

Formalmente:

```text
δ: (Q − {qAcepta, qRechaza}) × Γ → Q × Γ × {L, R}
```

Esta implementación exige que δ sea total en ese dominio. Son seis estados
no finales y seis símbolos de cinta: **6 × 6 = 36 reglas**. En los estados finales
no se define δ. El simulador no admite movimiento estacionario `S`; todas las
reglas se mueven una celda a izquierda o derecha. También exige que el estado
inicial y los dos finales sean distintos.

Estas son decisiones explícitas del modelo utilizado. Hay otras convenciones
de máquinas de Turing, por ejemplo cinta limitada a un extremo o transiciones
parciales; no son las que implementa este proyecto.

## 4. Qué problema resuelve la máquina diseñada

El lenguaje aceptado es:

```text
L = {0ⁿ1ⁿ | n ≥ 1}
```

**Puedes decir:**

> La cadena debe tener primero ceros y después unos, con la misma cantidad de
> cada símbolo y al menos uno de cada uno. No basta con contar: también importa
> el orden. Por ejemplo, 0011 se acepta y 0101 se rechaza aunque tengan las mismas
> cantidades de ceros y unos.

| Entrada | Comportamiento | Explicación |
|---|---|---|
| `01` | Acepta | Un cero seguido de un uno |
| `0011` | Acepta | Dos ceros seguidos de dos unos |
| `000111` | Acepta | Tres ceros seguidos de tres unos |
| ε | Rechaza | Se exige n ≥ 1 |
| `001` | Rechaza | Falta un uno para emparejar el segundo cero |
| `011` | Rechaza | Sobra un uno |
| `0101` | Rechaza | Hay un cero después de empezar la zona de unos |
| `2` o `201` | No se detiene | El primer símbolo activa la oscilación |
| `012` | Rechaza | El 2 aparece fuera de la primera posición |

El `2` forma parte de Σ porque es una entrada válida para demostrar la ejecución
infinita. Esa entrada no pertenece al lenguaje aceptado. Como algunas cadenas
no terminan, esta máquina **reconoce** el lenguaje, pero no lo **decide** sobre Σ*.

## 5. Explicación del diagrama

Abre `diagrama.svg` o `diagrama.png`. Todas las transiciones del archivo están
representadas, algunas con etiquetas agrupadas para que el dibujo sea legible.

Una etiqueta `0/X, R` significa: leer `0`, escribir `X` y mover a la derecha.
La flecha apunta al siguiente estado. `a/a, L` para `a en {0,1,X,Y}` representa
cuatro reglas que conservan el símbolo y se mueven a la izquierda.

La flecha inicial apunta a `q0`. Los estados finales tienen doble círculo y se
identifican por nombre y resultado, además del color.

### Función de cada estado

| Estado | Trabajo que realiza |
|---|---|
| q0 | Salta X; marca el siguiente 0; si encuentra Y inicia la comprobación final |
| qBusca1 | Avanza sobre 0 y Y hasta encontrar un 1 sin marcar; lo convierte en Y |
| qRegresa | Retrocede hasta el blanco anterior a la entrada y vuelve a q0 |
| qVerifica | Asegura que solo queden Y hasta encontrar blanco |
| qIda | Conserva el símbolo y mueve una celda a la derecha hacia qVuelta |
| qVuelta | Conserva el símbolo y vuelve una celda a la izquierda hacia qIda |
| qAcepta | Detiene la ejecución con aceptación |
| qRechaza | Detiene la ejecución con rechazo |

### Tabla completa de δ

Cada celda es `(estado siguiente, símbolo escrito, movimiento)`. Un guion en
los estados finales significa «sin transición», porque la máquina ya se detuvo.

| Estado / leído | 0 | 1 | 2 | X | Y | _ |
|---|---|---|---|---|---|---|
| q0 | (qBusca1,X,R) | (qRechaza,1,R) | (qIda,2,R) | (q0,X,R) | (qVerifica,Y,R) | (qRechaza,_,R) |
| qBusca1 | (qBusca1,0,R) | (qRegresa,Y,L) | (qRechaza,2,R) | (qRechaza,X,R) | (qBusca1,Y,R) | (qRechaza,_,R) |
| qRegresa | (qRegresa,0,L) | (qRegresa,1,L) | (qRechaza,2,R) | (qRegresa,X,L) | (qRegresa,Y,L) | (q0,_,R) |
| qVerifica | (qRechaza,0,R) | (qRechaza,1,R) | (qRechaza,2,R) | (qRechaza,X,R) | (qVerifica,Y,R) | (qAcepta,_,R) |
| qIda | (qVuelta,0,R) | (qVuelta,1,R) | (qVuelta,2,R) | (qVuelta,X,R) | (qVuelta,Y,R) | (qVuelta,_,R) |
| qVuelta | (qIda,0,L) | (qIda,1,L) | (qIda,2,L) | (qIda,X,L) | (qIda,Y,L) | (qIda,_,L) |
| qAcepta | — | — | — | — | — | — |
| qRechaza | — | — | — | — | — | — |

### Por qué funciona el emparejamiento

Para una entrada `0ⁿ1ⁿ`, después de k emparejamientos la cinta contiene:

```text
Xᵏ 0ⁿ⁻ᵏ Yᵏ 1ⁿ⁻ᵏ
```

Los espacios de esta fórmula separan bloques; no son celdas de la cinta. Cada
vuelta marca exactamente un cero y un uno. El estado `qBusca1` puede atravesar
los Y que dejaron las vueltas anteriores. Después, `qRegresa` coloca el cabezal
otra vez al inicio, sin recordar en variables cuántos símbolos se marcaron.

Cuando ya no quedan ceros, `q0` encuentra el primer Y y pasa a `qVerifica`.
Solo acepta si el resto también son Y y luego aparece blanco. Un uno adicional
o un cero fuera de orden causa rechazo. Si falta un uno, `qBusca1` llega al blanco
y rechaza. Si no existe ningún cero inicial, `q0` rechaza `1` o blanco directamente.

En cualquier entrada binaria, cada emparejamiento consume un cero sin marcar.
Cada búsqueda y regreso recorre un tramo finito, y finalmente se acepta o rechaza.
El ciclo intencional está separado en los estados qIda y qVuelta.

## 6. Cómo se guarda y valida la especificación

Abre `ejemplos/aceptacion.txt`.

**Puedes decir:**

> Los primeros campos describen los conjuntos, el blanco y los estados especiales.
> El campo entrada contiene la cadena que se coloca en la cinta. Después de la
> palabra transiciones se escribe la función delta, una regla por línea.

Muestra esta regla:

```text
q0 0 -> qBusca1 X R
```

Su interpretación formal es:

```text
δ(q0, 0) = (qBusca1, X, R)
```

El programa separa cada línea en seis tokens. El tercero debe ser `->`.
La clave del diccionario de reglas es la pareja `(q0, 0)` y su valor es la terna
`(qBusca1, X, R)`. Usar una pareja como clave permite buscar directamente la acción.

Antes de simular se comprueba la consistencia de la especificación. No basta con
que el texto se pueda leer: los estados deben existir, los símbolos deben
pertenecer a los alfabetos y no puede haber dos reglas para la misma pareja.
También deben estar todas las reglas de los estados no finales.

**Ejemplo para explicar la validación:** si se cambia `R` por `S`, aparece un error.
Si se duplica `q0 0`, se rechaza la especificación por repetir la misma clave,
en lugar de sobrescribir silenciosamente la regla anterior. Si se borra una regla,
se informa exactamente qué pareja quedó sin definir.

Un error de archivo **no equivale** al rechazo de una cadena: en el primer caso
no hay una máquina válida que ejecutar; en el segundo sí se ejecutó una máquina
y esta llegó explícitamente a `qRechaza`.

## 7. Explicación del código por funciones

El código está comentado por instrucciones y bloques. Este apartado explica
el propósito de cada función y las construcciones principales de Python.

### Importaciones y clases de datos

`argparse` lee argumentos de la terminal. `Path` maneja rutas y archivos.
`re` valida nombres mediante una expresión regular. `TextIO` es una anotación
que indica que un parámetro representa un archivo de texto abierto.

`@dataclass` genera el constructor de una clase a partir de sus atributos.
`Maquina` agrupa los componentes de la especificación. `Resultado` agrupa motivo,
número de pasos y último estado. `frozen=True` impide reasignar sus atributos;
no congela automáticamente el contenido de un diccionario, por lo que el código
también evita modificar la tabla de transiciones después de cargarla.

Las anotaciones como `str`, `int` o `dict[tuple[str, str], ...]` documentan tipos.
La validación explícita comprueba los valores; las anotaciones por sí solas
no verifican el contenido leído del archivo.

### `cargar_maquina(ruta)`

1. Define las claves obligatorias y prepara los contenedores de la descripción.
2. Abre el archivo con `with`, que garantiza su cierre al salir del bloque.
3. Lee una línea por vez y obtiene su número mediante `enumerate`.
4. Quita comentarios con `split('#', 1)` y espacios externos con `strip()`.
5. Antes de `transiciones:`, interpreta cada campo y detecta duplicados.
6. Después, descompone cada regla y rechaza claves de transición repetidas.
7. Comprueba que no falten campos ni la sección de reglas.
8. Convierte estados y alfabetos a `frozenset`, conjuntos que no se modifican.
9. Construye `Maquina`, llama a `validar_maquina` y devuelve la descripción válida.

La función interna `leer_conjunto(nombre)` evita repetir la conversión de las
tres listas y detecta elementos duplicados antes de convertirlos a conjunto.
`raise ValueError(...)` interrumpe la carga y explica por qué el contenido es inválido.

### `validar_maquina(maquina)`

Revisa los componentes formales y las restricciones del formato. El operador
`<=` entre conjuntos significa «es subconjunto de». `|` calcula la unión, y `-`
calcula la diferencia. `any(...)` devuelve verdadero cuando al menos un elemento
incumple la condición evaluada.

Al final recorre cada estado no final y cada símbolo de Γ para verificar que
δ esté completa. La unicidad de reglas se revisó al cargar el archivo, antes
de introducirlas al diccionario, para no perder una repetición por sobrescritura.

### `Cinta.__init__(entrada, blanco)`

Coloca cada carácter de la entrada en su índice: el primero en 0, el segundo
en 1, etc. El diccionario `celdas` es una representación dispersa de la única
cinta; una posición no almacenada se interpreta como blanco.

### `Cinta.leer(posicion)` y `Cinta.escribir(posicion, simbolo)`

`leer` utiliza `get` con el blanco como valor predeterminado. `escribir` cambia
la celda indicada. Si escribe blanco, elimina esa clave con `pop(posicion, None)`;
es equivalente a mantener explícitamente una celda blanca, pero ocupa menos espacio.

Estas funciones permiten que la máquina use posiciones negativas y posiciones
positivas nuevas sin reservar previamente una lista de tamaño fijo.

### `Cinta.escribir_configuracion(archivo, estado, cabezal)`

Calcula los extremos que contienen todas las celdas no blancas y el cabezal.
Recorre ese intervalo y escribe el nombre del estado inmediatamente antes del
símbolo bajo el cabezal. No añade el estado a la cinta: solo lo incorpora a la
representación textual de salida.

No conserva las configuraciones anteriores. Se recorre la cinta para mostrarla,
pero ese recorrido pertenece al informe del simulador y no cuenta como pasos
de la MT. Solo aplicar una regla de δ incrementa el número de transiciones.

### `simular(maquina, archivo, max_pasos)`

Inicializa la cinta, el estado, el cabezal en 0 y el contador de pasos. Escribe
C0 y repite este procedimiento:

```python
leido = cinta.leer(cabezal)
destino, escrito, movimiento = maquina.transiciones[(estado, leido)]
cinta.escribir(cabezal, escrito)
cabezal += 1 if movimiento == "R" else -1
estado = destino
pasos += 1
```

**Explicación línea por línea:**

1. Lee el símbolo de la celda donde está el cabezal.
2. Busca en δ la acción correspondiente al estado y al símbolo, y desempaqueta la terna.
3. Escribe el nuevo símbolo en la misma celda que acaba de leer.
4. Suma uno a la posición si se mueve a la derecha; resta uno si se mueve a la izquierda.
5. Actualiza el estado de control con el destino indicado por la regla.
6. Cuenta una transición efectuada para el informe y el límite de ejecución.

Después se escribe la configuración nueva. El bucle se detiene si observa
aceptación, rechazo o si agota el máximo de pasos. Los estados finales se
comprueban antes del límite para que aceptar exactamente en el último paso
permitido siga reportándose como aceptación.

El contador no cuenta ceros ni unos y no decide qué regla aplicar. Es una
protección externa para ejecutar ejemplos que podrían no detenerse.

### `entero_no_negativo(texto)` y `main()`

La primera convierte `--max-pasos` a entero y rechaza argumentos negativos.
`main` recibe las rutas, impide usar el mismo archivo para entrada y salida,
carga y valida la máquina, abre el archivo de salida y llama al simulador.

Los errores de archivo, codificación o validación se muestran como mensajes
legibles. El programa devuelve 1 si hay un error y 0 si la simulación se ejecuta
correctamente, incluso cuando la máquina rechaza o se alcanza el límite.
Ese código de proceso pertenece a la terminal y no al estado formal de la MT.

El bloque `if __name__ == '__main__':` ejecuta `main()` al abrir el programa;
al importar el módulo desde las pruebas, no inicia automáticamente la simulación.

## 8. Configuraciones: cómo leer la salida

Se usa **α q β**, con el estado antes del símbolo que está leyendo el cabezal.
Los espacios separan el nombre del estado de las partes de la cinta.

```text
X qBusca1 011
```

Aquí α es `X`, el estado es `qBusca1` y β es `011`. El cabezal lee el primer `0`
de β. La siguiente transición conserva ese cero y mueve a la derecha:

```text
X qBusca1 011 ⊢ X0 qBusca1 11
```

Si el cabezal se mueve a la izquierda de toda la entrada, la configuración
incluye un blanco a la izquierda. Si se mueve después de la parte escrita,
aparece blanco a la derecha. Nunca se pierde el símbolo que está leyendo.
Los rótulos C0, C1, etc. son números de referencia fuera de la cinta.

## 9. Demostración en vivo

### Aceptación

Ejecuta:

```powershell
python simulador.py ejemplos/aceptacion.txt -o salidas/aceptacion.txt
```

Abre la salida y muestra estos momentos:

```text
C0: q0 0011
⊢ C1: X qBusca1 011
⊢ C3: X qRegresa 0Y1
⊢ C6: q0 X0Y1
⊢ C10: XX qRegresa YY
⊢ C14: q0 XXYY
⊢ C19: XXYY_ qAcepta _
```

Es una selección de la traza; el archivo sí contiene todas las configuraciones
intermedias. Cada `⊢ Ck` en el archivo sigue a Ck−1, no al renglón previo de esta
selección abreviada.

**Puedes decir:**

> Primero marco un cero y un uno. Regreso al inicio y hago el segundo emparejamiento.
> Finalmente quedan XXYY. La comprobación encuentra solo Y hasta llegar al blanco
> y entra al estado de aceptación. Se ejecutaron 19 transiciones.

### Rechazo

```powershell
python simulador.py ejemplos/rechazo.txt -o salidas/rechazo.txt
```

La cadena `001` permite emparejar un cero con un uno. Al buscar el segundo uno,
la máquina encuentra blanco:

```text
⊢ C9: XXY qBusca1 _
⊢ C10: XXY_ qRechaza _
```

Se ejecutaron 10 transiciones. El rechazo es consecuencia de una regla explícita
de δ y no de que el simulador haya decidido contar símbolos por su cuenta.

### Ciclo infinito

```powershell
python simulador.py ejemplos/ciclo.txt -o salidas/ciclo.txt --max-pasos 12
```

```text
C0: q0 2
⊢ C1: 2 qIda _
⊢ C2: 2_ qVuelta _
⊢ C3: 2 qIda _
⊢ C4: 2_ qVuelta _
```

**Demostración:** C1 y C3 tienen la misma cinta completa, el mismo estado y el
cabezal en la misma posición. qIda mueve de la posición 1 a la 2, y qVuelta vuelve
de la 2 a la 1. Ninguna regla cambia símbolos. Por determinismo, a partir de C3
ocurre exactamente lo que ocurrió a partir de C1, una y otra vez. No se llega
a ninguno de los dos estados finales.

El archivo termina después de 12 transiciones porque el **simulador** interrumpe
la demostración. La **máquina** no se ha detenido. No existe un estado formal
llamado `LIMITE_ALCANZADO`; es una etiqueta del informe.

Una traza truncada no basta para demostrar infinitud en general. Por ejemplo,
`0011` con `--max-pasos 5` también alcanza el límite, pero sabemos que acepta en
19 transiciones. El proyecto no intenta resolver el problema de la parada ni
almacena un historial para buscar ciclos en máquinas arbitrarias.

## 10. Memoria, rendimiento y pruebas

### Por qué se utiliza una sola cinta

La información de los emparejamientos está en X y Y. La MT no dispone de una
pila, cola, segunda cinta ni variables con cantidades de ceros y unos. El
diccionario es la cinta misma; la tabla δ es el programa fijo. Estado y posición
del cabezal representan el control de la máquina.

Python necesariamente utiliza memoria para ejecutar el simulador y leer la
descripción. Eso no proporciona a la máquina simulada otra memoria de trabajo.
La salida se escribe conforme ocurre la ejecución y no se utiliza para tomar
decisiones. Las pruebas almacenan texto para comparar resultados; ese código
de verificación no pertenece al cálculo de la MT.

### Rendimiento

Para una cadena aceptada de longitud m, la MT realiza recorridos sucesivos para
emparejar símbolos; su número de transiciones es O(m²). Esto se refiere a la
máquina diseñada, no a cualquier máquina que pueda ejecutar el simulador.

El tiempo del programa anfitrión también incluye escribir las configuraciones:
cada registro recorre el tramo visible de cinta y busca sus extremos. Por eso
no debe confundirse el número de transiciones con el tiempo total de Python.
En cadenas largas, el archivo de configuraciones puede crecer considerablemente.

### Pruebas automatizadas

```powershell
python -m unittest discover -s tests -v
```

Las pruebas verifican el lenguaje contra su definición en todas las **511 cadenas
binarias de longitud 0 a 8**. También comprueban una traza exacta para `01`, los
estados finales justo en el límite, la cinta a la izquierda, el borrado, el ciclo
intencional y la reproducción de las tres salidas entregadas.

Se incluyen archivos inválidos construidos durante las pruebas: reglas repetidas
o ausentes, movimientos incorrectos, estados desconocidos y alfabetos incoherentes,
entre otros. Estas verificaciones aportan evidencia de funcionamiento; el argumento
del emparejamiento explica por qué el diseño reconoce el lenguaje en general.

## 11. Preguntas que podrían hacerte

**¿Por qué no utilizaste un contador para comparar ceros y unos?**

Porque la máquina debe usar su cinta como memoria de trabajo. Las marcas X y Y
registran qué símbolos ya fueron emparejados. El contador de pasos solo limita
la simulación y no interviene en la función de transición.

**¿Por qué δ se guarda en un diccionario?**

Porque su clave es exactamente el par que determina la acción: estado y símbolo
leído. Además permite verificar que no existan dos acciones para la misma clave.

**¿Qué pasa si falta una regla?**

Este proyecto exige δ total sobre los estados no finales, así que informa un
error antes de ejecutar. No inventa una transición ni lo confunde con rechazo.

**¿Qué pasa con la cadena vacía?**

Se escribe `entrada:` sin valor. La cinta empieza blanca y q0 pasa a qRechaza,
porque el lenguaje exige al menos un cero y un uno.

**¿Cómo sabes que `2` no termina?**

Porque se repite la configuración completa cada dos transiciones. Repetir solo
un estado no sería suficiente: una máquina puede visitar el mismo estado con
distintas cintas o posiciones del cabezal y después detenerse.

**¿El límite de pasos rechaza una cadena?**

No. Solo interrumpe el programa anfitrión y registra `LIMITE_ALCANZADO`.
Aceptar o rechazar requiere llegar a uno de los dos estados finales.

**¿Puedes ejecutar otra máquina con este programa?**

Sí, si sus componentes respetan el formato y el modelo documentados. Las reglas
se cargan del archivo; el bucle de simulación no contiene reglas especiales para
el lenguaje de ceros y unos ni para detectar el símbolo 2.

**¿El archivo del ciclo tiene infinitas configuraciones?**

No. Es un prefijo finito de una ejecución infinita, acompañado de la explicación
del límite. Guardar una ejecución infinita completa no es posible en un archivo finito.

## 12. Preparación de la entrega

Ten a mano `simulador.py`, el diagrama, las tres entradas y las tres salidas.
Revisa los comandos en tu computadora y practica explicar una transición sin
leer los comentarios. El README sirve como manual y este guion como material
de estudio para la revisión del código.

La carga a Canvas corresponde al estudiante. Los archivos del proyecto cubren
el programa, el diseño y los ejemplos solicitados; la presentación y revisión
presencial se realizan en la fecha que indique el docente.
