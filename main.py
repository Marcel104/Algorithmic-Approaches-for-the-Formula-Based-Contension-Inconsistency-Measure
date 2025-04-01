import time
import multiprocessing
import csv
import os
from src.solver_Max_SAT import solve_maxsat, generate_dynamic_clauses, get_both_atoms
from src.parser import parse_kb_to_cnf

directory_path = "data"
log_file = "log.csv"
TIMEOUT = 5

# CSV-Datei initialisieren (falls sie nicht existiert)
def initialize_csv():
    write_header = not os.path.exists(log_file)
    with open(log_file, mode="a", newline="") as file:
        writer = csv.writer(file)
        if write_header:
            writer.writerow(["filepath", "filename", "state", "runtime (ms)", "parse-time (ms)", "Ifc", "atoms_valued_both"])

# Funktion, um alle Dateien rekursiv zu finden
def get_all_files(directory):
    files = {}
    for root, _, filenames in os.walk(directory):
        for filename in filenames:
            files[os.path.join(root, filename)] = filename
    return files

# Diese Funktion wird in einem separaten Prozess ausgeführt
def process_file(filename, filepath, result_queue):
    start_time = time.perf_counter()

    try:
        # Umwandlung in CNF
        knowledgebase_cnf = parse_kb_to_cnf(filepath)

        parse_time = time.perf_counter()

        # Generiere hard und soft Clauses
        hard_clauses, soft_clauses, atom_mapping = generate_dynamic_clauses(knowledgebase_cnf)

        # Lösen mit MaxSAT
        model, weight = solve_maxsat(knowledgebase_cnf, solver_name="Minisat22", hard_clauses=hard_clauses, soft_clauses=soft_clauses)

        atoms_valued_both = get_both_atoms(model, atom_mapping)

        end_time = time.perf_counter()
        elapsed_time = (end_time - start_time) * 1000
        elapsed_parse_time = (parse_time - start_time) * 1000

        status = "solution found" if model else "no solution"
        result_queue.put((filepath, filename, status, f"{elapsed_time:.2f}", f"{elapsed_parse_time:.2f}", weight, atoms_valued_both))

    except Exception as e:
        result_queue.put((filepath, filename, f"Error: {str(e)}", "N/A", "N/A", "N/A", "N/A"))

if __name__ == '__main__':
    multiprocessing.freeze_support()
    initialize_csv()

    # Alle Dateien aus dem Verzeichnis und Unterordnern holen
    files = get_all_files(directory_path)

    # Durch alle Dateien iterieren
    for filepath, filename in files.items():
        result_queue = multiprocessing.Queue()
        process = multiprocessing.Process(target=process_file, args=(filename, filepath, result_queue))
        process.start()
        
        process.join(TIMEOUT)  # Warten auf Beendigung mit Timeout

        if process.is_alive():
            print(f"{filename}: Timeout after {TIMEOUT} seconds. Process cancelled.")
            process.terminate()  # Prozess beenden
            process.join()
            with open(log_file, mode="a", newline="") as file:
                writer = csv.writer(file)
                writer.writerow([filepath, filename, "timeout", "N/A", "N/A", "N/A", "N/A"])
        else:
            if not result_queue.empty():
                result = result_queue.get() 
                with open(log_file, mode="a", newline="") as file:
                    writer = csv.writer(file)
                    writer.writerow(result)
                print(f"{filepath}: {result[1]} {filename}: {result[2]} (time: {result[3]} ms, parse-time: {result[4]} ms), Ifc: {result[5]}, atoms_valued_both: {result[6]}")
