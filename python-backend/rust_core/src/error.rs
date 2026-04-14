// error.rs — Typed error handling for indicator computations.
// Adapted from kand (MIT/Apache-2.0). Replaces &'static str errors.

#[derive(thiserror::Error, Debug)]
pub enum TAError {
    #[error("Invalid parameter: {0}")]
    InvalidParameter(&'static str),

    #[error("Insufficient data: need at least {need}, got {got}")]
    InsufficientData { need: usize, got: usize },

    #[error("Input arrays have mismatched lengths: {a} vs {b}")]
    LengthMismatch { a: usize, b: usize },

    #[error("Input data contains NaN values")]
    NaNDetected,

    #[error("Calculation error: {0}")]
    CalculationError(&'static str),
}

pub type TAResult<T> = std::result::Result<T, TAError>;
