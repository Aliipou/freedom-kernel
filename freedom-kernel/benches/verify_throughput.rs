use criterion::{black_box, criterion_group, criterion_main, Criterion};
use freedom_kernel::engine;
use freedom_kernel::wire::{
    ActionWire, ClaimWire, EntityKind, EntityWire, MachineOwnerWire, OwnershipRegistryWire,
    ResourceWire,
};

fn build_registry_with_n_claims(n: usize) -> OwnershipRegistryWire {
    let owner = EntityWire { name: "alice".to_string(), kind: EntityKind::Human };
    let bot = EntityWire { name: "bot".to_string(), kind: EntityKind::Machine };
    let claims = (0..n)
        .map(|i| ClaimWire {
            holder: bot.clone(),
            resource: ResourceWire {
                name: format!("resource_{i}"),
                rtype: "file".to_string(),
                scope: String::new(),
                is_public: false,
                ifc_label: String::new(),
            },
            can_read: true,
            can_write: false,
            can_delegate: false,
            confidence: 1.0,
            expires_at: None,
        })
        .collect();
    OwnershipRegistryWire {
        claims,
        machine_owners: vec![MachineOwnerWire { machine: bot, owner }],
    }
}

fn build_benign_read_action() -> ActionWire {
    ActionWire {
        action_id: "bench-read".to_string(),
        actor: EntityWire { name: "bot".to_string(), kind: EntityKind::Machine },
        description: String::new(),
        resources_read: vec![ResourceWire {
            name: "resource_0".to_string(),
            rtype: "file".to_string(),
            scope: String::new(),
            is_public: false,
            ifc_label: String::new(),
        }],
        resources_write: vec![],
        resources_delegate: vec![],
        governs_humans: vec![],
        argument: String::new(),
        increases_machine_sovereignty: false,
        resists_human_correction: false,
        bypasses_verifier: false,
        weakens_verifier: false,
        disables_corrigibility: false,
        machine_coalition_dominion: false,
        coerces: false,
        deceives: false,
        self_modification_weakens_verifier: false,
        machine_coalition_reduces_freedom: false,
    }
}

fn bench_verify_100_claims(c: &mut Criterion) {
    let registry = build_registry_with_n_claims(100);
    let action = build_benign_read_action();
    c.bench_function("verify 100-claim registry", |b| {
        b.iter(|| engine::verify(black_box(&registry), black_box(&action)))
    });
}

criterion_group!(benches, bench_verify_100_claims);
criterion_main!(benches);
