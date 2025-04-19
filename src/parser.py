import re
import os
from sympy import symbols
from sympy.logic.boolalg import to_cnf, Or, Not, And

def structure_knowledgebase(filepath):
    with open(filepath, "r") as myFile:
        rows = myFile.readlines()

    original_formulas = [row.strip().replace("||", "|").replace("&&", "&").replace("!", "~") for row in rows]

    return original_formulas

# Wandelt eine Wissensbasis in der angegebenen Datei in CNF um
def parse_kb_to_cnf(original_formulas):

    # Jede ursprüngliche Formel einzeln in CNF umwandeln
    cnf_formulas = [[to_cnf(formula, simplify=False)] for formula in original_formulas]

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

    # Wissensbasis zusammensetzen
    K = []
    for cnf_formula_list in cnf_formulas:
        cnf_formula = cnf_formula_list[0]
        if cnf_formula.is_Atom or (isinstance(cnf_formula, Not) and cnf_formula.args[0].is_Atom) or isinstance(cnf_formula, Or):
            K.append([clause_to_list(cnf_formula)])
        elif isinstance(cnf_formula, And):
            K.append([clause_to_list(clause) for clause in cnf_formula.args])
        else:
            K.append([])

    return K