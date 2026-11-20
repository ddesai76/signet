#!/usr/bin/env python3

# regress.py:     SIGNET REGRESSION: THE BOOK'S EXAMPLES, END TO END
# AUTHOR:         DANIEL DESAI
# UPDATED:        2026-11-17
# VERSION:        0.1.5
#
# Runs the book's examples against a signet.py (and the tools beside it); blocks.json holds the book's code boxes.
# python3 regress.py <repo dir> [<signet binary>]   (binary given: every run uses it instead of signet.py)
import json, os, re, shutil, subprocess, sys, tempfile
if os.name == 'nt' and not sys.flags.utf8_mode:   # this harness reads and writes UTF-8; Signet runs with Windows' defaults
    sys.exit(subprocess.call([sys.executable, '-X', 'utf8'] + sys.argv))
REL = os.path.abspath(sys.argv[1]); SIG = REL + '/signet.py'
BIN = os.path.abspath(sys.argv[2]) if len(sys.argv) > 2 else None
HERE = os.path.dirname(os.path.abspath(__file__))
b = json.load(open(os.path.join(HERE, 'blocks.json')))
q = lambda t: t.replace('‘', "'").replace('’', "'")
results = []
def folder(*idx, extra=()):
    d = tempfile.mkdtemp(prefix='reg_'); shutil.copy(SIG, d)
    for i in idx: open(f"{d}/{b[i]['label']}", 'w').write(q(b[i]['text']) + '\n')
    for name, text in extra: open(f'{d}/{name}', 'w').write(text)
    return d
def sh(d, cmd, timeout=900, stdin=None):
    if BIN: cmd = cmd.replace('python3 signet.py', BIN)
    r = subprocess.run(cmd, cwd=d, shell=True, capture_output=True, text=True, timeout=timeout, input=stdin)
    return r.returncode, r.stdout, r.stderr
def check(name, cond, detail=''):
    results.append((name, bool(cond), detail)); print(('PASS ' if cond else 'FAIL ') + name + ('' if cond else f'\n     {detail[:600]}'))
def lines(s): return [l for l in s.splitlines() if l.strip() and not l.startswith('signet: building')]

# Ch1: hello, world in Signet and C++
d = folder(3, 4, 5)
rc, o, e = sh(d, 'python3 signet.py hello.sg --check'); check('ch1 hello.sg --check', rc == 0 and 'hello.sg: ok' in o, o + e)
rc, o, e = sh(d, 'python3 signet.py messenger.sg'); check('ch1 messenger.sg -> Hello, world!', rc == 0 and lines(o) == ['Hello, world!'], o + e)
open(d + '/e.sg', 'w').write("echo('Hello, world!')\n")
rc, o, e = sh(d, 'python3 signet.py e.sg'); check('ch1 echo', lines(o) == ['line 1: \'Hello, world!\' = "Hello, world!"'], o + e)
open(d + '/l.sg', 'w').write('let v = listen(float::, "Supply voltage?")\necho(v * 2)\n')
rc, o, e = sh(d, 'python3 signet.py l.sg', stdin='12\n'); check('ch1 listen', 'line 2: v * 2 = 24' in o, o + e)

# Ch2: watts from volts and amps (Python module, C++ display)
d = folder(17, 18, 19, 20)
rc, o, e = sh(d, 'python3 signet.py wiring.sg --param volts=12 --param amps=0.3'); check('ch2 wiring.sg -> 3.6', rc == 0 and lines(o)[-1:] == ['3.6'], o + e)
open(d + '/s.sg', 'w').write('run(source)\necho(source.k1!)\n')
rc, o, e = sh(d, 'python3 signet.py s.sg'); check('ch2 source.sg as a module -> 123.4', rc == 0 and 'source.k1! = 123.4' in o, o + e)

