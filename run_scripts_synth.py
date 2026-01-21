import os
import subprocess

def run_in_tmux(session_name, script_path, param):
    # Check if the tmux session exists
    result = subprocess.run(['tmux', 'has-session', '-t', session_name], stderr=subprocess.PIPE)
    if result.returncode != 0:
        # Create a new tmux session
        subprocess.run(['tmux', 'new-session', '-d', '-s', session_name])
    
    # Run the R script in the tmux session
    command = f"Rscript {script_path} {param}"
    
    # Use stdout and stderr pipes, replace 'text=True' with 'universal_newlines=True'
    result = subprocess.run(['tmux', 'send-keys', '-t', session_name, command, 'C-m'], stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True)
    
    # Check for errors
    if result.returncode != 0:
        print(f"Error running command for session {session_name} with param {param}: {result.stderr}")

if __name__ == "__main__":
    script_path = "/data/muscat_data/jaguir26/project1_ucsc_phd/Optimal_Synth_Ranges.r"
    param_list = [0.05, 0.2, 0.35, 0.5, 0.65, 0.8, 0.95]

    for param in param_list:
        session_name = f"session_fit_synth_{int(param * 100):02d}"
        run_in_tmux(session_name, script_path, param)
