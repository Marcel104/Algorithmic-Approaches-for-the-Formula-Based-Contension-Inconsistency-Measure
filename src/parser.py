import re
import os
from sympy import symbols
from sympy.logic.boolalg import to_cnf, Or, Not

# Wandelt eine Wissensbasis in der angegebenen Datei in CNF um
def parse_kb_to_cnf(filepath):

    with open(filepath, "r") as myFile:
        rows = myFile.readlines()

    # Wissensbasis in einheitliche Schreibweise umwandeln
    knowledgebase_text = " & ".join([row.strip() for row in rows])
    knowledgebase_text = knowledgebase_text.replace("||", "|").replace("&&", "&").replace("!", "~")

    max_symbol_index = -1
    for match in re.findall(r"A(\d+)", knowledgebase_text):
        num = int(match)
        if num > max_symbol_index:
            max_symbol_index = num

    if max_symbol_index >= 0:
        symbol_names = [f'A{i}' for i in range(max_symbol_index + 1)]
        symbols_dic = symbols(symbol_names)
        symbol_mapping = {name: symbol for name, symbol in zip(symbol_names, symbols_dic)}
    else:
        print(f"No symbols 'A<Zahl>' found in {filepath}.")
        symbol_mapping = {}

    for name, symbol in symbol_mapping.items():
        knowledgebase_text = knowledgebase_text.replace(name, str(symbol))

    cnf_knowledgebase = to_cnf(knowledgebase_text, simplify=False)

    # Wissensbasis in Textform zu Zahlen umwandeln
    def lit_to_int(literal):
        if literal.is_Symbol:
            return int(str(literal)[1:]) + 1
        elif isinstance(literal, Not):
            return -(int(str(literal.args[0])[1:]) + 1)
        else:
            raise ValueError(f"Unknown literal: {literal}")

    def clause_to_list(clause):
        return [lit_to_int(lit) for lit in (clause.args if isinstance(clause, Or) else [clause])]

    K = []
    if cnf_knowledgebase.is_Atom or isinstance(cnf_knowledgebase, Or):
        K.append(clause_to_list(cnf_knowledgebase))
    else:
        for clause in cnf_knowledgebase.args:
            K.append(clause_to_list(clause))

    return K

# Liest das gesamte Verzeichnis aus und gibt eine Liste der enthaltenen Dateien aus
def process_directory(directory_path):
    files = {}

    for filename in os.listdir(directory_path):
        if filename.endswith(".txt"):
            filepath = os.path.join(directory_path, filename)
            print(f"File found: {filepath}")
            files[filename] = filepath

    return files