# Ch8: multiply in every language with a toolchain here
for lab, idx in (('multiply.py', 85), ('multiply.sg', 88), ('multiply.c', 91), ('multiply.cpp', 92), ('multiply.rs', 98),
                 ('multiply.jl', 86), ('multiply.a68', 87), ('multiply.adb', 94), ('multiply.f90', 96)):
    tool = {'jl': 'julia', 'a68': 'a68g', 'adb': 'gnatmake', 'f90': 'gfortran'}.get(lab.split('.')[1])
    if tool and not shutil.which(tool):
        results.append((f'ch8 {lab}', None, f'{tool} not installed')); print(f'SKIP ch8 {lab} ({tool} not installed)'); continue
    d = folder(idx, extra=[('w.sg', 'connect(12.0, multiply.volts)\nconnect(0.5, multiply.amps)\nrun(multiply)\necho(multiply.watts!)\n')])
    rc, o, e = sh(d, 'python3 signet.py w.sg'); check(f'ch8 {lab} -> 6.0', rc == 0 and 'multiply.watts! = 6' in o, o + e)

# Ch9: cruise control, Python car and C++ controller
d = folder(99, 100, 101)
rc, o, e = sh(d, 'python3 signet.py cruise.sg --param v0=25', timeout=1800)
out = lines(o); check('ch9 cruise.sg --param v0=25 runs 240 steps', rc == 0 and len(out) >= 240, (o[-400:] + e[-400:]))

# Ch7: saturate.sg and excess.sg as Signet modules (wave.jl replaced by a Python series)
wave = '# signet: out series::wave\nfrom signet import signals\nimport math\nsignals.wave = signals.series([math.sin(k / 5) for k in range(64)], domain="time", start=0.0, step=0.1)\n'
d = folder(78, 79, extra=[('wave.py', wave), ('w.sg', 'run(wave)\nconnect(wave.wave!, saturate.s1)\nconnect(0.5, saturate.limit)\nrun(saturate)\nconnect(wave.wave!, excess.s1)\nconnect(0.5, excess.limit)\nrun(excess)\necho(max(saturate.s2!), max(excess.s2!))\n')])
rc, o, e = sh(d, 'python3 signet.py w.sg'); check('ch7 saturate.sg and excess.sg', rc == 0 and '= 0.5, ' in o, o + e)

# Ch10: the TVAC example with Rust stand-ins for tvac.rs and performance_test.rs
if os.path.isdir(HERE + '/fixtures/chamber'):
    d = folder(extra=[(n, open(HERE + '/fixtures/chamber/' + n).read()) for n in ('tvac.rs', 'performance_test.rs')])
    open(d + '/run.sg', 'w').write(q(b[102]['text']).replace('delay(13500)', 'delay(1)') + '\n')
    rc, o, e = sh(d, 'python3 signet.py run.sg', timeout=1200)
    nm = lambda l: re.sub(r'made by [\w-]+:', 'made by F:', re.sub(r'\d{4}-\d\d-\d\dT[\d:]+Z', 'T', l.strip()))
    want = [nm(l.replace('→', '').replace('.sig', '!')) for l in q(b[103]['text']).splitlines()]
    got = [nm(l) for l in lines(o) if 'lineage' in l or l.startswith('  ')]
    check('ch10 TVAC run + lineage (book output, names shown with !)', rc == 0 and got == want, '\n'.join(got) + '\nWANT\n' + '\n'.join(want) + e)
    rc, o, e = sh(d, 'python3 signet.py --lineage performance_test.report!'); check('ch10 ./signet --lineage performance_test.report!', rc == 0, o + e)

# Ch16: the race, Python generator and Signet/Python competitors
d = folder(110, 111, 112, extra=[('launch.sg', 'run(generator)\n')])
rc, o, e = sh(d, 'python3 signet.py launch.sg'); check('ch16 launch.sg', rc == 0 and os.path.exists(d + '/generator.x.sig'), o + e)
rc, o1, e = sh(d, 'python3 signet.py speedcheck.sg'); rc2, o2, e2 = sh(d, 'python3 speedcheck.py')
s1 = re.findall(r'[\d.]+(?:e-?\d+)?$', lines(o1)[-1]) if lines(o1) else []; s2 = lines(o2)[-1:] 
check('ch16 Signet std matches NumPy std', s1 and s2 and abs(float(s1[0]) - float(s2[0])) < 1e-12, o1 + e + o2 + e2)

