# Signet

**Signet 26** (26.b.0.1.6) is a lightweight coordination language for building systems of programs written in any language. The programs, called **modules**, pass results to one another as **Signals**. Signet is the wiring between them: a typed directed multigraph where modules are nodes and Signals are arrows.

Signet was first developed for [Starfire](https://github.com/ddesai76/starfire), a test design suite where each test point can run a module. It also runs on its own, as wiring code in any folder of modules.

This repository goes with the book *The Signet Programming Language* (Daniel Desai, 2026). The book is the full guide; this README covers getting started.

## Contents

| File | What it is |
|---|---|
| `signet.py` | The reference implementation: the evaluator, CLI and embedded module helpers |
| `build.sh` | Builds the standalone `signet` binary from `signet.py` |
| `signet.rs` | The Rust module helper, as written by `--export-helpers` |
| `visualizer.py` | Draws a system as SVG, in the style of Starfire's System view |
| `sys2dot.py` | Turns `--connections` JSON into a Graphviz graph |

## Install

`signet.py` needs only Python 3 and its standard library. Put `signet.py`, or the `signet` binary, in the working folder:

```sh
python3 signet.py hello.sg     # from source
./signet hello.sg              # standalone binary
```

To build the binary, run `./build.sh`.

## Hello, Signal

`hello.sg`:

```
echo('Hello, world!')
```

```
$ ./signet hello.sg
→ line 1: 'Hello, world!' = "Hello, world!"
```

That is a statement, not yet a Signal. To send one, make `hello.sg` a module with an output port, write a module that receives it, and wire the two together:

`hello.sg`
```
# signet: out text::message
let hello = 'Hello, world!'
output(text::message, hello)
```

`world.cpp`
```cpp
// signet: in text::input
#include <signet.hpp>
#include <iostream>
int main() {
    auto m = signet::in<std::string>("input");
    std::cout << m << '\n';
    return 0;
}
```

`messenger.sg`
```
run(hello)
connect(hello.message!, world.input)
run(world)
```

```
$ ./signet messenger.sg
→ Hello, world!
```

`connect` is an arrow from one module's output port to another module's input port. Within a single pass the graph is acyclic, because a module can only read a Signal that already exists. Feedback loops are written as passes, each reading what the one before it wrote.

## Signals

A Signal is a `.sig` file: one named result of one module run, written as JSON. In code, `!` is shorthand for `.sig`, so `messenger.output!` means `messenger.output.sig`.

```json
{"value": "Hello, world!", "type": "text", "origin": "hello.hello",
 "generated": "2026-10-23T17:08:22Z", "hash": "5daa9ee1…"}
```

When a module's run ends cleanly, Signet **stamps** each Signal it wrote. A stamp records the hash of every input value and where it came from: a Signal by its stamp, a file by its SHA-256, a parameter by its value. It also records the module file. If anyone edits the Signal afterwards, it no longer matches its stamp.

## The language at a glance

Signet borrows from Python, Julia, MATLAB, BASIC, Fortran 90, Rust, Haskell, C++ and the Unix shell. Typing is strong and dynamic, with optional `type::` annotations. Indexing is zero-based by default; `index(1)` changes that. Slices include both ends, and `last` names the last element.

Signet is deliberately **not Turing-complete**. Each loop is capped at 100,000 iterations, there is no unbounded `while`, and functions can't recurse, so every script terminates. Anything that needs more belongs in a module.

```
# Comments start with #
let mass = $mass                      # A parameter, from --param mass=…
where gravity = 9.81                  # A constant
let weight = mass * gravity           # A variable
echo(weight)

for k = 0:2                           # Loops are bounded
  if k == 1 then
    echo(k)
  end if
next k

f(x) = x**2 + 1                       # Short form of function … end function
let v = map(f, [1, 2, 3])

connect(v, plot.y)                    # Give a module's input a value
run(plot)
lineage(plot.figure!)                 # Print the chain that made a Signal
```

**Types:** `int`, `float`, `real`, `num`, `bool`, `hex`, `bits::<n>`, `text`, `complex`, `vector::<type>`, `tuple`, `range`, `series::<domain>::<float|complex>`, `stream::<domain>::<float|complex>`, `bus`, or a file extension such as `csv`.

**Routing:** `route(v, exit, [a, b])` fans a value out to several inputs, and `route(s, merge, [t, u])` appends Signals. Optional case markers state a value's role: `ex` (`.sta`), `ab` (`.lta`) and `ad` (`.lle`).

**Waiting:** `when c within s by s … end when` waits for a condition, with deadlines. Streams (timestamped samples that arrive while their source is running) are read with `sample(s)`, `$sample(s)`, `@sample(s)` and `freeze(s)`.

Appendix A of the book has the full quick reference: 120 reserved words, the operators in order of precedence, and the built-in functions.

## Modules

A module is any program that reads its inputs and writes its outputs as Signals. A module declares its ports in a comment, using its own language's comment marker (`#`, `//`, `--` or `!`):

```python
# signet: in float::volts, in float::amps, out float::watts
from signet import signals
signals.watts = signals.volts * signals.amps   # Writes multiply.watts.sig
```

`run(multiply)` finds `multiply.<ext>` in the working folder. There can be only one module per name: if `multiply.py` and `multiply.sg` are both present, Signet reports `multiply matches multiply.py, multiply.sg`.

| Language | Extension | How it runs |
|---|---|---|
| Signet | `.sg` | Natively |
| Python | `.py` | Interpreted (`from signet import signals`) |
| Julia | `.jl` | Interpreted (`using Signet: signals`; needs JSON3) |
| ALGOL 68 | `.a68` | Interpreted |
| C, C++ | `.c`, `.cpp` | Compiled by Signet (C11, C++17) |
| Rust | `.rs` | Compiled by Signet with `rustc` (no Cargo) |
| Ada | `.adb` | Compiled by Signet with `gnatmake` |
| Fortran | `.f90` | Compiled by Signet with `gfortran` |

Signet compiles a module the first time it runs, and again only when its source or Signet changes. On Debian or Ubuntu, install the compilers with:

```sh
sudo apt install gcc g++ gnat gfortran rustc
```

### Helpers

The helper files are embedded in Signet. To write them out, run:

```sh
./signet --export-helpers include
```

| Language | File | Use |
|---|---|---|
| Ada | `signet.ads`, `signet.adb` | `with Signet;` |
| C | `signet.h` | `#include <signet.h>` |
| C++ | `signet.hpp` | `#include <signet.hpp>` |
| Fortran | `signet.f90` | `use signet` |
| Rust | `signet.rs` | `use signet::get_f64;` |

The helpers only change when Signet does, so export them again after updating. To compile a module yourself and check it for errors before wiring it in:

```sh
gcc -O2 -std=c11 -I include module.c -o module -lm
g++ -O2 -std=c++17 -I include module.cpp -o module

# Rust: build the library once, then each module
rustc --edition 2021 -O --crate-type rlib --crate-name signet include/signet.rs -o include/libsignet.rlib
rustc --edition 2021 -O --extern signet=include/libsignet.rlib module.rs -o module

# Fortran: compile the helper once, then link each module
gfortran -O2 -c -J include include/signet.f90 -o include/signet.o
gfortran -O2 -I include module.f90 include/signet.o -o module

# Ada
mkdir -p obj && gnatmake -q -O2 -gnat2012 -Iinclude -D obj module.adb -o module
```

Streams default to a window of 1024 samples. For example, in Python:

```python
v = signals.stream("volts", domain="time", window=1024)
v.write(t, x)
```

## Command line

```
signet [file] [--param NAME=VALUE] [--check] [--lineage SIG]
       [--export-helpers DIR] [--connections] [--version]
```

| Flag | Does |
|---|---|
| `--param NAME=VALUE` | Sets `$NAME` (repeatable) |
| `--check` | Reads the file and reports every suspect line, without running it |
| `--lineage SIG` | Prints the chain that made a Signal in this folder (`name.sig` or `name!`) |
| `--export-helpers DIR` | Writes the module helpers into `DIR` |
| `--connections` | Prints the file's `connect()`s as JSON, without running it |
| `--version` | Prints the version |

**Exit codes:** `0` means the file ran to the end, `1` means an error (the message names the line), and `2` means the code reached `break`.

Both `.sg` and the older `.signet` extension are accepted.

### Lineage

```
$ ./signet --lineage performance_test.report!
performance_test.report! = true  bool  made by chamber:performance_test.report at …, stamp ok
  module performance_test.rs (unchanged)
  temperature <-
    tvac.temperature! = {…}  stream::time::float  made by chamber:tvac.temperature at …, stamp ok
      module tvac.rs (unchanged)
      setpoint <- written in the code
```

Problems are reported in the chain as `edited after it was stamped`, `replaced by a later run`, `missing`, `module … (changed since)` or `file … (changed since)`.

## Visualizing a system

Run either tool in the system's working folder:

```sh
python3 visualizer.py wiring.sg -o diagram.svg --theme light --large --label car=10:speed
./signet wiring.sg --connections | python3 sys2dot.py | dot -Tsvg -o system.svg
```

`visualizer.py` uses only the standard library. It uses `signet.py` from its own folder if present, or else the `signet` binary. A line is solid where its source Signal exists and faint where there is no data yet. `sys2dot.py` needs Graphviz (`sudo apt install graphviz`). In both, stepped feedback lines are dashed.

## Starfire

In Starfire, Signet code goes in each test point's **Signals** box, and a point's Signal is written `10:module.port!`. If `signet.py` is next to `starfire.py`, Starfire imports it. See the [Starfire README](https://github.com/ddesai76/starfire).

## License

MIT. The software is provided "as is", without warranty of any kind. See `LICENSE`.

Developed with AI assistance (Claude, Anthropic); all technical claims and results were reviewed and verified by the author.
