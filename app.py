"""
MediGuard Streamlit Demo UI

A simple web interface for demonstrating the MediGuard
Multi-Agent Clinical Compliance Orchestrator.
"""

import streamlit as st
import json
from pathlib import Path
from mediaguard.orchestrator import MediGuardOrchestrator
from mediaguard.rag.vector_store import VectorStore
import os

# Page configuration
st.set_page_config(
    page_title="MediGuard - Clinical Compliance Orchestrator",
    page_icon="🏥",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for better styling
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        color: #1f77b4;
        text-align: center;
        margin-bottom: 1rem;
    }
    .sub-header {
        font-size: 1.2rem;
        color: #666;
        text-align: center;
        margin-bottom: 2rem;
    }
    .success-box {
        padding: 1rem;
        border-radius: 0.5rem;
        background-color: #d4edda;
        border: 1px solid #c3e6cb;
        margin: 1rem 0;
    }
    .warning-box {
        padding: 1rem;
        border-radius: 0.5rem;
        background-color: #fff3cd;
        border: 1px solid #ffeaa7;
        margin: 1rem 0;
    }
    .error-box {
        padding: 1rem;
        border-radius: 0.5rem;
        background-color: #f8d7da;
        border: 1px solid #f5c6cb;
        margin: 1rem 0;
    }
    .metric-card {
        background-color: #f8f9fa;
        padding: 1rem;
        border-radius: 0.5rem;
        border-left: 4px solid #1f77b4;
    }