# Ch17: reentry wiring parses
d = folder(116); rc, o, e = sh(d, 'python3 signet.py reentry.sg --check')
check('ch17 reentry.sg wiring parses (modules not in the book)', 'line' in e and 'no module atmosphere' in e or rc == 0, o + e)

# App E: connections -> sys2dot -> dot; visualizer.py
# sys2dot.py as the book prints it (block 128), plus the closing line the book omits (erratum, 2nd edition)
d = folder(17, 18, 19, 20, extra=[('sys2dot.py', q(b[128]['text']) + '\nprint("}")\n')]); shutil.copy(REL + '/visualizer.py', d)
rc, o, e = sh(d, 'python3 signet.py wiring.sg --connections | python3 sys2dot.py | dot -Tsvg -o system_1.svg')
check('appE --connections | sys2dot.py | dot', rc == 0 and os.path.getsize(d + '/system_1.svg') > 500, o + e)
sh(d, 'python3 signet.py wiring.sg --param volts=12 --param amps=0.3')
rc, o, e = sh(d, 'python3 visualizer.py wiring.sg -o v.svg'); check('appE visualizer.py (signet.py beside it)', rc == 0 and '<svg' in open(d + '/v.svg').read(), o + e)
d2 = folder(99, 100, 101); shutil.copy(REL + '/visualizer.py', d2)
rc, o, e = sh(d2, 'python3 visualizer.py cruise.sg --label controller=1:controller --label car=2:car -o c.svg'); check('appE visualizer.py on cruise.sg (stepped loop)', rc == 0 and 'stepped' in open(d2 + '/c.svg').read(), o + e)

# Helpers: export, and build signet.rs as the book shows
d = folder()
rc, o, e = sh(d, 'python3 signet.py --export-helpers include')
check('helpers exported', rc == 0 and os.path.exists(d + '/include/signet.rs') and os.path.exists(d + '/include/signet.hpp'), o + e)
if shutil.which('rustc'):
    rc, o, e = sh(d, 'rustc --edition 2021 -O --crate-type rlib --crate-name signet include/signet.rs -o include/libsignet.rlib')
    check('signet.rs builds as an rlib', rc == 0, e)
rc, o, e = sh(d, 'g++ -O2 -std=c++17 -fsyntax-only -x c++ include/signet.hpp'); check('signet.hpp compiles', rc == 0, e)
rc, o, e = sh(d, 'gcc -O2 -std=c11 -fsyntax-only -x c include/signet.h'); check('signet.h compiles', rc == 0, e)

# CLI behaviour the book prints
d = folder(3, 4, 5); sh(d, 'python3 signet.py messenger.sg')
rc, o, e = sh(d, 'python3 signet.py --lineage hello.message!'); check('--lineage accepts name!', rc == 0 and 'stamp ok' in o, o + e)
rc, o, e = sh(d, 'python3 signet.py --lineage hello.message.sig'); check('--lineage accepts name.sig', rc == 0 and o.startswith('hello.message! ='), o + e)
rc, o, e = sh(d, 'python3 signet.py --lineage nope!'); check('--lineage missing -> exit 1', rc == 1, o + e)
ver = re.search(r'^VERSION = "(.*?)"', open(SIG).read(), re.M).group(1)
rc, o, e = sh(d, 'python3 signet.py --version'); check(f'--version {ver}', ver in o + e, o + e)

# ======== 26.b.0.1.7 additions: not in the book ========
def run_sg(code, *args):
    d = folder(); open(d + '/t.sg', 'w').write(code)
    return sh(d, 'python3 signet.py t.sg ' + ' '.join(args))

