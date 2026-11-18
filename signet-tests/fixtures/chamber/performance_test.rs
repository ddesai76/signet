// signet: in float::temperature, out bool::report
use signet::{get_f64, put};
fn main() {
    let t = get_f64("temperature");
    put("report", &(-45.0..=65.0).contains(&t), "bool");
}
