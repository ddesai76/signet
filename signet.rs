// signet.rs:  SIGNALS FOR RUST MODULES (standard library only)
// AUTHOR:     DANIEL DESAI
// UPDATED:    2026-11-17
// VERSION:    0.7.0
//
// Built into signet.py: Signet and Starfire compile a module against this as the crate `signet`, so a
// module just says `use signet::{get_f64, put};`. Inputs: get_f64("voltage"). Outputs: put("power", &power, "float").
// The type is optional (pass ""). Anything wrong stops the module with a message and exit code 2.

use std::collections::{HashMap, VecDeque};
use std::sync::OnceLock;

#[derive(Clone, Copy, Debug, PartialEq)]
pub struct Complex {
    pub re: f64,
    pub im: f64,
}

/// w + xi + yj + zk
#[derive(Clone, Copy, Debug, PartialEq)]
pub struct Quaternion {
    pub w: f64,
    pub x: f64,
    pub y: f64,
    pub z: f64,
}

#[derive(Clone, Debug, PartialEq)]
pub struct Series<V> {
    pub domain: String,
    pub x: Vec<f64>,
    pub values: Vec<V>,
}

struct Record {
    kind: String,
    shape: String,
    tok: Vec<String>,
}

fn fail(msg: &str) -> ! {
    eprintln!("signet: {msg}");
    std::process::exit(2)
}

fn env(key: &str) -> Option<String> {
    std::env::var(format!("SIGNET_{key}")).or_else(|_| std::env::var(format!("STARFIRE_{key}"))).ok()
}

fn unescape(t: &str) -> String {
    if t == "\\e" {
        return String::new();
    }
    let mut s = String::new();
    let mut it = t.chars();
    while let Some(c) = it.next() {
        if c != '\\' {
            s.push(c);
            continue;
        }
        match it.next() {
            Some('s') => s.push(' '),
            Some('t') => s.push('\t'),
            Some('n') => s.push('\n'),
            Some('r') => s.push('\r'),
            Some(o) => s.push(o),
            None => s.push('\\'),
        }
    }
    s
}

fn inputs() -> &'static HashMap<String, Record> {
    static M: OnceLock<HashMap<String, Record>> = OnceLock::new();
    M.get_or_init(|| {
        let mut m = HashMap::new();
        let Some(path) = env("SIGNALS_TXT") else { return m };
        let text = std::fs::read_to_string(&path).unwrap_or_else(|e| fail(&format!("can't read {path}: {e}")));
        for line in text.lines() {
            let f: Vec<&str> = line.splitn(4, '\t').collect();
            if f.len() == 4 {
                let tok = f[3].split(' ').filter(|t| !t.is_empty()).map(String::from).collect();
                m.insert(f[0].to_string(), Record { kind: f[1].into(), shape: f[2].into(), tok });
            }
        }
        m
    })
}

fn rec(name: &str, shape: &str, want: &str) -> &'static Record {
    let r = inputs().get(name).unwrap_or_else(|| fail(&format!("no input {name} (see the point's Signet code)")));
    if r.shape != shape {
        fail(&format!("input {name} is {}, not {want}", r.kind));
    }
    r
}

fn num(t: &str) -> f64 {
    t.parse().unwrap_or(f64::NAN)
}

fn real(name: &str, r: &Record, want: &str) {
    if r.kind == "bool" || r.kind == "text" || r.kind == "vector::bool" || r.kind == "vector::text" {
        fail(&format!("input {name} is {}, not {want}", r.kind));
    }
}

pub fn has(name: &str) -> bool {
    inputs().contains_key(name)
}

/// A number input; null reads as NaN.
pub fn get_f64(name: &str) -> f64 {
    let r = rec(name, "s", "a number");
    real(name, r, "a number");
    num(&r.tok[0])
}

pub fn get_i64(name: &str) -> i64 {
    let r = rec(name, "s", "an integer");
    if r.kind != "int" && r.kind != "hex" {
        fail(&format!("input {name} is {}, not an integer", r.kind));
    }
    r.tok[0].parse().unwrap_or_else(|_| fail(&format!("input {name} is not a whole number")))
}

pub fn get_bool(name: &str) -> bool {
    let r = rec(name, "s", "a bool");
    if r.kind != "bool" {
        fail(&format!("input {name} is {}, not a bool", r.kind));
    }
    r.tok[0] == "true"
}