# elseif
code = "for k = 0:4\n  if k == 0 then\n    echo('zero')\n  elseif k == 1 then\n    echo('one')\n  elseif k < 4\n    echo('two or three')\n  else\n    echo('four')\n  end if\nnext k\n"
rc, o, e = run_sg(code); check('0.1.7 elseif chain with else', rc == 0 and [l.split(' = ')[-1] for l in lines(o)] == ['"zero"', '"one"', '"two or three"', '"two or three"', '"four"'], o + e)
rc, o, e = run_sg("let x = 2\nif x == 1 then\n  echo(1)\nelseif x == 2 then\n  echo(2)\nend if\n"); check('0.1.7 elseif without else', rc == 0 and lines(o) == ['line 5: 2 = 2'], o + e)
rc, o, e = run_sg("let x = 1\nelseif x == 1 then\nend if\n", '--check'); check('0.1.7 elseif without if', rc != 0 and 'line 2: elseif without if' in o + e, o + e)
rc, o, e = run_sg("let x = 1\nif x == 1 then\nelse\nelseif x == 2 then\nend if\n", '--check'); check('0.1.7 elseif after else', rc != 0 and 'line 4: elseif without if' in o + e, o + e)
rc, o, e = run_sg("let x = 1\nif x == 1 then\nelseif x == 2 then\n", '--check'); check('0.1.7 open elseif chain reported at its if', rc != 0 and 'line 2: if without end if' in o + e, o + e)

# base
rc, o, e = run_sg("echo(base(255, 10, 16), base('FF', 16, 10), base(hex::FF, 16, 2), base(bits::8::00000101, 2, 10), base(1010, 2, 10), base(-255, 10, 16), base('zz', 36, 10))\n")
check('0.1.7 base', rc == 0 and o.strip().endswith('= "FF", 255, "11111111", 5, 10, "-FF", 1295'), o + e)
for code, msg in (('base(19, 8, 10)', "19 isn't a number in base 8"), ('base(1.5, 10, 16)', 'base takes an integer'),
                  ('base(5, 10, 37)', 'bases from 2 to 36'), ('base(5, 10)', 'base takes 3 values')):
    rc, o, e = run_sg(f'echo({code})\n'); check(f'0.1.7 {code} stops: {msg}', rc != 0 and msg in o + e, o + e)
rc, o, e = run_sg('let base = 2\n'); check('0.1.7 base is still a built-in name', rc != 0 and "base is built in and can't be a variable" in o + e, o + e)

# quaternion and hypercomplex
rc, o, e = run_sg("let i = (0, 1, 0, 0)\nlet j = (0, 0, 1, 0)\nlet k = (0, 0, 0, 1)\necho(i * j, j * i, i * j * k, (1, 2, 3, 4) * (1 + 2im))\n")
check('0.1.7 quaternion products', rc == 0 and o.strip().endswith('= (0.0, 0.0, 0.0, 1.0), (0.0, 0.0, 0.0, -1.0), (-1.0, 0.0, 0.0, 0.0), (-3.0, 4.0, 11.0, -2.0)'), o + e)
rc, o, e = run_sg("let q = (1, 2, 3, 4)\necho(abs(q), conj(q), Re(q), Im(q), q ** 2, versor((0, 3, 0, 4)))\n")
check('0.1.7 quaternion abs, conj, Re, Im, power, versor', rc == 0 and o.strip().endswith('= 5.477225575051661, (1.0, -2.0, -3.0, -4.0), 1.0, [2.0, 3.0, 4.0], (-28.0, 4.0, 6.0, 8.0), (0.0, 0.6, 0.0, 0.8)'), o + e)
rc, o, e = run_sg("let a = quat2ang(ang2quat(0.3, -0.2, 0.1))\necho(abs(a[0] - 0.3) < 1e-12, abs(a[1] + 0.2) < 1e-12, abs(a[2] - 0.1) < 1e-12)\n"
                  "echo(ang2quat(1.5707963267948966, 0, 0))\necho(quat2ang(ang2quat(0.7, 1.5707963267948966, 0.3)))\n")
