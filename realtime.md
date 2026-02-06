<!-- cspell:disable -->
<!-- auto-generated; DO NOT EDIT! see base.GenerateTyperHelpMarkdown() -->

# `realtime` Command-Line Interface

```text
Usage: realtime [OPTIONS] COMMAND [ARGS]...                                                                                                               
                                                                                                                                                           
 realtime: CLI for Irish Rail Realtime services.                                                                                                           
                                                                                                                                                           
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
│ markdown  Emit Markdown docs for the CLI (see README.md section "Creating a New Version").                                                              │
│ print     Print Realtime Data                                                                                                                           │
╰─────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╯
                                                                                                                                                           
 Example:                                                                                                                                                  
                                                                                                                                                           
 # --- Print realtime data ---                                                                                                                             
 poetry run realtime print stations                                                                                                                        
 poetry run realtime print running                                                                                                                         
 poetry run realtime print station LURGN                                                                                                                   
 poetry run realtime print train E108 20260201                                                                                                             
                                                                                                                                                           
 # --- Generate documentation ---                                                                                                                          
 poetry run realtime markdown > realtime.md
```

## `realtime markdown` Command

```text
Usage: realtime markdown [OPTIONS]                                                                                                                        
                                                                                                                                                           
 Emit Markdown docs for the CLI (see README.md section "Creating a New Version").                                                                          
                                                                                                                                                           
╭─ Options ───────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╮
│ --help          Show this message and exit.                                                                                                             │
╰─────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╯
                                                                                                                                                           
 Example:                                                                                                                                                  
                                                                                                                                                           
 $ poetry run realtime markdown > realtime.md                                                                                                              
 <<saves CLI doc>>
```

## `realtime print` Command

```text
Usage: realtime print [OPTIONS] COMMAND [ARGS]...                                                                                                         
                                                                                                                                                           
 Print Realtime Data                                                                                                                                       
                                                                                                                                                           
╭─ Options ───────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╮
│ --help          Show this message and exit.                                                                                                             │
╰─────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╯
╭─ Commands ──────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╮
│ stations  Print All System Stations.                                                                                                                    │
│ running   Print Running Trains.                                                                                                                         │
│ station   Print Station Board.                                                                                                                          │
│ train     Print Train Movements.                                                                                                                        │
╰─────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╯
```

### `realtime print running` Sub-Command

```text
Usage: realtime print running [OPTIONS]                                                                                                                   
                                                                                                                                                           
 Print Running Trains.                                                                                                                                     
                                                                                                                                                           
╭─ Options ───────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╮
│ --help          Show this message and exit.                                                                                                             │
╰─────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╯
                                                                                                                                                           
 Example:                                                                                                                                                  
                                                                                                                                                           
 $ poetry run realtime print running                                                                                                                       
 <<prints all running trains>>
```

### `realtime print station` Sub-Command

```text
Usage: realtime print station [OPTIONS] CODE                                                                                                              
                                                                                                                                                           
 Print Station Board.                                                                                                                                      
                                                                                                                                                           
╭─ Arguments ─────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╮
│ *    code      TEXT  Either a 5-letter station code (ex: "LURGN") or a search string that can be identified as a station (ex: "lurgan")       │
╰─────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╯
╭─ Options ───────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╮
│ --help          Show this message and exit.                                                                                                             │
╰─────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╯
                                                                                                                                                           
 Example:                                                                                                                                                  
                                                                                                                                                           
 $ poetry run realtime print station LURGN                                                                                                                 
 <<prints Lurgan station board>>
```

### `realtime print stations` Sub-Command

```text
Usage: realtime print stations [OPTIONS]                                                                                                                  
                                                                                                                                                           
 Print All System Stations.                                                                                                                                
                                                                                                                                                           
╭─ Options ───────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╮
│ --help          Show this message and exit.                                                                                                             │
╰─────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╯
                                                                                                                                                           
 Example:                                                                                                                                                  
                                                                                                                                                           
 $ poetry run realtime print stations                                                                                                                      
 <<prints all stations>>
```

### `realtime print train` Sub-Command

```text
Usage: realtime print train [OPTIONS] CODE [DAY]                                                                                                          
                                                                                                                                                           
 Print Train Movements.                                                                                                                                    
                                                                                                                                                           
╭─ Arguments ─────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╮
│ *    code      TEXT   Train code (ex: "E108")                                                                                                 │
│      day       [DAY]  Day to consider in "YYYYMMDD" format (default: TODAY/NOW).                                                     │
╰─────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╯
╭─ Options ───────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╮
│ --help          Show this message and exit.                                                                                                             │
╰─────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╯
                                                                                                                                                           
 Example:                                                                                                                                                  
                                                                                                                                                           
 $ poetry run realtime print train E108 20260201                                                                                                           
 <<prints train E108 movements>>
```