pub fn get_text(name: &str) -> String {
    let r = rec(name, "s", "text");
    if r.kind != "text" {
        fail(&format!("input {name} is {}, not text", r.kind));
    }
    r.tok.first().map(|t| unescape(t)).unwrap_or_default()
}

pub fn get_complex(name: &str) -> Complex {
    let r = rec(name, "c", "a complex number");
    Complex { re: num(&r.tok[0]), im: num(&r.tok[1]) }
}

pub fn get_vec_f64(name: &str) -> Vec<f64> {
    let r = rec(name, "v", "a vector of numbers");
    real(name, r, "a vector of numbers");
    r.tok.iter().map(|t| num(t)).collect()
}

pub fn get_vec_i64(name: &str) -> Vec<i64> {
    let r = rec(name, "v", "a vector of integers");
    if r.kind != "vector::int" && r.kind != "vector::hex" {
        fail(&format!("input {name} is {}, not a vector of integers", r.kind));
    }
    r.tok.iter().map(|t| t.parse().unwrap_or_else(|_| fail(&format!("input {name} has a value that is not whole")))).collect()
}

pub fn get_vec_text(name: &str) -> Vec<String> {
    let r = rec(name, "v", "a vector of text");
    if r.kind != "vector::text" {
        fail(&format!("input {name} is {}, not a vector of text", r.kind));
    }
    r.tok.iter().map(|t| unescape(t)).collect()
}

pub fn get_vec_complex(name: &str) -> Vec<Complex> {
    let r = rec(name, "vc", "a vector of complex numbers");
    r.tok.chunks(2).map(|p| Complex { re: num(&p[0]), im: num(&p[1]) }).collect()
}

fn quat(p: &[String]) -> Quaternion {
    Quaternion { w: num(&p[0]), x: num(&p[1]), y: num(&p[2]), z: num(&p[3]) }
}

/// A quaternion; a real or complex number is read as one too.
pub fn get_quaternion(name: &str) -> Quaternion {
    let r = inputs().get(name).unwrap_or_else(|| fail(&format!("no input {name} (see the point's Signet code)")));
    match r.shape.as_str() {
        "s" if r.kind != "bool" && r.kind != "text" => Quaternion { w: num(&r.tok[0]), x: 0.0, y: 0.0, z: 0.0 },
        "c" => Quaternion { w: num(&r.tok[0]), x: num(&r.tok[1]), y: 0.0, z: 0.0 },
        _ => quat(&rec(name, "q", "a quaternion").tok),
    }
}

pub fn get_vec_quaternion(name: &str) -> Vec<Quaternion> {
    rec(name, "vq", "a vector of quaternions").tok.chunks(4).map(quat).collect()
}

pub fn get_quaternion_series(name: &str) -> Series<Quaternion> {
    let r = rec(name, "xq", "a quaternion series");
    let n: usize = r.tok[1].parse().unwrap_or(0);
    Series {
        domain: r.tok[0].clone(),
        x: r.tok[2..2 + n].iter().map(|t| num(t)).collect(),
        values: r.tok[2 + n..2 + 5 * n].chunks(4).map(quat).collect(),
    }
}

pub fn get_series(name: &str) -> Series<f64> {
    let r = rec(name, "xs", "a real series");
    let n: usize = r.tok[1].parse().unwrap_or(0);
    Series {
        domain: r.tok[0].clone(),
        x: r.tok[2..2 + n].iter().map(|t| num(t)).collect(),
        values: r.tok[2 + n..2 + 2 * n].iter().map(|t| num(t)).collect(),
    }
}

pub fn get_complex_series(name: &str) -> Series<Complex> {
    let r = rec(name, "xc", "a complex series");
    let n: usize = r.tok[1].parse().unwrap_or(0);
    Series {
        domain: r.tok[0].clone(),
        x: r.tok[2..2 + n].iter().map(|t| num(t)).collect(),
        values: r.tok[2 + n..2 + 3 * n].chunks(2).map(|p| Complex { re: num(&p[0]), im: num(&p[1]) }).collect(),
    }
}

fn jnum(d: f64) -> String {
    if !d.is_finite() {
        return "null".into();
    }
    let s = format!("{d:?}");
    if s.contains(['.', 'e', 'E']) { s } else { format!("{s}.0") }
}

