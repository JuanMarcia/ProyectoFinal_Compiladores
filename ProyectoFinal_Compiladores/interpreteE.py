import re
from collections import defaultdict
import tkinter as tk
from tkinter import scrolledtext, messagebox
from PIL import Image, ImageTk
import tkinter as tk
from tkinter import scrolledtext, messagebox, font as tkFont
from tkinter import ttk  # Importar ttk para widgets temáticos
import math
import sys
import threading # Para ejecución en segundo plano
import queue 

class AnalizadorLexico:
    def __init__(self):
        self.tokens = [
            ('COMENTARIO', r'#.*'),
            ('PALABRA_CLAVE', r'\b(var|funcion|imprimir|si|sino|mientras|para|retornar|finfuncion|fin|verdadero|falso)\b'),
            ('OPERADOR', r'(\+|\-|\*|\/|%|==|!=|<=|>=|=|<|>|y|o|no)'),
            ('DELIMITADOR', r'(\(|\)|\{|\}|:|,|;)'),
            ('NUMERO', r'\b\d+(\.\d+)?\b'),
            ('CADENA', r'"[^"]*"'),
            ('IDENTIFICADOR', r'\b[a-zA-Z_][a-zA-Z0-9_]*\b'),
            ('ESPACIO', r'\s+')
        ]
        self.errores = []

    def tokenizar(self, codigo):
        tokens = []
        posicion = 0
        linea = 1
        columna = 1
        
        while posicion < len(codigo):
            match = None
            for tipo, patron in self.tokens:
                regex = re.compile(patron)
                match = regex.match(codigo, posicion)
                if match:
                    valor = match.group(0)
                    if tipo not in ['ESPACIO', 'COMENTARIO']:
                        tokens.append({
                            'tipo': tipo,
                            'valor': valor,
                            'linea': linea,
                            'columna': columna
                        })
                    if '\n' in valor:
                        linea += valor.count('\n')
                        columna = 1
                    else:
                        columna += len(valor)
                    posicion = match.end()
                    break
            if not match:
                caracter = codigo[posicion]
                self.errores.append({
                    'caracter': caracter,
                    'linea': linea,
                    'columna': columna
                })
                posicion += 1
                columna += 1
        
        return tokens, self.errores

