# Pipeline Architecture & Risk-Based Routing

MediGuard implements an industry-standard pipeline architecture with risk-based routing, quarantine for bad records, and human-in-the-loop validation.

## Architecture Overview

```
┌─────────────────┐
│  Input Document │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Triage Agent   │  Classify document
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Policy Validator│  Validate against policies
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Compliance Audit│  PHI & Bias detection
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Pipeline Router │  Risk assessment & routing
└────────┬────────┘
         │
    ┌────┴────┬──────────┬──────────────┐
    │        │          │              │
    ▼        ▼          ▼              ▼
┌────────┐ ┌────────┐ ┌────────────┐ ┌──────────┐
│  LOW   │ │  HIGH  │ │  CRITICAL   │ │QUARANTINE│
│  RISK  │ │  RISK  │ │    PHI      │ │          │
└────────┘ └────────┘ └────────────┘ └──────────┘
    │        │          │              │
    │        │          │              │
    └────────┴──────────┴──────────────┘
                    │
                    ▼
            ┌───────────────┐
            │ Human Review │  (if required)
            │     Queue     │
            └───────────────┘
```

## Pipeline Types

### 1. Low Risk Pipeline
- **Criteria**: Low PHI count, compliant, no bias, no errors
- **Processing**: Standard workflow
- **Output**: Direct to final output
- **Human Review**: Not required

### 2. High Risk Pipeline
- **Criteria**: Medium-high PHI, bias detected, high risk level
- **Processing**: Enhanced validation, double-checking
- **Output**: Enhanced validation results
- **Human Review**: Required for high risk level

### 3. Critical PHI Pipeline
- **Criteria**: 5+ PHI detections, critical risk level
- **Processing**: Specialized PHI handling, aggressive redaction
- **Output**: Critical PHI handling results
- **Human Review**: Always required

### 4. Quarantine Pipeline
- **Criteria**: 3+ errors, non-compliant, malformed data
- **Processing**: Stored for human review
- **Output**: Quarantine record
- **Human Review**: Always required

## Risk Assessment

The router assesses risk based on:

1. **PHI Detections**
   - 0 PHI: No risk
   - 1-4 PHI: Low-Medium risk
   - 5+ PHI: Critical risk

2. **Bias Detection**
   - No bias: No risk
   - Low severity: Low risk
   - Medium severity: Medium risk
   - High severity: High risk

3. **Compliance Status**
   - Compliant: No risk
   - Non-compliant: Medium risk

4. **Error Count**
   - 0 errors: No risk
   - 1-2 errors: Low risk
   - 3+ errors: Critical risk (quarantine)

5. **Validation Confidence**
   - High confidence (>0.8): No risk
   - Medium confidence (0.5-0.8): Low risk
   - Low confidence (<0.5): Medium risk

## Risk Levels

- **LOW**: Standard processing, no human review
- **MEDIUM**: Enhanced validation, optional review
- **HIGH**: Enhanced validation, human review required
- **CRITICAL**: Specialized handling, human review required

## Human-in-the-Loop Review

Documents requiring human review are added to a review queue with:

- **Priority Levels**: Critical, High, Normal, Low
- **Review Status**: Pending, In Review, Approved, Rejected, Needs Correction
- **Review Actions**: Approve, Reject, Request Corrections

### Review Queue Access

1. **Streamlit UI**: "👤 Human Review" tab
2. **API**: `HumanInTheLoopQueue` class
3. **CLI**: (Coming soon)

## Quarantine System

Bad records are quarantined with:

- **Storage**: `data/quarantine/` directory
- **Status Tracking**: Pending, Under Review, Approved, Rejected, Fixed, Resolved
- **Release Process**: Human review → Approval → Release

### Quarantine Criteria

- 3+ processing errors
- Non-compliant documents
- Malformed data
- Validation failures

## Pipeline Handlers

### LowRiskPipelineHandler
- Standard processing workflow
- No additional validation
- Fast processing

### HighRiskPipelineHandler
- Enhanced validation
- Double-checking
- Bias detection enabled
- Risk mitigation applied

### CriticalPHIPipelineHandler
- Aggressive PHI redaction
- Additional redaction pass
- Specialized PHI handling
- Always requires human review

## Usage

### Enable Pipeline Routing

```python
from mediaguard.orchestrator import MediGuardOrchestrator

orchestrator = MediGuardOrchestrator(
    enable_pipeline_routing=True  # Enable routing
)

result = orchestrator.process_document(
    document_text="...",
    document_id="doc_001"
)

# Check routing decision
routing = result.get("routing", {})
print(f"Pipeline: {routing.get('pipeline')}")
print(f"Requires Review: {routing.get('requires_human_review')}")
```

### Access Review Queue

```python
# Get pending reviews
pending = orchestrator.human_loop_queue.get_pending_items(priority="critical")

# Approve a document
orchestrator.human_loop_queue.approve(
    document_id="doc_001",
    reviewer="john_doe",
    notes="Looks good"
)
```

### Access Quarantine

```python
# List quarantined records
quarantined = orchestrator.quarantine_manager.list_quarantine_records()

# Release from quarantine
orchestrator.quarantine_manager.release_from_quarantine(
    document_id="doc_001",
    reviewer="john_doe",
    notes="Fixed and verified"
)
```

## Configuration

### Risk Thresholds

```python
router = PipelineRouter()

# Adjust thresholds
router.phi_critical_threshold = 5  # Critical if 5+ PHI
router.bias_high_threshold = "MEDIUM"  # High risk if bias >= MEDIUM
router.error_threshold = 3  # Quarantine if 3+ errors
```

## Benefits

1. **Safety**: Bad records are quarantined, preventing downstream issues
2. **Efficiency**: Low-risk documents processed quickly
3. **Compliance**: High-risk documents get enhanced validation
4. **Quality**: Human review for exceptional cases
5. **Traceability**: All routing decisions are logged
6. **Scalability**: Different pipelines can be optimized independently

## Monitoring

- **Pipeline Metrics**: Track documents per pipeline
- **Review Queue**: Monitor pending reviews
- **Quarantine**: Track quarantined records
- **Risk Distribution**: Analyze risk level distribution

## Future Enhancements

- [ ] Automated retry for quarantined records
- [ ] Machine learning for risk prediction
- [ ] Pipeline performance optimization
- [ ] Advanced routing rules
- [ ] Integration with external review systems
