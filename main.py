import time
from src.MaxSAT.solver import solve_maxsat, generate_dynamic_clauses
from src.parser import process_directory, parse_kb_to_cnf

directory_path = "data"
files = process_directory(directory_path) # Alle Dateien im Verzeichnis und dessen Unterordner

for filename, filepath in files.items():
    start_time = time.perf_counter()

    # Umwandlung in CNF
    knowledgebase_cnf = parse_kb_to_cnf(filepath)

    parse_time = time.perf_counter()

    # Generiere hard und soft Clauses
    hard_clauses, soft_clauses = generate_dynamic_clauses(knowledgebase_cnf)

    # Lösen mit MaxSAT
    model, weight = solve_maxsat(knowledgebase_cnf, solver_name="Minisat22", hard_clauses=hard_clauses, soft_clauses=soft_clauses)

    end_time = time.perf_counter()
    elapsed_time = (end_time - start_time) * 1000
    elapsed_parse_time = (parse_time - start_time) * 1000

    if model:
        print(f"knowledgebase: {knowledgebase_cnf}, model: {model}, Ifc: {weight} (time: {elapsed_time:.2f} ms), (parse_time: {elapsed_parse_time:.2f} ms)")
    else:
        print(f"No solution found. (time: {elapsed_time:.2f} ms)")