check('0.1.7 ang2quat / quat2ang (ZYX, radians; gimbal lock folds X into Z)', rc == 0 and 'true, true, true' in o and '(0.7071067811865476, 0.0, 0.0, 0.70710678118654' in o
      and re.search(r'= \[0\.39999999999999\d*, 1\.5707963267948966, 0\.0\]', o), o + e)
rc, o, e = run_sg("let v = [(1, 2, 3, 4), (0, 1, 0, 0)]\necho(sum(v), mean(v), length(v), v[1], v .* 2)\nlet hypercomplex::h = 3\nh = 1 + 2im\nh = (1, 0, 0, 0)\necho(h)\n")
check('0.1.7 vector::quaternion and hypercomplex', rc == 0 and '= (1.0, 3.0, 3.0, 4.0), (0.5, 1.5, 1.5, 2.0), 2, (0.0, 1.0, 0.0, 0.0), [(2.0, 4.0, 6.0, 8.0), (0.0, 2.0, 0.0, 0.0)]' in o and 'h = (1.0, 0.0, 0.0, 0.0)' in o, o + e)
for code, msg in (('(1, 2, 3, 4) < (1, 2, 3, 4)', "can't order quaternions"), ('sin((1, 2, 3, 4))', 'sin needs a real or complex number'),
                  ('(1, 2, 3)', 'a quaternion is written (w, x, y, z)'), ('quat2ang(1.0)', 'quat2ang needs a quaternion'),
                  ('versor((0, 0, 0, 0))', "isn't zero"), ('(1, 2, 3, 4) / (0, 0, 0, 0)', 'division by zero')):
    rc, o, e = run_sg(f'echo({code})\n'); check(f'0.1.7 {code} stops: {msg}', rc != 0 and msg in o + e, o + e)
rc, o, e = run_sg('let quaternion::q = 3\n'); check('0.1.7 quaternion:: does not promote, as complex:: does not', rc != 0 and 'expected quaternion, got int' in o + e, o + e)
rc, o, e = run_sg('let num::n = (1, 0, 0, 0)\n'); check('0.1.7 num stays real or complex', rc != 0 and 'expected num, got quaternion' in o + e, o + e)

