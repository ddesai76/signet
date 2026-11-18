// signet: in float::setpoint, out temperature
use signet::{get_f64, Stream};
use std::{thread, time::Duration};
fn main() {
    let sp = get_f64("setpoint");
    let mut temp: Stream<f64> = Stream::new("temperature", "time", 1024);
    let (mut t, mut x): (f64, f64) = (0.0, 20.0);
    let step: f64 = if sp > x { 4.0 } else { -4.0 };
    while (sp - x).abs() > step.abs() {
        temp.write(t, x); t += 60.0; x += step;
        thread::sleep(Duration::from_millis(20));
    }
    for _ in 0..20 {
        temp.write(t, sp); t += 60.0;
        thread::sleep(Duration::from_millis(20));
    }
}
