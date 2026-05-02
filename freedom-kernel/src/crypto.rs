use std::sync::OnceLock;

use ed25519_dalek::{Signer, SigningKey};
use rand_core::OsRng;

static KEY: OnceLock<SigningKey> = OnceLock::new();

fn key() -> &'static SigningKey {
    KEY.get_or_init(|| SigningKey::generate(&mut OsRng))
}

/// Sign `msg` with the process-scoped kernel key.
/// Returns (signature_hex, verifying_key_hex).
pub fn sign(msg: &[u8]) -> (String, String) {
    let k = key();
    let sig = k.sign(msg);
    (hex::encode(sig.to_bytes()), hex::encode(k.verifying_key().to_bytes()))
}

pub fn pubkey_hex() -> String {
    hex::encode(key().verifying_key().to_bytes())
}