# quaternion Signals through a module in every language with a toolchain here
QPORTS = 'signet: in quaternion::q, in vector::quaternion::v, in series::quaternion::s, in hypercomplex::h, out quaternion::r, out vector::quaternion::rv, out series::quaternion::rs'
QMODS = {
 'py': (None, f'# {QPORTS}\nfrom signet import signals, Quaternion\nq, v, s, h = signals.q, signals.v, signals.s, signals.h\n'
        'signals.r = Quaternion(q.w * 2, q.x, q.y, q.z)\nsignals.rv = v\ns.values[0] = Quaternion(9, *s.values[0][1:])\nsignals.rs = signals.series(s.values, domain=s.domain, x=s.x)\n'),
 'jl': ('julia', f'# {QPORTS}\nusing Signet: signals, series\nusing Quaternions\nq, v, s = signals.q, signals.v, signals.s\n'
        'signals.r = Quaternion(2 * q.s, q.v1, q.v2, q.v3)\nsignals.rv = v\nvals = copy(s.values)\nvals[1] = Quaternion(9.0, vals[1].v1, vals[1].v2, vals[1].v3)\n'
        'signals.rs = series(vals; domain=s.domain, x=s.x)\n'),
 'c': ('gcc', f'// {QPORTS}\n#include <signet.h>\nint main(void) {{\n    signet_quaternion q = signet_get_quaternion("q");\n    signet_quaternions v = signet_get_quaternions("v");\n'
       '    signet_qseries s = signet_get_qseries("s");\n    q.w *= 2;\n    signet_put_quaternion("r", q, NULL);\n    signet_put_quaternions("rv", v.v, v.n, NULL);\n'
       '    s.values[0].w = 9;\n    signet_put_qseries("rs", s, NULL);\n    return 0;\n}\n'),
 'cpp': ('g++', f'// {QPORTS}\n#include <signet.hpp>\nint main() {{\n    auto q = signet::in<signet::Quaternion>("q");\n    auto s = signet::in<signet::QuaternionSeries>("s");\n'
         '    q.w *= 2;\n    signet::out("r", q);\n    signet::out("rv", signet::in<std::vector<signet::Quaternion>>("v"));\n    s.values[0].w = 9;\n    signet::out("rs", s);\n}\n'),
 'rs': ('rustc', f'// {QPORTS}\nfn main() {{\n    let mut q = signet::get_quaternion("q");\n    let mut s = signet::get_quaternion_series("s");\n    q.w *= 2.0;\n'
        '    signet::put("r", &q, "");\n    signet::put("rv", &signet::get_vec_quaternion("v"), "");\n    s.values[0].w = 9.0;\n    signet::put("rs", &s, "");\n}\n'),
 'adb': ('gnatmake', f'--  {QPORTS}\nwith Signet;\nprocedure M is\n   Q : Signet.Quaternion := Signet.Get_Quaternion ("q");\n   S : Signet.Quaternion_Series := Signet.Get_Quaternion_Series ("s");\n'
         'begin\n   Q.W := Q.W * 2.0;\n   Signet.Put ("r", Q);\n   Signet.Put ("rv", Signet.Get_Quaternions ("v"));\n   S.Values (1).W := 9.0;\n   Signet.Put ("rs", S);\nend M;\n'),
 'f90': ('gfortran', f'! {QPORTS}\nprogram m\n  use signet\n  implicit none\n  type(signet_quaternion) :: q\n  type(signet_quaternion), allocatable :: v(:)\n  type(signet_qseries) :: s\n'
         "  call signet_get('q', q)\n  call signet_get('v', v)\n  call signet_get('s', s)\n  q%w = q%w * 2\n  call signet_put('r', q)\n  call signet_put('rv', v)\n"
         "  s%values(1)%w = 9\n  call signet_put('rs', s)\nend program m\n"),
 'hs': ('ghc', f'-- {QPORTS}\nimport Signet\nmain :: IO ()\nmain = do\n  q <- getQuaternion "q"\n  v <- getQuaternions "v"\n  s <- getQuaternionSeries "s"\n'
        '  put "r" q { qw = 2 * qw q } ""\n  put "rv" v ""\n  put "rs" s { seriesValues = case seriesValues s of (a : rest) -> a { qw = 9 } : rest; [] -> [] } ""\n'),
 'a68': ('a68g', f'# {QPORTS} #\nBEGIN\n   SIGNETQUAT q := signet get quaternion ("q");\n   SIGNETQSERIES s := signet get qseries ("s");\n   w OF q := w OF q * 2;\n'
         '   signet put quaternion ("r", q, "");\n   signet put quaternions ("rv", signet get quaternions ("v"), "");\n   w OF (values OF s)[1] := 9;\n   signet put qseries ("rs", s, "")\nEND\n'),
}
QMK = '# signet: out series::quaternion::s\nfrom signet import signals, Quaternion\nsignals.s = signals.series([Quaternion(1, 0, 0, 0), Quaternion(0, 1, 2, 3)], domain="time", start=0.0, step=0.5)\n'
QW = 'run(mk)\nconnect((1, 2, 3, 4), m.q)\nconnect([(1, 0, 0, 0), (0, 1, 0, 0)], m.v)\nconnect(mk.s!, m.s)\nconnect(1 + 2im, m.h)\nrun(m)\necho(m.r!, m.rv!, m.rs!)\n'
QWANT = ('= (2.0, 2.0, 3.0, 4.0), [(1.0, 0.0, 0.0, 0.0), (0.0, 1.0, 0.0, 0.0)], ',
         {"domain": "time", "x": [0.0, 0.5], "values": {"w": [9.0, 0.0], "x": [0.0, 1.0], "y": [0.0, 2.0], "z": [0.0, 3.0]}})
