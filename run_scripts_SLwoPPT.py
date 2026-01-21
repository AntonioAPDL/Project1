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
    subprocess.run(['tmux', 'send-keys', '-t', session_name, command, 'C-m'])

if __name__ == "__main__":
    script_path = "/home/jaguir26/project1_ucsc_phd/OptimalModelSLwoPPPexAL.r"
    param_list = [0.05, 0.2, 0.35, 0.5, 0.65, 0.8, 0.95]

    for param in param_list:
        session_name = f"session_SL_woppt_{int(param * 100):02d}"
        # session_name = f"session_SL_{int(param * 100):02d}"
        run_in_tmux(session_name, script_path, param)
