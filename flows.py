from vibeblocks import Chain, Flow, FailureStrategy
from blocks import (
    init_run_metadata,
    validate_context_version,
    load_runtime_config,
    validate_request_contract,
    build_gsc_client,
    execute_gsc_operation,
    normalize_output,
    persist_audit_event,
    finalize_run
)

preflight = Chain("preflight", [init_run_metadata, validate_context_version, load_runtime_config, validate_request_contract])
execution = Chain("execution", [build_gsc_client, execute_gsc_operation, normalize_output])
postflight = Chain("postflight", [persist_audit_event, finalize_run])

gsc_read_workflow = Flow(
    "gsc_read_workflow",
    blocks=[preflight, execution, postflight],
    strategy=FailureStrategy.ABORT,
)

gsc_site_mutation_workflow = Flow(
    "gsc_site_mutation_workflow",
    blocks=[preflight, execution, postflight],
    strategy=FailureStrategy.COMPENSATE,
)

gsc_sitemap_mutation_workflow = Flow(
    "gsc_sitemap_mutation_workflow",
    blocks=[preflight, execution, postflight],
    strategy=FailureStrategy.COMPENSATE,
)