def qgot(o):                       # (echoed r! and rv!, rs! as parsed JSON: key order differs by language)
    t = o.strip().splitlines()[-1] if o.strip() else ''
    k = t.find('= ('); j = t.find('{', k)
    try:
        return t[k:j], json.loads(t[j:])
    except ValueError:
        return t, None
for ext, (tool, src) in QMODS.items():
    if tool and not shutil.which(tool):
        results.append((f'0.1.7 quaternion Signals in m.{ext}', None, f'{tool} not installed')); print(f'SKIP 0.1.7 quaternion Signals in m.{ext} ({tool} not installed)'); continue
    d = folder(extra=[(f'm.{ext}', src), ('mk.py', QMK), ('w.sg', QW)])
    rc, o, e = sh(d, 'python3 signet.py w.sg'); check(f'0.1.7 quaternion Signals in m.{ext}', rc == 0 and qgot(o) == QWANT, o + e)

# Haskell modules
if shutil.which('ghc'):
    mul = '-- signet: in float::volts, in float::amps, out float::watts\nimport Signet\n\nmain :: IO ()\nmain = do\n  v <- getFloat "volts"\n  i <- getFloat "amps"\n  put "watts" (v * i) ""\n'
    d = folder(extra=[('multiply.hs', mul), ('w.sg', 'connect(12.0, multiply.volts)\nconnect(0.5, multiply.amps)\nrun(multiply)\necho(multiply.watts!)\n')])
    rc, o, e = sh(d, 'python3 signet.py w.sg'); check('0.1.7 multiply.hs -> 6.0', rc == 0 and 'multiply.watts! = 6' in o, o + e)
    rc, o, e = sh(d, 'python3 signet.py w.sg'); check('0.1.7 multiply.hs is built once', rc == 0 and 'building' not in e, o + e)
    open(d + '/b.sg', 'w').write("connect('x', multiply.volts)\nconnect(0.5, multiply.amps)\nrun(multiply)\n")
    rc, o, e = sh(d, 'python3 signet.py b.sg'); check('0.1.7 multiply.hs refuses text where it wants a number', rc != 0 and 'takes float, got text' in o + e, o + e)
    alls = ('-- signet: in int::n, in bool::b, in text::t, in vector::float::v, in vector::int::vi, in vector::text::vt, in complex::z, in vector::complex::vz, '
            'in series::s, out int::n2, out text::t2, out vector::float::v2, out vector::complex::vz2, out series::s2, out bool::b2, out vector::text::vt2\n'
            'import Signet\n\nmain :: IO ()\nmain = do\n  n <- getInt "n"\n  b <- getBool "b"\n  t <- getText "t"\n  v <- getFloats "v"\n  vi <- getInts "vi"\n'
            '  vt <- getTexts "vt"\n  z <- getComplex "z"\n  vz <- getComplexes "vz"\n  s <- getSeries "s"\n  put "n2" (n + sum vi) ""\n  put "t2" (t ++ " \\"q\\"") ""\n'
            '  put "v2" (map (* 2) v) ""\n  put "vz2" (map (* z) vz) ""\n  put "s2" s { seriesValues = map negate (seriesValues s) } ""\n  put "b2" (not b) ""\n  put "vt2" (reverse vt) ""\n')
    wave = '# signet: out series::wave\nfrom signet import signals\nsignals.wave = signals.series([0.5, 1.5, None], domain="time", start=0.0, step=0.1)\n'
    wire = ("run(wave)\nconnect(3, all.n)\nconnect(true, all.b)\nconnect('héllo wörld', all.t)\nconnect([1.5, 2.5], all.v)\nconnect([1, 2, 3], all.vi)\n"
            "connect(['a b', 'c'], all.vt)\nconnect(1 + 2im, all.z)\nconnect([1im, 2 + 0im], all.vz)\nconnect(wave.wave!, all.s)\nrun(all)\n"
            "echo(all.n2!, all.t2!, all.v2!, all.vz2!, all.b2!, all.vt2!)\necho(all.s2!)\n")
    d = folder(extra=[('all.hs', alls), ('wave.py', wave), ('w.sg', wire)])
    rc, o, e = sh(d, 'python3 signet.py w.sg')
    check('0.1.7 Haskell helper: int, bool, text, vectors, complex, series', rc == 0 and
          '= 9, "héllo wörld \\"q\\"", [3.0, 5.0], [-2.0 + 1.0i, 2.0 + 4.0i], false, ["c", "a b"]' in o and '"values": [-0.5, -1.5, null]' in o, o + e)