fn jstr(t: &str) -> String {
    let mut s = String::from("\"");
    for c in t.chars() {
        match c {
            '"' => s.push_str("\\\""),
            '\\' => s.push_str("\\\\"),
            '\n' => s.push_str("\\n"),
            '\r' => s.push_str("\\r"),
            '\t' => s.push_str("\\t"),
            c if (c as u32) < 0x20 => s.push_str(&format!("\\u{:04x}", c as u32)),
            c => s.push(c),
        }
    }
    s.push('"');
    s
}

fn jlist<T>(v: &[T], f: impl Fn(&T) -> String) -> String {
    format!("[{}]", v.iter().map(f).collect::<Vec<_>>().join(","))
}

fn jcomplexes(v: &[Complex]) -> String {
    format!("{{\"re\":{},\"im\":{}}}", jlist(v, |z| jnum(z.re)), jlist(v, |z| jnum(z.im)))
}

fn jquats(v: &[Quaternion]) -> String {
    format!("{{\"w\":{},\"x\":{},\"y\":{},\"z\":{}}}", jlist(v, |q| jnum(q.w)), jlist(v, |q| jnum(q.x)),
            jlist(v, |q| jnum(q.y)), jlist(v, |q| jnum(q.z)))
}

fn floaty(ty: &str) -> bool {
    ty.ends_with("float")
}

/// What `put` can write. The JSON text and the default type of the value.
pub trait Put {
    fn json(&self, ty: &str) -> (String, String);
}

macro_rules! put_float { ($($t:ty),*) => {$(
    impl Put for $t { fn json(&self, _: &str) -> (String, String) { (jnum(*self as f64), "float".into()) } }
    impl Put for Vec<$t> { fn json(&self, _: &str) -> (String, String) { (jlist(self, |e| jnum(*e as f64)), "vector::float".into()) } }
    impl Put for [$t] { fn json(&self, _: &str) -> (String, String) { (jlist(self, |e| jnum(*e as f64)), "vector::float".into()) } }
)*}}
macro_rules! put_int { ($($t:ty),*) => {$(
    impl Put for $t { fn json(&self, ty: &str) -> (String, String) {
        (if floaty(ty) { jnum(*self as f64) } else { self.to_string() }, "int".into()) } }
    impl Put for Vec<$t> { fn json(&self, ty: &str) -> (String, String) {
        (jlist(self, |e| if floaty(ty) { jnum(*e as f64) } else { e.to_string() }), "vector::int".into()) } }
    impl Put for [$t] { fn json(&self, ty: &str) -> (String, String) {
        (jlist(self, |e| if floaty(ty) { jnum(*e as f64) } else { e.to_string() }), "vector::int".into()) } }
)*}}
put_float!(f64, f32);
put_int!(i8, i16, i32, i64, u8, u16, u32, u64, usize, isize);

impl Put for bool {
    fn json(&self, _: &str) -> (String, String) { (self.to_string(), "bool".into()) }
}
impl Put for str {
    fn json(&self, _: &str) -> (String, String) { (jstr(self), "text".into()) }
}
impl Put for String {
    fn json(&self, _: &str) -> (String, String) { (jstr(self), "text".into()) }
}
impl Put for Complex {
    fn json(&self, _: &str) -> (String, String) { (format!("{{\"re\":{},\"im\":{}}}", jnum(self.re), jnum(self.im)), "complex".into()) }
}
impl Put for Vec<Complex> {
    fn json(&self, _: &str) -> (String, String) { (jcomplexes(self), "vector::complex".into()) }
}
impl Put for [Complex] {
    fn json(&self, _: &str) -> (String, String) { (jcomplexes(self), "vector::complex".into()) }
}
impl Put for Quaternion {
    fn json(&self, _: &str) -> (String, String) {
        (format!("{{\"w\":{},\"x\":{},\"y\":{},\"z\":{}}}", jnum(self.w), jnum(self.x), jnum(self.y), jnum(self.z)), "quaternion".into())
    }
}
impl Put for Vec<Quaternion> {
    fn json(&self, _: &str) -> (String, String) { (jquats(self), "vector::quaternion".into()) }
}
impl Put for [Quaternion] {
    fn json(&self, _: &str) -> (String, String) { (jquats(self), "vector::quaternion".into()) }
}
impl Put for Series<Quaternion> {
    fn json(&self, _: &str) -> (String, String) {
        (format!("{{\"domain\":{},\"x\":{},\"values\":{}}}", jstr(&self.domain), jlist(&self.x, |e| jnum(*e)), jquats(&self.values)),
         format!("series::{}::quaternion", self.domain))
    }
}
impl Put for Vec<String> {
    fn json(&self, _: &str) -> (String, String) { (jlist(self, |e| jstr(e)), "vector::text".into()) }
}
impl Put for Series<f64> {
    fn json(&self, _: &str) -> (String, String) {
        (format!("{{\"domain\":{},\"x\":{},\"values\":{}}}", jstr(&self.domain), jlist(&self.x, |e| jnum(*e)), jlist(&self.values, |e| jnum(*e))),
         format!("series::{}::float", self.domain))
    }
}
impl Put for Series<Complex> {
    fn json(&self, _: &str) -> (String, String) {
        (format!("{{\"domain\":{},\"x\":{},\"values\":{}}}", jstr(&self.domain), jlist(&self.x, |e| jnum(*e)), jcomplexes(&self.values)),
         format!("series::{}::complex", self.domain))
    }
}

