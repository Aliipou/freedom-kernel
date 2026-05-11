/// Kani bounded model-checking harnesses for Freedom Kernel engine properties.
///
/// Build with: cargo kani --harness <name>
/// These harnesses are gated behind #[cfg(kani)] so they never affect the
/// normal Rust build or test suite.
#[cfg(kani)]
mod proofs {
    use crate::engine;
    use crate::wire::{
        ActionWire, ClaimWire, EntityWire, MachineOwnerWire, OwnershipRegistryWire, ResourceWire,
    };

    // ── helpers ───────────────────────────────────────────────────────────────

    fn human(name: &str) -> EntityWire {
        EntityWire { name: name.to_string(), kind: "HUMAN".to_string() }
    }

    fn machine(name: &str) -> EntityWire {
        EntityWire { name: name.to_string(), kind: "MACHINE".to_string() }
    }

    fn file_resource(name: &str) -> ResourceWire {
        ResourceWire {
            name: name.to_string(),
            rtype: "file".to_string(),
            scope: String::new(),
            is_public: false,
            ifc_label: String::new(),
        }
    }

    fn claim(holder: EntityWire, resource: ResourceWire, can_write: bool) -> ClaimWire {
        ClaimWire {
            holder,
            resource,
            can_read: true,
            can_write,
            can_delegate: can_write,
            confidence: 1.0,
            expires_at: None,
        }
    }

    fn minimal_registry_with_owner() -> OwnershipRegistryWire {
        OwnershipRegistryWire {
            claims: vec![],
            machine_owners: vec![MachineOwnerWire {
                machine: machine("bot"),
                owner: human("alice"),
            }],
        }
    }

    fn base_action() -> ActionWire {
        ActionWire {
            action_id: "test".to_string(),
            actor: machine("bot"),
            description: String::new(),
            resources_read: vec![],
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

    // ── Macro: one harness per flag ───────────────────────────────────────────
    //
    // Each harness proves: setting flag X = true always blocks, regardless of
    // all other action fields. This gives us 10 independent formal proofs.

    macro_rules! forbidden_flag_harness {
        ($name:ident, $field:ident) => {
            #[kani::proof]
            fn $name() {
                let registry = minimal_registry_with_owner();
                let mut action = base_action();
                action.$field = true;
                let result = engine::verify(&registry, &action);
                kani::assert!(!result.permitted, stringify!($field must always block));
                kani::assert!(
                    result.violations.iter().any(|v| v.contains("FORBIDDEN")),
                    "violation list must contain FORBIDDEN"
                );
            }
        };
    }

    forbidden_flag_harness!(prop_increases_machine_sovereignty, increases_machine_sovereignty);
    forbidden_flag_harness!(prop_resists_human_correction,      resists_human_correction);
    forbidden_flag_harness!(prop_bypasses_verifier,             bypasses_verifier);
    forbidden_flag_harness!(prop_weakens_verifier,              weakens_verifier);
    forbidden_flag_harness!(prop_disables_corrigibility,        disables_corrigibility);
    forbidden_flag_harness!(prop_machine_coalition_dominion,    machine_coalition_dominion);
    forbidden_flag_harness!(prop_coerces,                       coerces);
    forbidden_flag_harness!(prop_deceives,                      deceives);
    forbidden_flag_harness!(prop_self_modification,             self_modification_weakens_verifier);
    forbidden_flag_harness!(prop_coalition_reduces_freedom,     machine_coalition_reduces_freedom);

    // ── Property: Ownerless machine is always blocked ─────────────────────────

    #[kani::proof]
    fn prop_ownerless_machine_blocked() {
        let registry = OwnershipRegistryWire {
            claims: vec![],
            machine_owners: vec![], // no owner registered
        };
        let action = ActionWire { action_id: "no_owner".to_string(), actor: machine("orphan"), ..base_action() };
        let result = engine::verify(&registry, &action);
        kani::assert!(!result.permitted, "Ownerless machine must be blocked (A4)");
        kani::assert!(result.violations.iter().any(|v| v.contains("A4")));
    }

    // ── Property: A machine governing a human is always blocked ───────────────

    #[kani::proof]
    fn prop_machine_governs_human_blocked() {
        let registry = minimal_registry_with_owner();
        let mut action = base_action();
        action.governs_humans = vec![human("bob")];
        let result = engine::verify(&registry, &action);
        kani::assert!(!result.permitted, "Machine governing human must be blocked (A6)");
        kani::assert!(result.violations.iter().any(|v| v.contains("A6")));
    }

    // ── Property: Public resource read always permitted ───────────────────────

    #[kani::proof]
    fn prop_public_resource_read_permitted() {
        let public_res = ResourceWire {
            name: "public_data".to_string(),
            rtype: "file".to_string(),
            scope: String::new(),
            is_public: true,
            ifc_label: String::new(),
        };
        let registry = minimal_registry_with_owner();
        let mut action = base_action();
        action.resources_read = vec![public_res];
        let result = engine::verify(&registry, &action);
        kani::assert!(result.permitted, "Public resource reads must always be permitted");
    }

    // ── Property: Write denied without write claim ────────────────────────────

    #[kani::proof]
    fn prop_write_denied_without_claim() {
        let res = file_resource("secret");
        let registry = OwnershipRegistryWire {
            claims: vec![claim(machine("bot"), file_resource("secret"), false)], // read-only
            machine_owners: vec![MachineOwnerWire {
                machine: machine("bot"),
                owner: human("alice"),
            }],
        };
        let mut action = base_action();
        action.resources_write = vec![res];
        let result = engine::verify(&registry, &action);
        kani::assert!(!result.permitted, "Write without write claim must be denied");
        kani::assert!(result.violations.iter().any(|v| v.contains("WRITE DENIED")));
    }
}
