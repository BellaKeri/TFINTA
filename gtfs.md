<!-- cspell:disable -->
<!-- auto-generated; DO NOT EDIT! see base.GenerateTyperHelpMarkdown() -->

# `gtfs` Command-Line Interface

```text
Usage: gtfs [OPTIONS] COMMAND [ARGS]...                                                                                                                   
                                                                                                                                                           
 gtfs: CLI for GTFS (General Transit Feed Specification) data.                                                                                             
                                                                                                                                                           
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
                                                                                                                                                           
 # --- Read GTFS data ---                                                                                                                                  
 poetry run gtfs read                                                                                                                                      
                                                                                                                                                           
 # --- Print data ---                                                                                                                                      
 poetry run gtfs print basics                                                                                                                              
 poetry run gtfs print trip 8001_17410                                                                                                                     
                                                                                                                                                           
 # --- Generate documentation ---                                                                                                                          
 poetry run gtfs markdown > gtfs.md
```

## `gtfs markdown` Command

```text
Usage: gtfs markdown [OPTIONS]                                                                                                                            
                                                                                                                                                           
 Emit Markdown docs for the CLI (see README.md section "Creating a New Version").                                                                          
                                                                                                                                                           
╭─ Options ───────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╮
│ --help          Show this message and exit.                                                                                                             │
╰─────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╯
                                                                                                                                                           
 Example:                                                                                                                                                  
                                                                                                                                                           
 $ poetry run gtfs markdown > gtfs.md                                                                                                                      
 <<saves CLI doc>>
```

## `gtfs print` Command

```text
Usage: gtfs print [OPTIONS] COMMAND [ARGS]...                                                                                                             
                                                                                                                                                           
 Print DB                                                                                                                                                  
                                                                                                                                                           
╭─ Options ───────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╮
│ --help          Show this message and exit.                                                                                                             │
╰─────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╯
╭─ Commands ──────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╮
│ all        Print all database information.                                                                                                              │
│ basics     Print Basic Data.                                                                                                                            │
│ calendars  Print Calendars/Services.                                                                                                                    │
│ stops      Print Stops.                                                                                                                                 │
│ shape      Print Shape.                                                                                                                                 │
│ trip       Print GTFS Trip.                                                                                                                             │
╰─────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╯
```

### `gtfs print all` Sub-Command

```text
Usage: gtfs print all [OPTIONS]                                                                                                                           
                                                                                                                                                           
 Print all database information.                                                                                                                           
                                                                                                                                                           
╭─ Options ───────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╮
│ --help          Show this message and exit.                                                                                                             │
╰─────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╯
                                                                                                                                                           
 Example:                                                                                                                                                  
                                                                                                                                                           
 $ poetry run gtfs print all                                                                                                                               
 <<prints all GTFS data>>
```

### `gtfs print basics` Sub-Command

```text
Usage: gtfs print basics [OPTIONS]                                                                                                                        
                                                                                                                                                           
 Print Basic Data.                                                                                                                                         
                                                                                                                                                           
╭─ Options ───────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╮
│ --help          Show this message and exit.                                                                                                             │
╰─────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╯
                                                                                                                                                           
 Example:                                                                                                                                                  
                                                                                                                                                           
 $ poetry run gtfs print basics                                                                                                                            
 <<prints basic GTFS data>>
```

### `gtfs print calendars` Sub-Command

```text
Usage: gtfs print calendars [OPTIONS]                                                                                                                     
                                                                                                                                                           
 Print Calendars/Services.                                                                                                                                 
                                                                                                                                                           
╭─ Options ───────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╮
│ --help          Show this message and exit.                                                                                                             │
╰─────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╯
                                                                                                                                                           
 Example:                                                                                                                                                  
                                                                                                                                                           
 $ poetry run gtfs print calendars                                                                                                                         
 <<prints GTFS service calendars>>
```

### `gtfs print shape` Sub-Command

```text
Usage: gtfs print shape [OPTIONS] SHAPE_ID                                                                                                                
                                                                                                                                                           
 Print Shape.                                                                                                                                              
                                                                                                                                                           
╭─ Arguments ─────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╮
│ *    shape_id      TEXT  Shape ID to print                                                                                                    │
╰─────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╯
╭─ Options ───────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╮
│ --help          Show this message and exit.                                                                                                             │
╰─────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╯
                                                                                                                                                           
 Example:                                                                                                                                                  
                                                                                                                                                           
 $ poetry run gtfs print shape 38002                                                                                                                       
 <<prints details for shape 38002>>
```

### `gtfs print stops` Sub-Command

```text
Usage: gtfs print stops [OPTIONS]                                                                                                                         
                                                                                                                                                           
 Print Stops.                                                                                                                                              
                                                                                                                                                           
╭─ Options ───────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╮
│ --help          Show this message and exit.                                                                                                             │
╰─────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╯
                                                                                                                                                           
 Example:                                                                                                                                                  
                                                                                                                                                           
 $ poetry run gtfs print stops                                                                                                                             
 <<prints all GTFS stops>>
```

### `gtfs print trip` Sub-Command

```text
Usage: gtfs print trip [OPTIONS] TRIP_ID                                                                                                                  
                                                                                                                                                           
 Print GTFS Trip.                                                                                                                                          
                                                                                                                                                           
╭─ Arguments ─────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╮
│ *    trip_id      TEXT  Trip ID to print                                                                                                      │
╰─────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╯
╭─ Options ───────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╮
│ --help          Show this message and exit.                                                                                                             │
╰─────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╯
                                                                                                                                                           
 Example:                                                                                                                                                  
                                                                                                                                                           
 $ poetry run gtfs print trip 8001_17410                                                                                                                   
 <<prints details for trip 8001_17410>>
```

## `gtfs read` Command

```text
Usage: gtfs read [OPTIONS]                                                                                                                                
                                                                                                                                                           
 Read DB from official sources                                                                                                                             
                                                                                                                                                           
╭─ Options ───────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╮
│ --freshness            -f                              INTEGER RANGE   Number of days to cache; 0 == always load                     │
│ --allow-unknown-file       --no-allow-unknown-file                           Allow unknown files in GTFS ZIP. Defaults to allowing unknown files.       │
│                                                                                                                            │
│ --allow-unknown-field      --no-allow-unknown-field                          Allow unknown fields in GTFS files. Defaults to not allowing unknown       │
│                                                                              fields.                                                                    │
│                                                                                                                        │
│ --replace                  --no-replace                                      Force replace DB version. Defaults to not loading the same version again.  │
│                                                                                                                                    │
│ --override             -o                              TEXT                  Override ZIP file path (instead of downloading)                            │
│ --help                                                                       Show this message and exit.                                                │
╰─────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╯
                                                                                                                                                           
 Example:                                                                                                                                                  
                                                                                                                                                           
 $ poetry run gtfs read                                                                                                                                    
 <<loads latest GTFS data>>
```