else:
    results.append(('0.1.7 Haskell modules', None, 'ghc not installed')); print('SKIP 0.1.7 Haskell modules (ghc not installed)')

# PyPI: 26.b.0.1.N is published as 26.0bN0
pp = os.path.join(REL, 'pyproject.toml')
if os.path.exists(pp):
    ver = open(os.path.join(REL, 'VERSION'), encoding='utf-8').read().strip()
    m = re.fullmatch(r'26\.b\.0\.1\.(\d+)(?:\.([1-9]))?', ver)               # 0.1.N is bN0, 0.1.N.M is b(N*10+M)
    got = re.search(r'^version = "([^"]+)"', open(pp, encoding='utf-8').read(), re.M)
    want = f'26.0b{int(m.group(1)) * 10 + int(m.group(2) or 0)}' if m else None
    check(f'pyproject.toml version matches VERSION {ver}', bool(m and got) and got.group(1) == want,
          got.group(1) if got else 'no version line')

# ======== 26.b.0.1.7.5 additions: not in the book ========
# --graph is what the book's sys2dot.py (with its closing line) makes of --connections
book_dot = q(b[128]['text']) + '\nprint("}")\n'
for blocks, wiring, args in (((17, 18, 19, 20), 'wiring.sg', ''), ((99, 100, 101), 'cruise.sg', ' --param v0=25')):
    d = folder(*blocks, extra=[('sys2dot.py', book_dot)])
    rc1, o1, e1 = sh(d, f'python3 signet.py {wiring}{args} --connections | python3 sys2dot.py')
    rc2, o2, e2 = sh(d, f'python3 signet.py {wiring}{args} --graph')
    check(f'0.1.7.5 --graph on {wiring} matches sys2dot.py', rc1 == 0 and rc2 == 0 and o1 == o2 and o2.startswith('digraph'), o2 + e1 + e2)
    if shutil.which('dot'):
        rc, o, e = sh(d, f'python3 signet.py {wiring}{args} --graph | dot -Tsvg -o g.svg')
        check(f'0.1.7.5 --graph on {wiring} | dot', rc == 0 and os.path.getsize(d + '/g.svg') > 500, e)
d = folder(extra=[('m.py', '# signet: in text::t\n'), ('w.sg', 'connect(\'say "hi"\', m.t)\nrun(m)\n')])
rc, o, e = sh(d, 'python3 signet.py w.sg --graph' + (' | dot -Tsvg -o q.svg' if shutil.which('dot') else ''))
check('0.1.7.5 --graph escapes a quote in a constant', rc == 0, o + e)

ok = sum(1 for r in results if r[1]); bad = [r for r in results if r[1] is False]; skip = [r for r in results if r[1] is None]
print(f'\n{ok} passed, {len(bad)} failed, {len(skip)} skipped')
sys.exit(1 if bad else 0)
