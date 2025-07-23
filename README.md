This project is based on the Master-Thesis 'Algorithmic Approaches for the Formula-Based Contension Inconsistency Measure' at the 'Fernuniversität in Hagen'.

# Formula-Based Contension Inconsistency Measure

To calculate the formula-based contension inconsistency measure ($I_{fc}$) we use the three-valued logic by Graham Priest where we can assign each Atom a third truth-value 'both'.
Ifc now calculates the minimum of formulas, where at least one atom got assigned the value 'both'. The agorithmic approaches, provided in this project, use Max SAT Solver and Answer Set Programming.

# Experiment Orchestration

The *main.py* script is the execution entry point and manages the entire experiment
lifecycle. The process is initiated within the if *__name__ == "__main__"* clause.
Initially, CSV log files are initialized with appropriate headers. Then, the *get_all_files()* function scans the data directory and compiles a list of all knowl-
edge bases to be processed. In the main loop, each file is read in, and for each knowledgebase, the three solving functions *asp_encode_and_solve()*, *maxsat_encode_and_solve()*, and *maxsat_tseitin_encode_and_solve()* are called.

To ensure the robustness of the experimental process, each solver call is wrapped by the *run_without_timeout function*. This function starts the solver in a separate process and enforces a hard time limit of 1000 seconds. 
If the solver fails or exceeds the time limit, the process is safely terminated and the error or timeout is logged without interrupting the overall experiment.
Result extraction is implemented in a solver-specific manner. 
The function *asp_encode_and_solve* uses the *on_model* callback function from the Clingo library. 
For each optimal model found, this callback extracts the cost and the atoms of the *val/2* and *f_inconsistent/1* predicates to reconstruct the solution details.

The MaxSAT functions use the RC2 solver from the PySAT library. 
After computing the result using *rc2.compute()*, the cost is directly read from the solver object. 
To retrieve solution details, the returned model is analyzed and integer variables are translated back into their boolean interpretations using a reverse_varmap. 
The violated soft clauses reveal the inconsistent formulas.
All collected data, including precise runtime measurements for encoding and solving, are written by write_result to two separate CSV files: *log_file_general.csv* for general results and *log_file_maxsat.csv* for additional MaxSAT-specific metrics such as the number of hard clauses.