class AnalizadorSintactico:
    def __init__(self, tokens):
        self.tokens = tokens
        self.posicion = 0
        self.errores = []
        self.arbol = {
            'tipo': 'PROGRAMA',
            'hijos': []
        }

    def analizar(self):
        while not self.fin_tokens():
            try:
                nodo = self.declaracion()
                if nodo:
                    self.arbol['hijos'].append(nodo)
            except Exception as e:
                self.error_sintactico(str(e))
                while not self.fin_tokens() and self.tokens[self.posicion]['valor'] != '\n':
                    self.posicion += 1
                self.posicion += 1
        
        return self.arbol, self.errores

    def fin_tokens(self):
        return self.posicion >= len(self.tokens)

    def declaracion(self):
        if self.comparar('PALABRA_CLAVE', 'funcion'):
            return self.declaracion_funcion()
        elif self.comparar('PALABRA_CLAVE', 'var'):
            return self.declaracion_variable()
        elif self.comparar('PALABRA_CLAVE', 'imprimir'):
            return self.declaracion_imprimir()
        elif self.comparar('PALABRA_CLAVE', 'si'):
            return self.declaracion_si()
        elif self.comparar('PALABRA_CLAVE', 'mientras'):
            return self.declaracion_mientras()
        elif self.comparar('PALABRA_CLAVE', 'para'):
            return self.declaracion_para()
        elif self.comparar('PALABRA_CLAVE', 'retornar'):
            expresion = self.expresion()
            return {'tipo': 'RETORNO', 'expresion': expresion}
        elif self.comparar('IDENTIFICADOR'):
            identificador = self.anterior()
            if self.comparar('OPERADOR', '='):
                expresion = self.expresion()
                return {
                    'tipo': 'ASIGNACION',
                    'identificador': identificador,
                    'expresion': expresion
                }
            elif self.comparar('DELIMITADOR', '('):  # Llamada a función como statement
                argumentos = []
                if not self.comparar('DELIMITADOR', ')'):
                    while True:
                        argumentos.append(self.expresion())
                        if not self.comparar('DELIMITADOR', ','):
                            break
                    if not self.comparar('DELIMITADOR', ')'):
                        raise SyntaxError("Se esperaba ')' después de argumentos")
                return {
                    'tipo': 'LLAMADA_FUNC',
                    'nombre': identificador['valor'],
                    'argumentos': argumentos
                }
            raise SyntaxError("Se esperaba '=' o '(' después de identificador")
        else:
            token = self.siguiente() if not self.fin_tokens() else {'valor': 'EOF'}
            raise SyntaxError(f"Declaración inválida, token inesperado: {token['valor']}")

    def declaracion_funcion(self):
        if not self.comparar('IDENTIFICADOR'):
            raise SyntaxError("Se esperaba nombre de función")
        nombre = self.anterior()['valor']
        
        if not self.comparar('DELIMITADOR', '('):
            raise SyntaxError("Se esperaba '(' después del nombre")
        
        parametros = []
        if not self.comparar('DELIMITADOR', ')'):
            while True:
                if not self.comparar('IDENTIFICADOR'):
                    raise SyntaxError("Se esperaba parámetro")
                parametros.append(self.anterior()['valor'])
                if not self.comparar('DELIMITADOR', ','):
                    break
            if not self.comparar('DELIMITADOR', ')'):
                raise SyntaxError("Se esperaba ')' después de parámetros")
        
        if not self.comparar('DELIMITADOR', '{'):
            raise SyntaxError("Se esperaba '{' para iniciar cuerpo")
        
        cuerpo = []
        while not self.comparar('PALABRA_CLAVE', 'finfuncion'):
            if self.fin_tokens():
                raise SyntaxError("Se esperaba 'finfuncion'")
            declaracion = self.declaracion()
            if declaracion:
                cuerpo.append(declaracion)
        
        return {
            'tipo': 'DECLARACION_FUNC',
            'nombre': nombre,
            'parametros': parametros,
            'cuerpo': cuerpo
        }

    def declaracion_variable(self):
        if not self.comparar('IDENTIFICADOR'):
            raise SyntaxError("Se esperaba un identificador después de 'var'")
        nombre = self.anterior()['valor']
    
        if not self.comparar('OPERADOR', '='):
            raise SyntaxError("Se esperaba '=' en declaración de variable")
    
        expresion = self.expresion()
    
        return {
            'tipo': 'DECLARACION_VAR',
            'nombre': nombre,
            'valor': expresion
        }

    def declaracion_imprimir(self):
        expresion = self.expresion()
        return {
            'tipo': 'IMPRIMIR',
            'expresion': expresion
        }

    def declaracion_si(self):
        if not self.comparar('DELIMITADOR', '('):
            raise SyntaxError("Se esperaba '(' después de 'si'")
        
        condicion = self.expresion()
        
        if not self.comparar('DELIMITADOR', ')'):
            raise SyntaxError("Se esperaba ')' después de condición")
        
        if not self.comparar('DELIMITADOR', '{'):
            raise SyntaxError("Se esperaba '{' para iniciar bloque")
        
        bloque_si = []
        while not self.comparar('DELIMITADOR', '}'):
            if self.fin_tokens():
                raise SyntaxError("Se esperaba '}' para cerrar bloque")
            declaracion = self.declaracion()
            if declaracion:
                bloque_si.append(declaracion)
        
        bloque_sino = []
        if self.comparar('PALABRA_CLAVE', 'sino'):
            if not self.comparar('DELIMITADOR', '{'):
                raise SyntaxError("Se esperaba '{' para iniciar bloque sino")
            while not self.comparar('DELIMITADOR', '}'):
                if self.fin_tokens():
                    raise SyntaxError("Se esperaba '}' para cerrar bloque sino")
                declaracion = self.declaracion()
                if declaracion:
                    bloque_sino.append(declaracion)
        
        return {
            'tipo': 'SI',
            'condicion': condicion,
            'bloque_si': bloque_si,
            'bloque_sino': bloque_sino
        }

    def declaracion_mientras(self):
        if not self.comparar('DELIMITADOR', '('):
            raise SyntaxError("Se esperaba '(' después de 'mientras'")
        
        condicion = self.expresion()
        
        if not self.comparar('DELIMITADOR', ')'):
            raise SyntaxError("Se esperaba ')' después de condición")
        
        if not self.comparar('DELIMITADOR', '{'):
            raise SyntaxError("Se esperaba '{' para iniciar bloque")
        
        bloque = []
        while not self.comparar('DELIMITADOR', '}'):
            if self.fin_tokens():
                raise SyntaxError("Se esperaba '}' para cerrar bloque")
            declaracion = self.declaracion()
            if declaracion:
                bloque.append(declaracion)
        
        return {
            'tipo': 'MIENTRAS',
            'condicion': condicion,
            'bloque': bloque
        }
    
    def declaracion_para(self):
        if not self.comparar('DELIMITADOR', '('):
            raise SyntaxError("Se esperaba '(' después de 'para'")
    
    # Inicialización (obligatoria con 'var')
        if not self.comparar('PALABRA_CLAVE', 'var'):
            raise SyntaxError("Se esperaba 'var' en inicialización de 'para'")
        inicializacion = self.declaracion_variable()
    
    # Condición (obligatoria)
        if not self.comparar('DELIMITADOR', ';'):
            raise SyntaxError("Se esperaba ';' después de inicialización")
        condicion = self.expresion()
    
    # Actualización (opcional)
        if not self.comparar('DELIMITADOR', ';'):
            raise SyntaxError("Se esperaba ';' después de condición")
        actualizacion = None
        if self.comparar('IDENTIFICADOR'):
            identificador = self.anterior()
        if self.comparar('OPERADOR', '='):
            actualizacion = {
                'tipo': 'ASIGNACION',
                'identificador': identificador,
                'expresion': self.expresion()
            }
    
        if not self.comparar('DELIMITADOR', ')'):
            raise SyntaxError("Se esperaba ')' después de actualización")
    
    # Bloque de código
        if not self.comparar('DELIMITADOR', '{'):
            raise SyntaxError("Se esperaba '{' para iniciar bloque")
    
        bloque = []
        while not self.comparar('DELIMITADOR', '}'):
            if self.fin_tokens():
                raise SyntaxError("Se esperaba '}' para cerrar bloque")
            declaracion = self.declaracion()
            if declaracion:
                bloque.append(declaracion)
    
        return {    
        'tipo': 'PARA',
        'inicializacion': inicializacion,
        'condicion': condicion,
        'actualizacion': actualizacion,
        'bloque': bloque
    }

    def expresion(self):
        expr = self.expresion_simple()
        
        while True:
            if self.comparar('OPERADOR', 'y') or self.comparar('OPERADOR', 'o'):
                operador = self.anterior()['valor']
                derecha = self.expresion_simple()
                expr = {
                    'tipo': 'OPERACION_BINARIA',
                    'izquierda': expr,
                    'operador': operador,
                    'derecha': derecha
                }
            else:
                break
        
        if self.comparar('OPERADOR'):
            operador = self.anterior()['valor']
            derecha = self.expresion()
            return {
                'tipo': 'OPERACION_BINARIA',
                'izquierda': expr,
                'operador': operador,
                'derecha': derecha
            }
        return expr

    def expresion_simple(self):
        if self.comparar('OPERADOR', 'no'):
            return {
                'tipo': 'OPERACION_UNARIA',
                'operador': 'no',
                'expresion': self.expresion_simple()
            }
            
        if self.comparar('PALABRA_CLAVE', 'verdadero'):
            return {
                'tipo': 'LITERAL',
                'valor': 'verdadero',
                'tipo_dato': 'BOOLEANO'
            }
        elif self.comparar('PALABRA_CLAVE', 'falso'):
            return {
                'tipo': 'LITERAL',
                'valor': 'falso',
                'tipo_dato': 'BOOLEANO'
            }
        elif self.comparar('NUMERO'):
            return {
                'tipo': 'LITERAL',
                'valor': self.anterior()['valor'],
                'tipo_dato': 'NUMERO'
            }
        elif self.comparar('CADENA'):
            return {
                'tipo': 'LITERAL',
                'valor': self.anterior()['valor'],
                'tipo_dato': 'CADENA'
            }
        elif self.comparar('IDENTIFICADOR'):
            identificador = self.anterior()
            if self.comparar('DELIMITADOR', '('):  # Llamada a función
                argumentos = []
                if not self.comparar('DELIMITADOR', ')'):
                    while True:
                        argumentos.append(self.expresion())
                        if not self.comparar('DELIMITADOR', ','):
                            break
                    if not self.comparar('DELIMITADOR', ')'):
                        raise SyntaxError("Se esperaba ')' después de argumentos")
                return {
                    'tipo': 'LLAMADA_FUNC',
                    'nombre': identificador['valor'],
                    'argumentos': argumentos
                }
            return {
                'tipo': 'IDENTIFICADOR',
                'nombre': identificador['valor']
            }
        elif self.comparar('DELIMITADOR', '('):
            expr = self.expresion()
            if not self.comparar('DELIMITADOR', ')'):
                raise SyntaxError("Se esperaba ')' después de expresión")
            return expr
        else:
            token = self.siguiente() if not self.fin_tokens() else {'valor': 'EOF'}
            raise SyntaxError(f"Expresión inválida, token inesperado: {token['valor']}")

    def comparar(self, tipo, valor=None):
        if not self.fin_tokens():
            token = self.tokens[self.posicion]
            if token['tipo'] == tipo:
                if valor is None or token['valor'] == valor:
                    self.posicion += 1
                    return True
        return False

    def avanzar(self):
        if not self.fin_tokens():
            self.posicion += 1
        return self.anterior()

    def anterior(self):
        if self.posicion > 0:
            return self.tokens[self.posicion - 1]
        return None

    def siguiente(self):
        if not self.fin_tokens():
            return self.tokens[self.posicion]
        return None

    def error_sintactico(self, mensaje):
        if not self.fin_tokens():
            token = self.tokens[self.posicion]
            self.errores.append({
                'mensaje': mensaje,
                'linea': token['linea'],
                'columna': token['columna']
            })
        else:
            self.errores.append({
                'mensaje': mensaje,
                'linea': -1,
                'columna': -1
            })