/// Writes output `name` as <prefix>-<module>.<name>.sig, whole and then renamed so a reader never sees half a
/// file. `ty` is the Signet type ("float", "vector::float", ...), or "" for the value's own.
pub fn put<T: Put + ?Sized>(name: &str, value: &T, ty: &str) {
    let (json, own) = value.json(ty);
    emit(name, &json, &if ty.is_empty() { own } else { ty.to_string() });
}

fn emit(name: &str, json: &str, ty: &str) {
    let module = env("MODULE").unwrap_or_else(|| fail("SIGNET_MODULE is not set (run from Signet or Starfire)"));
    let prefix = env("PREFIX").unwrap_or_default();
    let path = if prefix.is_empty() { format!("{module}.{name}.sig") } else { format!("{prefix}-{module}.{name}.sig") };
    let tmp = format!("{path}.tmp");
    std::fs::write(&tmp, format!("{{\"value\":{json},\"type\":{}}}\n", jstr(&ty))).unwrap_or_else(|e| fail(&format!("can't write {tmp}: {e}")));
    std::fs::rename(&tmp, &path).unwrap_or_else(|e| fail(&format!("can't rename {tmp}: {e}")));
}

/// What a stream holds: f64 or Complex.
pub trait StreamValue: Copy {
    const KIND: &'static str;
    fn jvalues(v: &[Self]) -> String;
}
impl StreamValue for f64 {
    const KIND: &'static str = "float";
    fn jvalues(v: &[f64]) -> String { jlist(v, |e| jnum(*e)) }
}
impl StreamValue for Complex {
    const KIND: &'static str = "complex";
    fn jvalues(v: &[Complex]) -> String { jcomplexes(v) }
}

/// An output stream: `let mut s = Stream::<f64>::new("volts", "time", 1024); s.write(t, v);`. Its .sig keeps the
/// last `window` samples, rewritten whole at each write.
pub struct Stream<V: StreamValue> {
    name: String,
    domain: String,
    window: usize,
    count: u64,
    x: VecDeque<f64>,
    values: VecDeque<V>,
}

impl<V: StreamValue> Stream<V> {
    pub fn new(name: &str, domain: &str, window: usize) -> Self {
        if window == 0 {
            fail("a stream's window must be above 0");
        }
        Stream { name: name.into(), domain: domain.into(), window, count: 0, x: VecDeque::new(), values: VecDeque::new() }
    }

    pub fn write(&mut self, t: f64, v: V) {
        if !t.is_finite() {
            fail("a stream's t must be a finite number");
        }
        self.x.push_back(t);
        self.values.push_back(v);
        if self.x.len() > self.window {
            self.x.pop_front();
            self.values.pop_front();
        }
        self.count += 1;
        let x: Vec<f64> = self.x.iter().copied().collect();
        let vals: Vec<V> = self.values.iter().copied().collect();
        emit(&self.name,
             &format!("{{\"domain\":{},\"x\":{},\"values\":{},\"window\":{},\"count\":{},\"ended\":false}}",
                      jstr(&self.domain), jlist(&x, |e| jnum(*e)), V::jvalues(&vals), self.window, self.count),
             &format!("stream::{}::{}", self.domain, V::KIND));
    }
}

