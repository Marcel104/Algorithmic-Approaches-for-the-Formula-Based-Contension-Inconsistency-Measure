import time
from src.MaxSAT.solver import solve_maxsat, generate_dynamic_clauses
from src.parser import process_directory, parse_kb_to_cnf  # Stelle sicher, dass parse_kb_to_cnf importiert ist

directory_path = "data"
files = process_directory(directory_path)  # Holt die Datei-Pfade

for filename, filepath in files.items():  # filepath ist der tatsächliche Pfad der Datei
    start_time = time.perf_counter()  # Startzeit für die gesamte Verarbeitung

    # Umwandlung in CNF (die eigentliche Parsing-Funktion aufrufen)
    knowledgebase_cnf = parse_kb_to_cnf(filepath)

    # Generiere dynamische Klauseln
    hard_clauses, soft_clauses = generate_dynamic_clauses(knowledgebase_cnf)

    # Lösen mit MaxSAT
    model, weight = solve_maxsat(knowledgebase_cnf, solver_name="Glucose3", hard_clauses=hard_clauses, soft_clauses=soft_clauses)

    end_time = time.perf_counter()  # Endzeit messen
    elapsed_time = (end_time - start_time) * 1000  # Umrechnung in Millisekunden

    if model:
        print(f"knowledgebase: {knowledgebase_cnf}, model: {model}, Ifc: {weight} (time: {elapsed_time:.2f} ms)")
    else:
        print(f"  Keine Lösung gefunden. (Berechnungszeit: {elapsed_time:.2f} ms)")
