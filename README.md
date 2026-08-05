# JIATRIX
Ai intergrated with Terminal.

## Install openai
## test the Ai with the terminal
## for bash or shell alias use this
    function jiatrix
        set env_path ~/.jiatrix/bin/activate.fish
        set script_path ~/.jiatrix/jiatrix.py

        # if activated
        if test -f $env_path
            source $env_path
        else
            echo "Activating script not found at $env_path"
            return 1
        end

        # check if Ai on
        if test -f $script_path
            python $script_path
        else
            echo "Script not found at $script_path"
            return 1
        end
    end