// A stream's .sig, read without a JSON library: (x, values, count, ended) of the window.
fn key(s: &str, k: &str) -> Option<usize> {
    let q = format!("\"{k}\"");
    let mut from = 0;
    while let Some(p) = s[from..].find(&q) {
        let mut i = from + p + q.len();
        let b = s.as_bytes();
        while i < b.len() && b[i] == b' ' { i += 1; }
        if i < b.len() && b[i] == b':' {
            i += 1;
            while i < b.len() && b[i] == b' ' { i += 1; }
            return Some(i);
        }
        from += p + 1;
    }
    None
}

fn numbers(s: &str, at: Option<usize>) -> Vec<f64> {
    let Some(i) = at else { return Vec::new() };
    if !s[i..].starts_with('[') { return Vec::new(); }
    let end = s[i..].find(']').map(|e| i + e).unwrap_or(s.len());
    s[i + 1..end].split(',').map(str::trim).filter(|t| !t.is_empty()).map(|t| if t == "null" { f64::NAN } else { num(t) }).collect()
}

fn read_stream(path: &str) -> (Vec<f64>, Vec<f64>, u64, bool) {
    let Ok(s) = std::fs::read_to_string(path) else { return (Vec::new(), Vec::new(), 0, false) };
    let vi = key(&s, "values");
    if vi.map_or(false, |i| s[i..].starts_with('{')) {
        fail(&format!("{path} is a complex stream: read it in Python or Julia"));
    }
    let (x, v) = (numbers(&s, key(&s, "x")), numbers(&s, vi));
    if x.len() != v.len() { return (Vec::new(), Vec::new(), 0, false); }     // caught between writes
    let count = key(&s, "count").map(|i| s[i..].chars().take_while(|c| c.is_ascii_digit()).collect::<String>().parse().unwrap_or(0))
        .unwrap_or(x.len() as u64);
    let ended = key(&s, "ended").map_or(false, |i| s[i..].starts_with('t'));
    (x, v, count, ended)
}

/// A real stream input: `let mut s = get_stream("volts");`. `for (t, v) in &mut s` (or `s.next()`) follows it
/// sample by sample until its module ends; `s.latest()` is the newest sample; `s.window()` the samples kept.
pub struct StreamIn {
    paths: Vec<String>,
    seen: Vec<u64>,
    queue: VecDeque<(f64, f64)>,
}

pub fn get_stream(name: &str) -> StreamIn {
    let r = rec(name, "st", "a stream");
    let paths: Vec<String> = r.tok.iter().map(|t| unescape(t)).collect();
    StreamIn { seen: vec![0; paths.len()], paths, queue: VecDeque::new() }
}

impl StreamIn {
    pub fn window(&self) -> Vec<(f64, f64)> {
        let mut rows: Vec<(f64, f64)> = Vec::new();
        for p in &self.paths {
            let (x, v, _, _) = read_stream(p);
            rows.extend(x.into_iter().zip(v));
        }
        rows.sort_by(|a, b| a.0.total_cmp(&b.0));
        rows
    }
    pub fn latest(&self) -> Option<(f64, f64)> {
        self.window().last().copied()
    }
    pub fn ended(&self) -> bool {
        self.paths.iter().all(|p| read_stream(p).3)
    }
}

impl Iterator for StreamIn {
    type Item = (f64, f64);
    fn next(&mut self) -> Option<(f64, f64)> {
        while self.queue.is_empty() {
            let mut done = true;
            let mut got: Vec<(f64, f64)> = Vec::new();
            for (k, p) in self.paths.iter().enumerate() {
                let (x, v, count, ended) = read_stream(p);
                let n = (count.saturating_sub(self.seen[k]) as usize).min(x.len());
                got.extend(x[x.len() - n..].iter().copied().zip(v[v.len() - n..].iter().copied()));
                self.seen[k] = self.seen[k].max(count);
                done &= ended;
            }
            got.sort_by(|a, b| a.0.total_cmp(&b.0));
            self.queue.extend(got);
            if self.queue.is_empty() {
                if done { return None; }
                std::thread::sleep(std::time::Duration::from_millis(20));
            }
        }
        self.queue.pop_front()
    }
}
