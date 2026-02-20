<!-- cspell:disable -->
<!-- auto-generated; DO NOT EDIT! see base.GenerateTyperHelpMarkdown() -->

# `realtime-api` Command-Line Interface

```text
Usage: realtime-api [OPTIONS] COMMAND [ARGS]...                                                                                                           
                                                                                                                                                           
 realtime-api: Launch the TFINTA Realtime API server.                                                                                                      
                                                                                                                                                           
╭─ Options ───────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╮
│ --version                                                        Show version and exit.                                                                 │
│ --verbose             -v                INTEGER RANGE [0<=x<=3]  Verbosity (nothing=ERROR, -v=WARNING, -vv=INFO, -vvv=DEBUG).               │
│ --color                   --no-color                             Force enable/disable colored output (respects NO_COLOR env var if not provided).       │
│                                                                  Defaults to having colors.                                                             │
│ --install-completion                                             Install completion for the current shell.                                              │
│ --show-completion                                                Show completion for the current shell, to copy it or customize the installation.       │
│ --help                                                           Show this message and exit.                                                            │
╰─────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╯
╭─ Commands ──────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╮
│ run       Run the TFINTA Realtime API server.                                                                                                           │
│ markdown  Emit Markdown docs for the CLI (see README.md section "Creating a New Version").                                                              │
╰─────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╯
                                                                                                                                                           
 Example:                                                                                                                                                  
                                                                                                                                                           
 # --- Run API ---                                                                                                                                         
 poetry run realtime-api run  # starts on 0.0.0.0:8080 poetry run realtime-api run --port 9000                                                             
                                                                                                                                                           
 # --- Generate documentation ---                                                                                                                          
 poetry run realtime-api markdown > realtime-api.md
```

## `realtime-api markdown` Command

```text
Usage: realtime-api markdown [OPTIONS]                                                                                                                    
                                                                                                                                                           
 Emit Markdown docs for the CLI (see README.md section "Creating a New Version").                                                                          
                                                                                                                                                           
╭─ Options ───────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╮
│ --help          Show this message and exit.                                                                                                             │
╰─────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╯
                                                                                                                                                           
 Example:                                                                                                                                                  
                                                                                                                                                           
 $ poetry run realtime-api markdown > realtime-api.md                                                                                                      
 <<saves CLI doc>>
```

## `realtime-api run` Command

```text
Usage: realtime-api run [OPTIONS]                                                                                                                         
                                                                                                                                                           
 Run the TFINTA Realtime API server.                                                                                                                       
                                                                                                                                                           
╭─ Options ───────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╮
│ --host    -h                 TEXT     Bind address, default "0.0.0.0"                                                                 │
│ --port    -p                 INTEGER  Port, default 8080                                                                                 │
│ --reload      --no-reload             Development auto-reload? (default: False)                                                     │
│ --help                                Show this message and exit.                                                                                       │
╰─────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╯
                                                                                                                                                           
 Example:                                                                                                                                                  
                                                                                                                                                           
 $ poetry run realtime-api run                                                                                                                             
 <<starts the API server>>
```