class Interprete:
    def __init__(self):
        self.variables = {
            'verdadero': True,
            'falso': False
        }
        self.funciones = {}
        self.en_ejecucion = True
        self.pila_ambitos = [{}]

    def ejecutar(self, codigo):
        lexico = AnalizadorLexico()
        tokens, errores_lexico = lexico.tokenizar(codigo)

        if errores_lexico:
            print("\n=== Errores léxicos ===")
            for error in errores_lexico:
                print(f"Línea {error['linea']}, Columna {error['columna']}: Carácter inesperado '{error['caracter']}'")
            return

        sintactico = AnalizadorSintactico(tokens)
        arbol, errores_sintactico = sintactico.analizar()

        if errores_sintactico:
            print("\n=== Errores sintácticos ===")
            for error in errores_sintactico:
                print(f"Línea {error['linea']}: {error['mensaje']}")
            return

        self.ejecutar_arbol(arbol)

    def ejecutar_arbol(self, nodo):
        if not self.en_ejecucion:
            return None

        if nodo['tipo'] == 'PROGRAMA':
            for hijo in nodo['hijos']:
                result = self.ejecutar_arbol(hijo)
                if result is not None and isinstance(result, dict) and result.get('tipo') == 'RETORNO_VALUE':
                    return result['valor']
        elif nodo['tipo'] == 'DECLARACION_FUNC':
            self.funciones[nodo['nombre']] = nodo
        elif nodo['tipo'] == 'DECLARACION_VAR':
            valor = self.evaluar_expresion(nodo['valor'])
            self.variables[nodo['nombre']] = valor
        elif nodo['tipo'] == 'ASIGNACION':
            valor = self.evaluar_expresion(nodo['expresion'])
            self.variables[nodo['identificador']['valor']] = valor
        elif nodo['tipo'] == 'IMPRIMIR':
            valor = self.evaluar_expresion(nodo['expresion'])
            print(valor)
        elif nodo['tipo'] == 'SI':
            condicion = self.evaluar_expresion(nodo['condicion'])
            if condicion:
                for declaracion in nodo['bloque_si']:
                    result = self.ejecutar_arbol(declaracion)
                    if result is not None and isinstance(result, dict) and result.get('tipo') == 'RETORNO_VALUE':
                        return result
            else:
                for declaracion in nodo['bloque_sino']:
                    result = self.ejecutar_arbol(declaracion)
                    if result is not None and isinstance(result, dict) and result.get('tipo') == 'RETORNO_VALUE':
                        return result
        elif nodo['tipo'] == 'MIENTRAS':
            while self.evaluar_expresion(nodo['condicion']) and self.en_ejecucion:
                for declaracion in nodo['bloque']:
                    result = self.ejecutar_arbol(declaracion)
                    if result is not None and isinstance(result, dict) and result.get('tipo') == 'RETORNO_VALUE':
                        return result
        elif nodo['tipo'] == 'PARA':
    # Ejecutar inicialización (ej: var i = 0)
            self.ejecutar_arbol(nodo['inicializacion'])
    
    # Ejecutar el bloque mientras la condición sea verdadera
            while self.evaluar_expresion(nodo['condicion']) and self.en_ejecucion:
        # Ejecutar todas las declaraciones del bloque
                for declaracion in nodo['bloque']:
                    self.ejecutar_arbol(declaracion)
        # Ejecutar actualización (ej: i = i + 1)
                if nodo['actualizacion']:
                    self.ejecutar_arbol(nodo['actualizacion'])
        elif nodo['tipo'] == 'LLAMADA_FUNC':
            return self.llamar_funcion(nodo['nombre'], [self.evaluar_expresion(arg) for arg in nodo['argumentos']])
        elif nodo['tipo'] == 'RETORNO':
            return {'tipo': 'RETORNO_VALUE', 'valor': self.evaluar_expresion(nodo['expresion'])}
        return None

    def llamar_funcion(self, nombre, argumentos):
        if nombre not in self.funciones:
            raise NameError(f"Función no definida: '{nombre}'")

        funcion = self.funciones[nombre]
        if len(argumentos) != len(funcion['parametros']):
            raise ValueError(f"Número incorrecto de argumentos para {nombre}")

        # Guardar estado actual
        variables_originales = self.variables.copy()

        # Crear un nuevo ámbito para la función
        self.variables = variables_originales.copy() # Reset to original, then apply arguments
        for i, param in enumerate(funcion['parametros']):
            self.variables[param] = argumentos[i]

        # Ejecutar cuerpo
        resultado = None
        for nodo in funcion['cuerpo']:
            result = self.ejecutar_arbol(nodo)
            if result is not None and isinstance(result, dict) and result.get('tipo') == 'RETORNO_VALUE':
                resultado = result['valor']
                break

        # Restaurar variables (ámbito anterior)
        # self.variables = variables_originales # This was incorrect, should restore after the loop
        self.variables = variables_originales
        return resultado

    def evaluar_expresion(self, expresion):
        if expresion['tipo'] == 'LITERAL':
            if expresion['tipo_dato'] == 'NUMERO':
                return float(expresion['valor']) if '.' in expresion['valor'] else int(expresion['valor'])
            elif expresion['tipo_dato'] == 'CADENA':
                return expresion['valor'].strip('"')
            elif expresion['tipo_dato'] == 'BOOLEANO':
                return expresion['valor'] == 'verdadero'
        elif expresion['tipo'] == 'IDENTIFICADOR':
            if expresion['nombre'] in self.variables:
                return self.variables[expresion['nombre']]
            raise NameError(f"Variable no definida: '{expresion['nombre']}'")
        elif expresion['tipo'] == 'LLAMADA_FUNC':
            return self.llamar_funcion(expresion['nombre'], [self.evaluar_expresion(arg) for arg in expresion['argumentos']])
        elif expresion['tipo'] == 'OPERACION_BINARIA':
            izquierda = self.evaluar_expresion(expresion['izquierda'])
            derecha = self.evaluar_expresion(expresion['derecha'])
            operador = expresion['operador']

            if operador == '+':
                if isinstance(izquierda, str) or isinstance(derecha, str):
                    return str(izquierda) + str(derecha)
                return izquierda + derecha
            elif operador == '-':
                return izquierda - derecha
            elif operador == '*':
                return izquierda * derecha
            elif operador == '/':
                if derecha == 0:
                    return float('nan')
                return izquierda / derecha
            elif operador == '%':
                if derecha == 0:
                    return float('nan')
                return izquierda % derecha
            elif operador == '==':
                return izquierda == derecha
            elif operador == '!=':
                return izquierda != derecha
            elif operador == '<':
                return izquierda < derecha
            elif operador == '>':
                return izquierda > derecha
            elif operador == '<=':
                return izquierda <= derecha
            elif operador == '>=':
                return izquierda >= derecha
            elif operador == 'y':
                return izquierda and derecha
            elif operador == 'o':
                return izquierda or derecha
            else:
                raise ValueError(f"Operador no soportado: {operador}")
        elif expresion['tipo'] == 'OPERACION_UNARIA':
            if expresion['operador'] == 'no':
                return not self.evaluar_expresion(expresion['expresion'])
            raise ValueError(f"Operador unario no soportado: {expresion['operador']}")

