#!/bin/bash
for pid in $(tmux list-panes -a -F "#{pane_pid}"); do
    kill -SIGTERM $pid
done
echo "All tmux processes have been terminated."

