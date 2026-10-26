# Signet

**Signet 26** is a lightweight programming language for building systems of signals: programs written in any language, called Modules, that pass results to one another as Signals. The user writes a few lines of Signet to wire modules together, and Signet checks it, passes inputs to each module, and exports results.

Signet was initially developed for **_Starfire_**, a test engineering design suite built around Test Cards comprising Test Points, where each Test Point can run a Module. For example, a vibration test produces an acceleration record; an analysis module finds its modes; a third module compares them against a requirement. Signet is the wiring between them. It also runs on its own, in any folder of modules.

**Who it is for.** Engineers who write modules in Python, Julia, C++, Rust, Ada, Fortran, shell or Signet itself (all with built-in support), or any other programming language, and want to connect them, either to use with Starfire, another environment, or independently. 

**Conventions.** Signet code and file names are in `code`. Output appears after a `→`. *Signal* with a capital S means a `.sig` file: one named result of one module run.

## Terminology

| Term | What it is |
|:--|:--|
| **Signal** | A `.sig` file: one named result of one module run, stamped with where, when and by which run it was made. |
| **Signet** | This language, and `signet.py`, the one file that reads it. A `.signet` file is Signet code saved on its own. |
| **Module** | Any program that reads its inputs and writes its outputs as Signals: Python, Julia, C++, Rust, Ada, Fortran, a shell script, or anything that reads and writes files. |
| **Stamp** | The record of origin and the hash that Signet adds to a Signal after a clean run. An edited Signal no longer matches its stamp. |
| **Parameter** | An external value, `$name`, given on the command line or in a test point's Parameters table. |
| **Series** | Values against an axis, such as amplitude against frequency, real or complex. It travels as one Signal. |
| **Sequence** | Signet code that runs test points itself, in order, waiting for conditions between them. |
| **Starfire** | The test-campaign tool Signet grew out of. Its test points each hold a Signals box; a Signal ticked **live** can be used by other points. |
| **System** | A set of modules joined by Signals: each module's outputs are wired to other modules' inputs, and Signet runs them and keeps the record. |

## Getting started

Signet is one file: `signet.py`, or an executable binary. Put it in a folder with the files below and run it:

```
python3 signet.py hello.signet        # or: ./signet hello.signet
```

### Hello, Signal

Every language starts by saying hello. Signet says it with a Signal. `hello.signet` makes a value, uses `connect` to send it as a Signal to the input of a module called `message`, and uses `run` to start that module. The module answers back as a Signal, and `echo` shows it.

`hello.signet`:

```
let hello = 'Hello, world!'
connect(hello, message.input)
run(message)
echo(message.output.sig)
```

`message` is the module it runs. Signet looks for `message.py`, `message.jl`, `message.signet`, or any other module file in the folder, so write it in whichever language you like. Each version reads the input and writes it back as the output `output`.

`message.py`, in Python:

```python
from signet import signals

print(signals.input)
signals.output = signals.input    # written as message.output.sig
```

`message.jl`, in Julia (needs the `JSON3` package):

```julia
using Signet: signals

println(signals.input)
signals.output = signals.input    # written as message.output.sig
```

`message.signet`, in Signet itself. The module's inputs are variables, and `output` writes a Signal:

```
echo(input)
output(output, input)
```

Keep one of the three: Signet runs whichever `message` file is in the folder, and stops if there is more than one. Run it:

```
python3 signet.py hello.signet
```

```
→ Hello, world!
→ line 4: message.output.sig = "Hello, world!"
```

The first line is the module's own `print` (in the Signet version it is the module's `echo`, `line 1: input = "Hello, world!"`); the second is `hello.signet`'s `echo`, with the line it is on and what the Signal holds.

### Signet on its own

A module is only needed when something has to be worked out outside Signet. For this message nothing does, so Signet can say it by itself. `echo` prints what you wrote and what it worked out to, and no module is involved:

`hello_only.signet`:

```
let hello = 'Hello, world!'
echo(hello)
```

```
→ line 2: hello = "Hello, world!"
```

### The Signal between them

A Signal on disk is plain JSON. After the run above, `message.output.sig` holds:

```json
{"value": "Hello, world!", "type": "text", "origin": "hello:message.output", "generated": "2026-10-25T14:13:55Z", "hash": "392f4b2c7625a5e1295013976405d414e94419ac578a1885ae3c175d941846a5"}
```

The module wrote only the `value`; Signet added the type, where it came from, when, and a hash of the rest after the module finished cleanly. If anyone edits the file, the hash stops matching and the Signal is refused. That is what makes a Signal trustworthy evidence rather than just a number in a file.

The module's input travelled the other way. `connect` wrote it to `message.inputs.json` (and a plain-text copy, `message.inputs.txt`, for languages without a JSON library), and the helper read it back as `signals.input`.

### Checking without running

`--check` reads the whole file and reports every line it can't understand, without running anything:

```
python3 signet.py hello.signet --check
```

```
→ hello.signet: ok
```

### Two places Signet runs

* **On its own,** as above: `python3 signet.py <file>.signet` runs in the current folder, and the modules it starts are files in that folder.
* **In Starfire,** in the Signals box of a test point. The code runs each time you press run on that point, just before the module starts, and `echo` lines appear at the top of the module's output.

The language is the same in both. Test points exist only in Starfire, and `run(module)` is for the standalone runner.

Exit codes: `0` the file ran to the end, `1` an error, `2` a `break`.

## More

The full manual (types, vectors and complex numbers, routing, conditionals, functions, sequences, loops, and writing modules in every supported language) is `Signet_Programming_Language.pdf`.
