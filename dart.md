<!-- cspell:disable -->
<!-- auto-generated; DO NOT EDIT! see base.GenerateTyperHelpMarkdown() -->

# `dart` Command-Line Interface

```text
Usage: dart [OPTIONS] COMMAND [ARGS]...                                                                                                                   
                                                                                                                                                           
 dart: CLI for Dublin DART rail services.                                                                                                                  
                                                                                                                                                           
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
│ read      Read DB from official sources                                                                                                                 │
│ markdown  Emit Markdown docs for the CLI (see README.md section "Creating a New Version").                                                              │
│ print     Print DB                                                                                                                                      │
╰─────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╯
                                                                                                                                                           
 Example:                                                                                                                                                  
                                                                                                                                                           
 # --- Read DART data ---                                                                                                                                  
 poetry run dart read                                                                                                                                      
                                                                                                                                                           
 # --- Print schedules ---                                                                                                                                 
 poetry run dart print trips 20260201                                                                                                                      
 poetry run dart print station Tara 20260201                                                                                                               
 poetry run dart print trip E108                                                                                                                           
                                                                                                                                                           
 # --- Generate documentation ---                                                                                                                          
 poetry run dart markdown > dart.md
```

## `dart markdown` Command

```text
Usage: dart markdown [OPTIONS]                                                                                                                            
                                                                                                                                                           
 Emit Markdown docs for the CLI (see README.md section "Creating a New Version").                                                                          
                                                                                                                                                           
╭─ Options ───────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╮
│ --help          Show this message and exit.                                                                                                             │
╰─────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╯
                                                                                                                                                           
 Example:                                                                                                                                                  
                                                                                                                                                           
 $ poetry run dart markdown > dart.md                                                                                                                      
 <<saves CLI doc>>
```

## `dart print` Command

```text
Usage: dart print [OPTIONS] COMMAND [ARGS]...                                                                                                             
                                                                                                                                                           
 Print DB                                                                                                                                                  
                                                                                                                                                           
╭─ Options ───────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╮
│ --help          Show this message and exit.                                                                                                             │
╰─────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╯
╭─ Commands ──────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╮
│ all        Print all database information.                                                                                                              │
│ calendars  Print Calendars/Services.                                                                                                                    │
│ stops      Print Stops.                                                                                                                                 │
│ trips      Print Trips.                                                                                                                                 │
│ station    Print Station Chart.                                                                                                                         │
│ trip       Print DART Trip.                                                                                                                             │
╰─────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╯
```

### `dart print all` Sub-Command

```text
Usage: dart print all [OPTIONS]                                                                                                                           
                                                                                                                                                           
 Print all database information.                                                                                                                           
                                                                                                                                                           
╭─ Options ───────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╮
│ --help          Show this message and exit.                                                                                                             │
╰─────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╯
                                                                                                                                                           
 Example:                                                                                                                                                  
                                                                                                                                                           
 $ poetry run dart print all                                                                                                                               
 <<prints all DART data>>
```

### `dart print calendars` Sub-Command

```text
Usage: dart print calendars [OPTIONS]                                                                                                                     
                                                                                                                                                           
 Print Calendars/Services.                                                                                                                                 
                                                                                                                                                           
╭─ Options ───────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╮
│ --help          Show this message and exit.                                                                                                             │
╰─────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╯
                                                                                                                                                           
 Example:                                                                                                                                                  
                                                                                                                                                           
 $ poetry run dart print calendars                                                                                                                         
 <<prints DART service calendars>>
```

### `dart print station` Sub-Command

```text
Usage: dart print station [OPTIONS] STATION [DAY]                                                                                                         
                                                                                                                                                           
 Print Station Chart.                                                                                                                                      
                                                                                                                                                           
╭─ Arguments ─────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╮
│ *    station      TEXT   Station to print chart for; finds by ID (stops.txt/stop_id) or by name (stop_name)                                   │
│      day          [DAY]  Day to consider in "YYYYMMDD" format (default: TODAY/NOW).                                                  │
╰─────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╯
╭─ Options ───────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╮
│ --help          Show this message and exit.                                                                                                             │
╰─────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╯
                                                                                                                                                           
 Example:                                                                                                                                                  
                                                                                                                                                           
 $ poetry run dart print station Tara 20260201                                                                                                             
 <<prints Tara Street station schedule>>
```

### `dart print stops` Sub-Command

```text
Usage: dart print stops [OPTIONS]                                                                                                                         
                                                                                                                                                           
 Print Stops.                                                                                                                                              
                                                                                                                                                           
╭─ Options ───────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╮
│ --help          Show this message and exit.                                                                                                             │
╰─────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╯
                                                                                                                                                           
 Example:                                                                                                                                                  
                                                                                                                                                           
 $ poetry run dart print stops                                                                                                                             
 <<prints all DART stations>>
```

### `dart print trip` Sub-Command

```text
Usage: dart print trip [OPTIONS] TRAIN                                                                                                                    
                                                                                                                                                           
 Print DART Trip.                                                                                                                                          
                                                                                                                                                           
╭─ Arguments ─────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╮
│ *    train      TEXT  DART train code, like "E108" for example                                                                                │
╰─────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╯
╭─ Options ───────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╮
│ --help          Show this message and exit.                                                                                                             │
╰─────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╯
                                                                                                                                                           
 Example:                                                                                                                                                  
                                                                                                                                                           
 $ poetry run dart print trip E108                                                                                                                         
 <<prints details for train E108>>
```

### `dart print trips` Sub-Command

```text
Usage: dart print trips [OPTIONS] [DAY]                                                                                                                   
                                                                                                                                                           
 Print Trips.                                                                                                                                              
                                                                                                                                                           
╭─ Arguments ─────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╮
│   day      [DAY]  Day to consider in "YYYYMMDD" format (default: TODAY/NOW).                                                         │
╰─────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╯
╭─ Options ───────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╮
│ --help          Show this message and exit.                                                                                                             │
╰─────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╯
                                                                                                                                                           
 Example:                                                                                                                                                  
                                                                                                                                                           
 $ poetry run dart print trips 20260201                                                                                                                    
 <<prints all trips for 2026-02-01>>
```

## `dart read` Command

```text
Usage: dart read [OPTIONS]                                                                                                                                
                                                                                                                                                           
 Read DB from official sources                                                                                                                             
                                                                                                                                                           
╭─ Options ───────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╮
│ --freshness  -f                  INTEGER RANGE   Number of days to cache; 0 == always load                                           │
│ --replace        --no-replace                          Force replace DB version. Defaults to not loading the same version again.   │
│ --help                                                 Show this message and exit.                                                                      │
╰─────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╯
                                                                                                                                                           
 Example:                                                                                                                                                  
                                                                                                                                                           
 $ poetry run dart read                                                                                                                                    
 <<loads latest DART data>>
```