</style>
""", unsafe_allow_html=True)

# Initialize session state
if 'orchestrator' not in st.session_state:
    st.session_state.orchestrator = None
if 'vector_store' not in st.session_state:
    st.session_state.vector_store = None
if 'last_result' not in st.session_state:
    st.session_state.last_result = None

def initialize_orchestrator():
    """Initialize the orchestrator if not already done."""
    if st.session_state.orchestrator is None:
        with st.spinner("Initializing MediGuard Orchestrator..."):
            try:
                # Check if langchain-ollama is available when using Ollama
                llm_provider = os.getenv("LLM_PROVIDER", "openai").lower()
                if llm_provider == "ollama":
                    try:
                        import langchain_ollama
                    except ImportError:
                        st.error("""
                        **langchain-ollama is not installed in this Python environment.**
                        
                        **To fix:**
                        1. Stop Streamlit (Ctrl+C)
                        2. Activate your virtual environment: `source venv/bin/activate`
                        3. Install: `pip install langchain-ollama`
                        4. Restart Streamlit: `streamlit run app.py`
                        
                        Or use the run script: `./run_ui.sh`
                        """)
                        return False
                
                st.session_state.orchestrator = MediGuardOrchestrator()
                return True
            except ImportError as e:
                error_msg = str(e)
                if "langchain-ollama" in error_msg or "langchain_ollama" in error_msg:
                    st.error("""
                    **langchain-ollama is not installed.**
                    
                    **Quick Fix:**
                    1. Stop Streamlit (press Ctrl+C in terminal)
                    2. Run: `source venv/bin/activate && pip install langchain-ollama`
                    3. Restart: `streamlit run app.py`
                    
                    Or use: `./run_ui.sh`
                    """)
                else:
                    st.error(f"Import error: {e}")
                return False
            except Exception as e:
                st.error(f"Error initializing orchestrator: {e}")
                st.code(f"Full error: {str(e)}", language="python")
                return False
    return True

def initialize_vector_store():
    """Initialize the vector store if not already done."""
    if st.session_state.vector_store is None:
        with st.spinner("Initializing vector store..."):
            try:
                st.session_state.vector_store = VectorStore()
                return True
            except Exception as e:
                st.warning(f"Vector store initialization warning: {e}")
                return True  # Continue even if vector store fails
    return True

# Header
st.markdown('<div class="main-header">🏥 MediGuard</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-header">Multi-Agent Clinical Compliance Orchestrator</div>', unsafe_allow_html=True)

# Sidebar
with st.sidebar:
    st.header("⚙️ Configuration")
    
    # LLM Provider info
    llm_provider = os.getenv("LLM_PROVIDER", "openai")
    st.info(f"**LLM Provider:** {llm_provider.upper()}")
    
    if llm_provider == "ollama":
        ollama_model = os.getenv("OLLAMA_MODEL", "llama3.2")
        st.info(f"**Model:** {ollama_model}")
    
    st.divider()
    
    # Initialize button
    if st.button("🔄 Initialize System", use_container_width=True):
        st.session_state.orchestrator = None
        st.session_state.vector_store = None
        if initialize_orchestrator():
            initialize_vector_store()
            st.success("✅ System initialized successfully!")
        else:
            st.error("❌ Failed to initialize system. Check error messages above.")
    
    st.divider()
    
    # Sample documents
    st.header("📄 Sample Documents")
    
    sample_claims = {
        "Sample Claim 1": "Patient: John Doe\nDOB: 03/15/1980\nTreatment: MRI scan of brain\nCost: $1,500.00\nInsurance: Standard Plan",
        "Sample Claim 2": "Patient: Jane Smith\nDOB: 07/22/1975\nTreatment: Physical therapy session\nCost: $250.00\nInsurance: Premium Plan",
        "Sample Claim with PHI": "Patient: John Doe\nDOB: 01/15/1980\nSSN: 123-45-6789\nPhone: 555-123-4567\nEmail: john.doe@email.com\nTreatment: MRI scan\nAmount: $1,500.00"
    }
    
    for name, text in sample_claims.items():
        if st.button(f"📋 {name}", use_container_width=True, key=f"sample_{name}"):
            st.session_state.sample_text = text
            st.rerun()

# Main content
tab1, tab2, tab3, tab4 = st.tabs(["📝 Document Processing", "📚 Policy Management", "👤 Human Review", "ℹ️ About"])

with tab1:
    # Processing mode selection
    processing_mode = st.radio(
        "Processing Mode:",
        ["Single Document", "Batch Processing"],
        horizontal=True
    )
    
    # Initialize if needed (but don't stop if it fails)
    init_success = initialize_orchestrator()
    
    if not init_success:
        st.warning("⚠️ System not initialized. Please click '🔄 Initialize System' in the sidebar first.")
    
    if processing_mode == "Single Document":
        st.header("Process Medical Document")
        
        # Input method selection
        input_method = st.radio(
            "Input Method:",
            ["Text Input", "File Upload"],
            horizontal=True
        )
        
        document_text = ""
        
        if input_method == "Text Input":
            # Use sample text if available
            default_text = st.session_state.get('sample_text', '')
            document_text = st.text_area(
                "Enter document text:",
                value=default_text,
                height=200,
                placeholder="Enter medical claim, patient report, or policy document text here..."
            )
        else:
            uploaded_file = st.file_uploader("Upload document file", type=['txt', 'json'])
            if uploaded_file:
                document_text = uploaded_file.read().decode('utf-8')
        
        # Document type selection (optional)
        doc_type = st.selectbox(
            "Document Type (optional - will be auto-detected if not specified):",
            ["Auto-detect", "CLAIM", "PATIENT_REPORT", "POLICY_UPDATE", "OTHER"]
        )
        
        document_type = None if doc_type == "Auto-detect" else doc_type
        
        # Process button - always show, but check if system is initialized
        if st.button("🚀 Process Document", type="primary", use_container_width=True):
            if not init_success or st.session_state.orchestrator is None:
                st.error("❌ System not initialized. Please click '🔄 Initialize System' in the sidebar first.")
            elif not document_text.strip():
                st.error("Please enter document text or upload a file.")
            else:
                with st.spinner("Processing document through MediGuard system..."):
                    try:
                        result = st.session_state.orchestrator.process_document(
                            document_text=document_text,
                            document_type=document_type
                        )
                        st.session_state.last_result = result
                        st.success("Document processed successfully!")
                    except Exception as e:
                        st.error(f"Error processing document: {e}")
                        st.exception(e)
        
        # Display results
        if st.session_state.last_result:
            result = st.session_state.last_result
            st.divider()
            st.header("📊 Results")
            
            # Classification
            if "classification" in result:
                classification = result["classification"]
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    st.metric(
                        "Document Type",
                        classification.get('document_type_label', 'N/A')
                    )
                with col2:
                    confidence = classification.get('confidence', 0)
                    st.metric(
                        "Confidence",
                        f"{confidence:.1%}"
                    )
                with col3:
                    st.metric(
                        "Agent",
                        classification.get('agent', 'N/A')
                    )
                
                if classification.get('reasoning'):
                    with st.expander("📝 Classification Reasoning"):
                        st.write(classification.get('reasoning'))
                
                if classification.get('extracted_metadata'):
                    with st.expander("🔍 Extracted Metadata"):
                        st.json(classification.get('extracted_metadata'))
            
            # Validation
            if "validation" in result and not result["validation"].get("skipped"):
                validation = result["validation"]
                st.divider()
                st.subheader("✅ Policy Validation")
                
                col1, col2, col3, col4 = st.columns(4)
                
                with col1:
                    is_covered = validation.get('is_covered', False)
                    st.metric(
                        "Coverage Status",
                        "✅ Covered" if is_covered else "❌ Not Covered"
                    )
                with col2:
                    coverage_pct = validation.get('coverage_percentage', 0)
                    st.metric(
                        "Coverage",
                        f"{coverage_pct}%"
                    )
                with col3:
                    copay = validation.get('copay_amount')
                    copay_display = f"${copay:.2f}" if copay is not None else "N/A"
                    st.metric(
                        "Co-pay",
                        copay_display
                    )
                with col4:
                    policies_consulted = validation.get('policies_consulted', 0)
                    st.metric(
                        "Policies Consulted",
                        policies_consulted
                    )
                
                if validation.get('reasoning'):
                    with st.expander("📝 Validation Reasoning"):
                        st.write(validation.get('reasoning'))
                
                if validation.get('policy_references'):
                    st.info(f"**Policy References:** {', '.join(validation.get('policy_references', []))}")
            
            # Compliance
            if "compliance" in result:
                compliance = result["compliance"]
                st.divider()
                st.subheader("🛡️ Compliance Audit")
                
                # PHI Check
                phi_check = compliance.get("phi_check", {})
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    phi_count = phi_check.get('total_phi_detections', 0)
                    st.metric(
                        "PHI Detections",
                        phi_count
                    )
                with col2:
                    risk_level = phi_check.get('risk_level', 'N/A')
                    risk_color = {
                        'LOW': '🟢',
                        'MEDIUM': '🟡',
                        'HIGH': '🔴'
                    }.get(risk_level, '⚪')
                    st.metric(
                        "Risk Level",
                        f"{risk_color} {risk_level}"
                    )
                with col3:
                    is_compliant = phi_check.get('is_compliant', True)
                    st.metric(
                        "Compliance",
                        "✅ Compliant" if is_compliant else "❌ Non-Compliant"
                    )
                
                if phi_check.get('detected_types'):
                    detected = phi_check.get('detected_types', {})
                    phi_types = [f"{k}: {v}" for k, v in detected.items() if v > 0]
                    if phi_types:
                        st.warning(f"**PHI Types Detected:** {', '.join(phi_types)}")
                
                if phi_check.get('recommendation'):
                    st.info(f"**Recommendation:** {phi_check.get('recommendation')}")
                
                # Bias Check
                bias_check = compliance.get("bias_check", {})
                st.divider()
                
                col1, col2 = st.columns(2)
                
                with col1:
                    has_bias = bias_check.get('has_bias', False)
                    st.metric(
                        "Bias Detected",
                        "⚠️ Yes" if has_bias else "✅ No"
                    )
                with col2:
                    severity = bias_check.get('bias_severity', 'N/A')
                    st.metric(
                        "Bias Severity",
                        severity
                    )
                
                if bias_check.get('bias_types'):
                    st.warning(f"**Bias Types:** {', '.join(bias_check.get('bias_types', []))}")
                
                if bias_check.get('evidence'):
                    with st.expander("🔍 Bias Analysis"):
                        st.write(bias_check.get('evidence'))
                
                if bias_check.get('recommendations'):
                    with st.expander("💡 Recommendations"):
                        for rec in bias_check.get('recommendations', []):
                            st.write(f"• {rec}")
            
            # Full JSON
            with st.expander("📄 Full JSON Response"):
                st.json(result)
            
            # Download results
            st.download_button(
                label="📥 Download Results (JSON)",
                data=json.dumps(result, indent=2),
                file_name="mediguard_result.json",
                mime="application/json"
            )
    
    else:  # Batch Processing
        st.header("Batch Process Multiple Documents")
        
        st.info("💡 Upload a JSON file with multiple documents or process all text files from a directory.")
        
        batch_input_method = st.radio(
            "Batch Input Method:",
            ["JSON File", "Directory of Text Files"],
            horizontal=True
        )
        
        documents = []
        
        if batch_input_method == "JSON File":
            uploaded_file = st.file_uploader(
                "Upload JSON file",
                type=["json"],
                help="JSON file should contain a list of documents, each with 'id' and 'text' fields. Optional: 'document_type' and 'patient_metadata'."
            )
            
            if uploaded_file:
                try:
                    data = json.load(uploaded_file)
                    if isinstance(data, list):
                        documents = data
                    elif isinstance(data, dict) and "documents" in data:
                        documents = data["documents"]
                    else:
                        st.error("❌ JSON file must contain a list of documents or a dict with 'documents' key")
                        documents = []
                    
                    if documents:
                        st.success(f"✅ Loaded {len(documents)} documents from JSON file")
                        with st.expander("📋 Preview Documents"):
                            for i, doc in enumerate(documents[:5], 1):
                                st.write(f"**Document {i}:** {doc.get('id', 'unknown')}")
                                st.text(doc.get('text', '')[:200] + "..." if len(doc.get('text', '')) > 200 else doc.get('text', ''))
                            if len(documents) > 5:
                                st.write(f"... and {len(documents) - 5} more documents")
                except json.JSONDecodeError as e:
                    st.error(f"❌ Invalid JSON format: {e}")
                except Exception as e:
                    st.error(f"❌ Error reading file: {e}")
        else:
            # Directory input
            directory_path = st.text_input(
                "Directory Path",
                placeholder="/path/to/documents",
                help="Enter the full path to a directory containing .txt files"
            )
            
            if directory_path:
                from pathlib import Path
                dir_path = Path(directory_path)
                
                if dir_path.exists() and dir_path.is_dir():
                    txt_files = list(dir_path.glob("*.txt"))
                    if txt_files:
                        st.success(f"✅ Found {len(txt_files)} text files in directory")
                        
                        # Load documents
                        documents = []
                        for file_path in txt_files:
                            try:
                                with open(file_path, "r") as f:
                                    doc_text = f.read()
                                    documents.append({
                                        "id": file_path.stem,
                                        "text": doc_text
                                    })
                            except Exception as e:
                                st.warning(f"⚠️ Failed to read {file_path.name}: {e}")
                        
                        if documents:
                            with st.expander("📋 Preview Documents"):
                                for i, doc in enumerate(documents[:5], 1):
                                    st.write(f"**Document {i}:** {doc.get('id', 'unknown')}")
                                    st.text(doc.get('text', '')[:200] + "..." if len(doc.get('text', '')) > 200 else doc.get('text', ''))
                                if len(documents) > 5:
                                    st.write(f"... and {len(documents) - 5} more documents")
                    else:
                        st.warning("⚠️ No .txt files found in the specified directory")
                else:
                    st.error("❌ Invalid directory path")
        
        # Batch processing controls
        if documents:
            st.divider()
            
            col1, col2 = st.columns(2)
            with col1:
                max_workers = st.slider(
                    "Parallel Workers",
                    min_value=1,
                    max_value=10,
                    value=4,
                    help="Number of documents to process in parallel"
                )
            
            with col2:
                st.metric("Total Documents", len(documents))
            
            if st.button("🚀 Process Batch", type="primary", use_container_width=True):
                if st.session_state.orchestrator is None:
                    st.error("❌ Orchestrator not initialized. Please initialize the system first.")
                else:
                    # Process batch
                    progress_bar = st.progress(0)
                    status_text = st.empty()
                    
                    try:
                        status_text.text("Processing documents...")
                        batch_result = st.session_state.orchestrator.process_batch(
                            documents=documents,
                            max_workers=max_workers,
                            show_progress=False  # We'll use Streamlit's progress bar
                        )
                        
                        # Update progress
                        progress_bar.progress(1.0)
                        status_text.text("✅ Processing complete!")
                        
                        # Display summary
                        summary = batch_result["summary"]
                        st.success(f"✅ Batch processing complete!")
                        
                        col1, col2, col3, col4 = st.columns(4)
                        with col1:
                            st.metric("Total", summary["total"])
                        with col2:
                            st.metric("Successful", summary["successful"], delta=None)
                        with col3:
                            st.metric("Failed", summary["failed"], delta=None)
                        with col4:
                            st.metric("Success Rate", f"{summary['success_rate']:.1%}")
                        
                        # Show errors if any
                        if batch_result["errors"]:
                            st.warning(f"⚠️ {len(batch_result['errors'])} documents failed processing")
                            with st.expander("❌ Error Details"):
                                for error in batch_result["errors"][:10]:
                                    st.error(f"**{error.get('document_id', 'unknown')}:** {error.get('error', 'Unknown error')}")
                                if len(batch_result["errors"]) > 10:
                                    st.write(f"... and {len(batch_result['errors']) - 10} more errors")
                        
                        # Display results table
                        st.divider()
                        st.subheader("📊 Results")
                        
                        # Create a summary table
                        results_data = []
                        for result in batch_result["results"][:50]:  # Show first 50
                            doc_id = result.get("document_id", "unknown")
                            status = result.get("status", "unknown")
                            doc_type = result.get("classification", {}).get("document_type_label", "N/A")
                            is_covered = result.get("validation", {}).get("is_covered", False)
                            phi_count = result.get("compliance", {}).get("phi_check", {}).get("total_phi_detections", 0)
                            
                            results_data.append({
                                "ID": doc_id,
                                "Status": status,
                                "Type": doc_type,
                                "Covered": "✅" if is_covered else "❌",
                                "PHI Detected": phi_count
                            })
                        
                        if results_data:
                            import pandas as pd
                            df = pd.DataFrame(results_data)
                            st.dataframe(df, use_container_width=True)
                            
                            if len(batch_result["results"]) > 50:
                                st.info(f"Showing first 50 of {len(batch_result['results'])} results. Download full results below.")
                        
                        # Download results
                        st.download_button(
                            label="📥 Download Batch Results (JSON)",
                            data=json.dumps(batch_result, indent=2),
                            file_name=f"mediguard_batch_results_{summary['timestamp'].replace(':', '-')}.json",
                            mime="application/json",
                            use_container_width=True
                        )
                        
                    except Exception as e:
                        progress_bar.progress(0)
                        status_text.text("❌ Processing failed")
                        st.error(f"❌ Error during batch processing: {e}")
                        import traceback
                        with st.expander("🔍 Error Details"):
                            st.code(traceback.format_exc())

with tab2:
    st.header("Policy Management")
    
    if not initialize_vector_store():
        st.stop()
    
    st.subheader("Add Policy to Database")
    
    col1, col2 = st.columns(2)
    
    with col1:
        policy_id = st.text_input("Policy ID", placeholder="POL-001")
        policy_text = st.text_area("Policy Text", height=300, placeholder="Enter policy document text...")
    
    with col2:
        policy_metadata = st.text_area(
            "Policy Metadata (JSON)",
            height=300,
            placeholder='{"name": "Standard Plan", "type": "health_insurance"}'
        )
    
    if st.button("➕ Add Policy", type="primary"):
        if not policy_id or not policy_text:
            st.error("Policy ID and text are required.")
        else:
            try:
                metadata = {}
                if policy_metadata:
                    metadata = json.loads(policy_metadata)
                
                st.session_state.vector_store.add_policy(policy_id, policy_text, metadata)
                st.success(f"Policy {policy_id} added successfully!")
            except json.JSONDecodeError:
                st.error("Invalid JSON in metadata field.")
            except Exception as e:
                st.error(f"Error adding policy: {e}")
    
    st.divider()
    st.subheader("Search Policies")
    
    search_query = st.text_input("Search Query", placeholder="MRI scan coverage")
    top_k = st.slider("Number of Results", 1, 10, 5)
    
    if st.button("🔍 Search"):
        if search_query:
            try:
                results = st.session_state.vector_store.search_similar(search_query, top_k=top_k)
                
                if results:
                    st.success(f"Found {len(results)} results")
                    
                    for i, result in enumerate(results, 1):
                        with st.expander(f"Result {i}: {result.get('id', 'N/A')} (Score: {result.get('score', 0):.4f})"):
                            if result.get('metadata'):
                                st.json(result.get('metadata'))
                            if result.get('text'):
                                st.text(result.get('text')[:500] + "..." if len(result.get('text', '')) > 500 else result.get('text'))
                else:
                    st.info("No results found.")
            except Exception as e:
                st.error(f"Error searching: {e}")

with tab3:
    st.header("👤 Human-in-the-Loop Review")
    st.info("Review and validate documents that require human oversight.")
    
    # Initialize human loop queue
    if st.session_state.orchestrator and hasattr(st.session_state.orchestrator, 'human_loop_queue'):
        human_queue = st.session_state.orchestrator.human_loop_queue
        quarantine_manager = st.session_state.orchestrator.quarantine_manager
        
        # Tabs for different review queues
        review_tab1, review_tab2 = st.tabs(["📋 Review Queue", "🚫 Quarantine"])
        
        with review_tab1:
            st.subheader("Pending Reviews")
            
            # Filter options
            col1, col2 = st.columns(2)
            with col1:
                priority_filter = st.selectbox(
                    "Priority Filter",
                    ["All", "Critical", "High", "Normal", "Low"]
                )
            with col2:
                limit = st.slider("Number of Items", 1, 50, 10)
            
            # Get pending items
            priority = None if priority_filter == "All" else priority_filter.lower()
            pending_items = human_queue.get_pending_items(priority=priority, limit=limit)
            
            if not pending_items:
                st.success("✅ No pending reviews!")
            else:
                st.info(f"📊 {len(pending_items)} items pending review")
                
                for item in pending_items:
                    with st.expander(f"📄 {item['document_id']} - {item.get('priority', 'normal').upper()} - {item.get('reason', 'Review required')}"):
                        col1, col2 = st.columns([2, 1])
                        
                        with col1:
                            st.write("**Document Text:**")
                            st.text_area(
                                "Document",
                                value=item.get('document_text', ''),
                                height=200,
                                key=f"doc_{item['document_id']}",
                                disabled=True
                            )
                            
                            if item.get('processing_result'):
                                with st.expander("📊 Processing Result"):
                                    st.json(item['processing_result'])
                        
                        with col2:
                            st.write("**Review Actions:**")
                            
                            reviewer_name = st.text_input(
                                "Your Name/ID",
                                key=f"reviewer_{item['document_id']}",
                                placeholder="Enter reviewer name"
                            )
                            
                            review_notes = st.text_area(
                                "Review Notes",
                                key=f"notes_{item['document_id']}",
                                height=100,
                                placeholder="Add review notes..."
                            )
                            
                            col_approve, col_reject = st.columns(2)
                            
                            with col_approve:
                                if st.button("✅ Approve", key=f"approve_{item['document_id']}", use_container_width=True):
                                    if reviewer_name:
                                        if human_queue.approve(
                                            document_id=item['document_id'],
                                            reviewer=reviewer_name,
                                            notes=review_notes
                                        ):
                                            st.success("✅ Approved!")
                                            st.rerun()
                                        else:
                                            st.error("Failed to approve")
                                    else:
                                        st.warning("Please enter reviewer name")
                            
                            with col_reject:
                                if st.button("❌ Reject", key=f"reject_{item['document_id']}", use_container_width=True):
                                    if reviewer_name:
                                        corrections = st.text_area(
                                            "Corrections Needed",
                                            key=f"corrections_{item['document_id']}",
                                            placeholder="Describe corrections needed..."
                                        )
                                        if human_queue.reject(
                                            document_id=item['document_id'],
                                            reviewer=reviewer_name,
                                            notes=review_notes,
                                            corrections={"notes": corrections} if corrections else None
                                        ):
                                            st.success("❌ Rejected - requires correction")
                                            st.rerun()
                                        else:
                                            st.error("Failed to reject")
                                    else:
                                        st.warning("Please enter reviewer name")
        
        with review_tab2:
            st.subheader("Quarantined Records")
            
            # Get quarantined records
            quarantine_records = quarantine_manager.list_quarantine_records()
            
            if not quarantine_records:
                st.success("✅ No quarantined records!")
            else:
                st.info(f"🚫 {len(quarantine_records)} records in quarantine")
                
                for record in quarantine_records[:20]:  # Show first 20
                    with st.expander(f"🚫 {record['document_id']} - {record.get('status', 'pending').upper()} - {record.get('reason', 'Unknown')}"):
                        col1, col2 = st.columns([2, 1])
                        
                        with col1:
                            st.write("**Document Text:**")
                            st.text_area(
                                "Document",
                                value=record.get('document_text', ''),
                                height=200,
                                key=f"quarantine_doc_{record['document_id']}",
                                disabled=True
                            )
                            
                            if record.get('processing_result'):
                                with st.expander("📊 Processing Result"):
                                    st.json(record['processing_result'])
                            
                            if record.get('metadata'):
                                with st.expander("📋 Metadata"):
                                    st.json(record['metadata'])
                        
                        with col2:
                            st.write("**Status:** " + record.get('status', 'pending').upper())
                            st.write("**Quarantined:** " + record.get('quarantined_at', 'Unknown'))
                            
                            if record.get('status') == 'pending':
                                reviewer_name = st.text_input(
                                    "Your Name/ID",
                                    key=f"quarantine_reviewer_{record['document_id']}",
                                    placeholder="Enter reviewer name"
                                )
                                
                                review_notes = st.text_area(
                                    "Review Notes",
                                    key=f"quarantine_notes_{record['document_id']}",
                                    height=100
                                )
                                
                                if st.button("✅ Release from Quarantine", key=f"release_{record['document_id']}", use_container_width=True):
                                    if reviewer_name:
                                        if quarantine_manager.release_from_quarantine(
                                            document_id=record['document_id'],
                                            reviewer=reviewer_name,
                                            notes=review_notes
                                        ):
                                            st.success("✅ Released from quarantine!")
                                            st.rerun()
                                        else:
                                            st.error("Failed to release")
                                    else:
                                        st.warning("Please enter reviewer name")
    else:
        st.warning("⚠️ Pipeline routing not enabled. Enable it in orchestrator initialization.")

with tab4:
    st.header("About MediGuard")
    
    st.markdown("""
    ### 🏥 Multi-Agent Clinical Compliance Orchestrator
    
    MediGuard is an AI-powered system for automated medical claim validation and 
    clinical document compliance review using multi-agent AI.
    
    #### 🤖 Agents
    
    1. **Triage Agent** - Classifies incoming documents
    2. **Policy Validator** - Validates treatments against insurance policies using RAG
    3. **Compliance Auditor** - Detects PHI and bias
    
    #### 🛡️ Features
    
    - ✅ Document Classification
    - ✅ Policy Validation with RAG
    - ✅ PHI Detection & Redaction
    - ✅ Bias Detection
    - ✅ Compliance Auditing
    
    #### 🔧 Configuration
    
    - **LLM Provider:** Supports both OpenAI and Ollama (local Llama models)
    - **Vector Store:** Pinecone, Milvus, or in-memory
    - **Privacy:** Can run entirely locally with Ollama
    
    #### 📚 Documentation
    
    See `TESTING_GUIDE.md` and `QUICKSTART.md` for more information.
    """)
    
    # System info
    with st.expander("🔧 System Information"):
        st.json({
            "LLM Provider": os.getenv("LLM_PROVIDER", "openai"),
            "Ollama Model": os.getenv("OLLAMA_MODEL", "N/A"),
            "Ollama URL": os.getenv("OLLAMA_BASE_URL", "N/A"),
            "OpenAI Model": os.getenv("OPENAI_MODEL", "N/A"),
        })

if __name__ == "__main__":
    # Auto-initialize on first load
    if st.session_state.orchestrator is None:
        initialize_orchestrator()
        initialize_vector_store()