import re
from collections import defaultdict
import tkinter as tk
from tkinter import scrolledtext, messagebox, ttk
from PIL import Image, ImageTk
import math
import sys
import time

class InterfazGrafica:
    def __init__(self):
        self.ventana = tk.Tk()
        self.ventana.title("Jaimamba - Lenguaje de Programación")
        self.ventana.geometry("1000x800")

        self.dark_mode = False
        self.light_colors = {
            'bg': '#f0f0f0',
            'fg': '#333',
            'text_bg': '#fff',
            'text_fg': '#000',
            'insert': '#000',
            'select_bg': '#add8e6',
            'button_bg': '#e0e0e0',
            'button_fg': '#333',
            'button_active_bg': '#d0d0d0',
            'notebook_bg': '#f0f0f0',
            'notebook_tab_bg': '#e0e0e0',
            'notebook_tab_fg': '#333',
            'notebook_tab_selected_bg': '#c0c0c0',
            'status_fg': '#228b22',
            'error_fg': '#ff0000',
            'keyword': '#0000ff',
            'string': '#008000',
            'number': '#ff0000',
            'comment': '#808080',
            'operator': '#800080',
            'delimiter': '#000000'
        }
        self.dark_colors = {
            'bg': '#2c3e50',
            'fg': '#ecf0f1',
            'text_bg': '#34495e',
            'text_fg': '#ecf0f1',
            'insert': '#fff',
            'select_bg': '#16a085',
            'button_bg': '#1abc9c',
            'button_fg': '#ffffff',
            'button_active_bg': '#16a085',
            'notebook_bg': '#2c3e50',
            'notebook_tab_bg': '#34495e',
            'notebook_tab_fg': '#ecf0f1',
            'notebook_tab_selected_bg': '#1abc9c',
            'status_fg': '#2ecc71',
            'error_fg': '#e74c3c',
            'keyword': '#3498db',
            'string': '#2ecc71',
            'number': '#e74c3c',
            'comment': '#95a5a6',
            'operator': '#f39c12',
            'delimiter': '#9b59b6'
        }
        self.colors = self.dark_colors if self.dark_mode else self.light_colors

        # Configuración de estilo
        self.estilo = ttk.Style()
        self.estilo.theme_use('clam')
        self.configurar_estilos()

        self.crear_widgets()
        self.interprete = None  # Initialize interpreter later

        self.ventana.mainloop()

    def configurar_estilos(self):
        """Configura los estilos para los widgets"""
        self.estilo.configure('TFrame', background=self.colors['bg'])
        self.estilo.configure('TLabel', background=self.colors['bg'], foreground=self.colors['fg'], font=('Arial', 10))
        self.estilo.configure('TButton', font=('Arial', 10, 'bold'), padding=5,
                            background=self.colors['button_bg'], foreground=self.colors['button_fg'])
        self.estilo.map('TButton',
                        foreground=[('active', self.colors['fg']), ('!active', self.colors['button_fg'])],
                        background=[('active', self.colors['button_active_bg']), ('!active', self.colors['button_bg'])])
        self.estilo.configure('TNotebook', background=self.colors['notebook_bg'], borderwidth=0)
        self.estilo.configure('TNotebook.Tab', background=self.colors['notebook_tab_bg'], foreground=self.colors['notebook_tab_fg'],
                             padding=[10, 5], font=('Arial', 10, 'bold'))
        self.estilo.map('TNotebook.Tab',
                       background=[('selected', self.colors['notebook_tab_selected_bg']), ('active', self.colors['notebook_tab_selected_bg'])],
                       foreground=[('selected', self.colors['fg']), ('active', self.colors['fg'])])

    def crear_widgets(self):
        """Crea todos los widgets de la interfaz"""
        # Frame principal
        main_frame = ttk.Frame(self.ventana)
        main_frame.pack(fill='both', expand=True, padx=10, pady=10)

        # Header con logo y título
        header_frame = ttk.Frame(main_frame)
        header_frame.pack(fill='x', pady=(0, 15))

        try:
            imagen = Image.open("jajaliko.png")
            imagen = imagen.resize((80, 80), Image.Resampling.LANCZOS)
            self.logo = ImageTk.PhotoImage(imagen)
            logo_label = tk.Label(header_frame, image=self.logo, bg=self.colors['bg'])
            logo_label.pack(side='left', padx=10)
        except:
            logo_label = ttk.Label(header_frame, text="[Logo]", style='TLabel')
            logo_label.pack(side='left', padx=10)

        title_frame = ttk.Frame(header_frame)
        title_frame.pack(side='left', fill='y', expand=True)

        ttk.Label(title_frame, text="Jaimamba", font=('Arial', 24, 'bold'),
                 style='TLabel').pack(anchor='w')
        ttk.Label(title_frame, text="Lenguaje de Programación",
                 style='TLabel').pack(anchor='w')

        # Notebook para pestañas
        self.notebook = ttk.Notebook(main_frame)
        self.notebook.pack(fill='both', expand=True)

        # Pestaña de editor
        editor_frame = ttk.Frame(self.notebook)
        self.notebook.add(editor_frame, text='Editor')

        # Frame de botones
        button_frame = ttk.Frame(editor_frame)
        button_frame.pack(fill='x', pady=(0, 10))

        self.boton_ejecutar = ttk.Button(button_frame, text="Ejecutar (F5)",
                                       command=self.ejecutar_codigo)
        self.boton_ejecutar.pack(side='left', padx=5)

        ttk.Button(button_frame, text="Limpiar",
                 command=self.limpiar_codigo).pack(side='left', padx=5)

        ttk.Button(button_frame, text="Ejemplos",
                 command=self.mostrar_ejemplos).pack(side='left', padx=5)

        self.theme_button = ttk.Button(button_frame, text="Modo Oscuro" if not self.dark_mode else "Modo Claro",
                                        command=self.toggle_theme)
        self.theme_button.pack(side='left', padx=5)

        # Editor de código
        self.texto_codigo = scrolledtext.ScrolledText(
            editor_frame, height=20, width=80,
            font=('Consolas', 12), bg=self.colors['text_bg'], fg=self.colors['text_fg'],
            insertbackground=self.colors['insert'], selectbackground=self.colors['select_bg'],
            wrap=tk.NONE, undo=True, autoseparators=True
        )
        self.texto_codigo.pack(fill='both', expand=True)

        # Configurar scroll horizontal
        x_scroll = tk.Scrollbar(editor_frame, orient='horizontal',
                               command=self.texto_codigo.xview)
        x_scroll.pack(fill='x')
        self.texto_codigo.configure(xscrollcommand=x_scroll.set)

        # Configurar resaltado de sintaxis
        self.configurar_resaltado_sintaxis()

        # Pestaña de salida
        output_frame = ttk.Frame(self.notebook)
        self.notebook.add(output_frame, text='Salida')

        # Área de salida
        self.texto_salida = scrolledtext.ScrolledText(
            output_frame, height=15, width=80,
            font=('Consolas', 11), bg='#1a1a1a' if self.dark_mode else '#f8f8f8', fg='#ffffff' if self.dark_mode else '#000000',
            state='normal', wrap=tk.WORD
        )
        self.texto_salida.pack(fill='both', expand=True, pady=(5, 0))
        self.texto_salida.config(bg=self.colors['text_bg'], fg=self.colors['text_fg'])

        # Frame de estado
        status_frame = ttk.Frame(output_frame)
        status_frame.pack(fill='x', pady=(5, 0))

        self.status_label = ttk.Label(
            status_frame, text="Listo",
            style='TLabel', anchor='w'
        )
        self.status_label.pack(side='left', fill='x', expand=True)

        # Configurar atajos de teclado
        self.configurar_atajos()

        # Insertar código de ejemplo al iniciar
        self.insertar_codigo_ejemplo()

    def toggle_theme(self):
        """Alterna entre modo claro y oscuro"""
        self.dark_mode = not self.dark_mode
        self.colors = self.dark_colors if self.dark_mode else self.light_colors
        self.ventana.configure(bg=self.colors['bg'])
        self.configurar_estilos()

        # Update widget colors manually that are not styled by ttk
        self.texto_codigo.config(bg=self.colors['text_bg'], fg=self.colors['text_fg'],
                                 insertbackground=self.colors['insert'], selectbackground=self.colors['select_bg'])
        self.texto_salida.config(bg=self.colors['text_bg'], fg=self.colors['text_fg'])
        try:
            self.logo_label.config(bg=self.colors['bg'])
        except AttributeError:
            pass # Logo label might not be created yet

        self.status_label.config(background=self.colors['bg'], foreground=self.colors['status_fg'])
        for tab_id in self.notebook.tabs():
            self.notebook.itemconfig(tab_id, background=self.colors['notebook_tab_bg'], foreground=self.colors['notebook_tab_fg'])
        self.notebook.config(background=self.colors['notebook_bg'])

        self.theme_button.config(text="Modo Oscuro" if not self.dark_mode else "Modo Claro")
        self.resaltar_sintaxis() # Re-apply syntax highlighting with new colors

    def configurar_resaltado_sintaxis(self):
        """Configura el resaltado de sintaxis básico"""
        self.texto_codigo.tag_configure('keyword', foreground=self.colors['keyword'])
        self.texto_codigo.tag_configure('string', foreground=self.colors['string'])
        self.texto_codigo.tag_configure('number', foreground=self.colors['number'])
        self.texto_codigo.tag_configure('comment', foreground=self.colors['comment'])
        self.texto_codigo.tag_configure('operator', foreground=self.colors['operator'])
        self.texto_codigo.tag_configure('delimiter', foreground=self.colors['delimiter'])

        # Configurar evento para resaltar
        self.texto_codigo.bind('<KeyRelease>', self.resaltar_sintaxis)

    def resaltar_sintaxis(self, event=None):
        """Resalta la sintaxis del código"""
        keywords = ['var', 'funcion', 'imprimir', 'si', 'sino', 'mientras',
                   'para', 'retornar', 'finfuncion', 'fin', 'verdadero', 'falso']
        operators = ['+', '-', '*', '/', '%', '==', '!=', '<=', '>=', '=', '<', '>', 'y', 'o', 'no']
        delimiters = ['(', ')', '{', '}', '[', ']', ':', ',', ';']

        # Limpiar todos los tags
        for tag in self.texto_codigo.tag_names():
            self.texto_codigo.tag_remove(tag, '1.0', 'end')

        text = self.texto_codigo.get('1.0', 'end-1c')

        # Resaltar palabras clave
        for word in keywords:
            start = '1.0'
            while True:
                start = self.texto_codigo.search(r'\m{}\M'.format(word), start, stopindex='end',
                                               regexp=True, nocase=False)
                if not start:
                    break
                end = f"{start}+{len(word)}c"
                self.texto_codigo.tag_add('keyword', start, end)
                start = end

        # Resaltar operadores
        for op in operators:
            start = '1.0'
            while True:
                start = self.texto_codigo.search(re.escape(op), start, stopindex='end')
                if not start:
                    break
                end = f"{start}+{len(op)}c"
                self.texto_codigo.tag_add('operator', start, end)
                start = end

        # Resaltar delimitadores
        for delim in delimiters:
            start = '1.0'
            while True:
                start = self.texto_codigo.search(re.escape(delim), start, stopindex='end')
                if not start:
                    break
                end = f"{start}+{len(delim)}c"
                self.texto_codigo.tag_add('delimiter', start, end)
                start = end

        # Resaltar cadenas
        start = '1.0'
        while True:
            start = self.texto_codigo.search('"[^"]*"', start, stopindex='end', regexp=True)
            if not start:
                break
            end = self.texto_codigo.search('"', f"{start}+1c", stopindex='end')
            if not end:
                break
            end = f"{end}+1c"
            self.texto_codigo.tag_add('string', start, end)
            start = end

        # Resaltar números
        start = '1.0'
        while True:
            start = self.texto_codigo.search(r'\b\d+(\.\d+)?\b', start, stopindex='end', regexp=True)
            if not start:
                break
            end = self.texto_codigo.search(r'\M', start, stopindex='end', regexp=True)
            if not end:
                end = 'end'
            self.texto_codigo.tag_add('number', start, end)
            start = end

        # Resaltar comentarios
        start = '1.0'
        while True:
            start = self.texto_codigo.search('#.*', start, stopindex='end', regexp=True)
            if not start:
                break
            end = self.texto_codigo.search('\n', start, stopindex='end')
            if not end:
                end = 'end'
            self.texto_codigo.tag_add('comment', start, end)
            start = end

    def configurar_atajos(self):
        """Configura los atajos de teclado"""
        self.ventana.bind('<F5>', lambda e: self.ejecutar_codigo())
        self.ventana.bind('<Control-s>', lambda e: self.guardar_codigo())
        self.ventana.bind('<Control-o>', lambda e: self.cargar_codigo())
        self.ventana.bind('<Control-l>', lambda e: self.limpiar_codigo())

    def insertar_codigo_ejemplo(self):
        """Inserta un código de ejemplo al iniciar"""
        ejemplo = """# Ejemplo de código en Jaimamba

funcion factorial(n){
    si (n <= 1) {
        retornar 1}
    sino{
        retornar n * factorial(n - 1)}
finfuncion

# Calcular factorial de 5
var resultado = factorial(5)
imprimir("El factorial de 5 es: " + resultado)
"""
        self.texto_codigo.insert('1.0', ejemplo)
        self.resaltar_sintaxis()

    def ejecutar_codigo(self):
        """Ejecuta el código escrito en el editor"""
        if self.interprete is None:
            from __main__ import Interprete
            self.interprete = Interprete()

        self.texto_salida.config(state='normal')
        self.texto_salida.delete('1.0', tk.END)
        self.actualizar_estado("Ejecutando código...")
        self.ventana.update()

        codigo = self.texto_codigo.get('1.0', tk.END)

        # Redirigir salida estándar
        original_stdout = sys.stdout
        sys.stdout = self

        try:
            start_time = time.time()
            self.interprete.ejecutar(codigo)
            execution_time = time.time() - start_time
            self.actualizar_estado(f"Ejecución completada en {execution_time:.2f} segundos")
        except Exception as e:
            self.texto_salida.insert(tk.END, f"\nError: {str(e)}\n", 'error')
            self.actualizar_estado(f"Error: {str(e)}", error=True)
        finally:
            sys.stdout = original_stdout
            self.texto_salida.config(state='disabled')

    def write(self, text):
        """Método para redirigir la salida estándar al widget de texto"""
        self.texto_salida.config(state='normal')
        self.texto_salida.insert(tk.END, text)
        self.texto_salida.see(tk.END)
        self.texto_salida.config(state='disabled')
        self.ventana.update()

    def flush(self):
        """Método necesario para redirigir la salida estándar"""
        pass

    def limpiar_codigo(self):
        """Limpia el editor de código"""
        self.texto_codigo.delete('1.0', tk.END)
        self.resaltar_sintaxis() # Volver a aplicar el resaltado a un editor vacío
        self.actualizar_estado("Editor limpiado")

    def mostrar_ejemplos(self):
        """Muestra algunos ejemplos de código en una ventana emergente"""
        ejemplos_texto = """
# Ejemplo 1: Hola Mundo
imprimir("Hola Mundo")

# Ejemplo 2: Declaración de variable y operación
var mensaje = "El resultado es: "
var numero1 = 10
var numero2 = 20
var suma = numero1 + numero2
imprimir(mensaje + suma)

# Ejemplo 3: Estructura condicional
var edad = 18
si (edad >= 18) {
    imprimir("Eres mayor de edad")
} sino {
    imprimir("Eres menor de edad")
}


# Ejemplo 4: Bucle mientras
var contador = 0
mientras (contador < 5) {
    imprimir("Contador: " + contador)
    contador = contador + 1
}

# Ejemplo 5: Definición y llamada de función
funcion saludar(nombre)
    imprimir("Hola, " + nombre)
finfuncion

saludar("Jaimamba")

# Ejemplo 6: Factorial (recursivo)
funcion factorial(n) {
    si (n <= 1) {
        retornar 1
    } sino {
        retornar n * factorial(n - 1)
    }
 finfuncion

var numero = 5
var resultado = factorial(numero)
imprimir(resultado)

# Imprimir números del 1 al 5
para (var i = 1; i <= 5; i = i + 1) {
    imprimir("Número: " + i)
}

# Sumar números pares del 2 al 10
var suma = 0
para (var j = 2; j <= 10; j = j + 2) {
    suma = suma + j
}
imprimir("Suma de pares: " + suma)
"""
        top = tk.Toplevel(self.ventana)
        top.title("Ejemplos de Código")
        ejemplos_scrolled_text = scrolledtext.ScrolledText(top, height=20, width=70, font=('Consolas', 11),
                                                            bg=self.colors['text_bg'], fg=self.colors['text_fg'])
        ejemplos_scrolled_text.insert('1.0', ejemplos_texto)
        ejemplos_scrolled_text.config(state='disabled')
        ejemplos_scrolled_text.pack(padx=10, pady=10, fill='both', expand=True)

    def guardar_codigo(self):
        """Abre un diálogo para guardar el código en un archivo"""
        from tkinter import filedialog
        file = filedialog.asksaveasfile(defaultextension=".jm",
                                        filetypes=[("Jaimamba files", "*.jm"), ("All files", "*.*")])
        if file:
            file.write(self.texto_codigo.get('1.0', tk.END))
            file.close()
            self.actualizar_estado(f"Código guardado en: {file.name}")

    def cargar_codigo(self):
        """Abre un diálogo para cargar código desde un archivo"""
        from tkinter import filedialog
        file = filedialog.askopenfile(filetypes=[("Jaimamba files", "*.jm"), ("All files", "*.*")])
        if file:
            self.texto_codigo.delete('1.0', tk.END)
            self.texto_codigo.insert('1.0', file.read())
            file.close()
            self.resaltar_sintaxis()
            self.actualizar_estado(f"Código cargado desde: {file.name}")

    def actualizar_estado(self, mensaje, error=False):
        """Actualiza la etiqueta de estado en la parte inferior"""
        self.status_label.config(text=mensaje, foreground=self.colors['error_fg'] if error else self.colors['status_fg'], background=self.colors['bg'])

if __name__ == "__main__":
    interfaz = InterfazGrafica()