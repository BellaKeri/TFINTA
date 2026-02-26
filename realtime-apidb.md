<!-- cspell:disable -->
<!-- auto-generated; DO NOT EDIT! see base.GenerateTyperHelpMarkdown() -->

# `realtime-apidb` Command-Line Interface

```text
Usage: realtime-apidb [OPTIONS] COMMAND [ARGS]...                                                                                                         
                                                                                                                                                           
 realtime-apidb: Launch the TFINTA Realtime DB API server.                                                                                                 
                                                                                                                                                           
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
│ run       Run the TFINTA Realtime DB API server.                                                                                                        │
│ markdown  Emit Markdown docs for the CLI (see README.md section "Creating a New Version").                                                              │
╰─────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╯
                                                                                                                                                           
 Example:                                                                                                                                                  
                                                                                                                                                           
 # --- Run DB API ---                                                                                                                                      
 poetry run realtime-apidb run  # starts on 0.0.0.0:8081 poetry run realtime-apidb run --port 9000                                                         
                                                                                                                                                           
 # --- Generate documentation ---                                                                                                                          
 poetry run realtime-apidb markdown > realtime-apidb.md
```

## `realtime-apidb markdown` Command

```text
Usage: realtime-apidb markdown [OPTIONS]                                                                                                                  
                                                                                                                                                           
 Emit Markdown docs for the CLI (see README.md section "Creating a New Version").                                                                          
                                                                                                                                                           
╭─ Options ───────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╮
│ --help          Show this message and exit.                                                                                                             │
╰─────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╯
                                                                                                                                                           
 Example:                                                                                                                                                  
                                                                                                                                                           
 $ poetry run realtime-apidb markdown > realtime-apidb.md                                                                                                  
 <<saves CLI doc>>
```

## `realtime-apidb run` Command

```text
Usage: realtime-apidb run [OPTIONS]                                                                                                                       
                                                                                                                                                           
 Run the TFINTA Realtime DB API server.                                                                                                                    
                                                                                                                                                           
╭─ Options ───────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╮
│ --host    -h                 TEXT     Bind address, default "0.0.0.0"                                                                 │
│ --port    -p                 INTEGER  Port, default 8081                                                                                 │
│ --reload      --no-reload             Development auto-reload? (default: False)                                                     │
│ --help                                Show this message and exit.                                                                                       │
╰─────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╯
                                                                                                                                                           
 Example:                                                                                                                                                  
                                                                                                                                                           
 $ poetry run realtime-apidb run                                                                                                                           
 <<starts the DB API server>>
```
