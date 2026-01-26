"""
Quarantine Manager

Manages quarantined records that require human review or correction.
"""

from typing import Dict, Any, List, Optional
from pathlib import Path
import json
from datetime import datetime
from enum import Enum


class QuarantineStatus(str, Enum):
    """Status of quarantined records."""
    PENDING = "pending"
    UNDER_REVIEW = "under_review"
    APPROVED = "approved"
    REJECTED = "rejected"
    FIXED = "fixed"
    RESOLVED = "resolved"


class QuarantineManager:
    """Manages quarantined records."""
    
    def __init__(self, quarantine_dir: str = "data/quarantine"):
        """Initialize quarantine manager.
        
        Args:
            quarantine_dir: Directory for storing quarantine records
        """
        self.quarantine_dir = Path(quarantine_dir)
        self.quarantine_dir.mkdir(parents=True, exist_ok=True)
        
        self.status_dir = self.quarantine_dir / "status"
        self.status_dir.mkdir(exist_ok=True)
    
    def add_to_quarantine(
        self,
        document_id: str,
        document_text: str,
        reason: str,
        metadata: Optional[Dict[str, Any]] = None,
        processing_result: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Add a record to quarantine.
        
        Args:
            document_id: Document identifier
            document_text: Document text
            reason: Reason for quarantine
            metadata: Additional metadata
            processing_result: Processing result if available
            
        Returns:
            Quarantine record
        """
        record = {
            "document_id": document_id,
            "document_text": document_text,
            "reason": reason,
            "status": QuarantineStatus.PENDING.value,
            "quarantined_at": datetime.now().isoformat(),
            "metadata": metadata or {},
            "processing_result": processing_result
        }
        
        # Save record
        record_file = self.quarantine_dir / f"{document_id}.json"
        with open(record_file, "w") as f:
            json.dump(record, f, indent=2)
        
        return record
    
    def get_quarantine_record(self, document_id: str) -> Optional[Dict[str, Any]]:
        """Get a quarantine record by ID.
        
        Args:
            document_id: Document identifier
            
        Returns:
            Quarantine record or None
        """
        record_file = self.quarantine_dir / f"{document_id}.json"
        if record_file.exists():
            with open(record_file, "r") as f:
                return json.load(f)
        return None
    
    def update_status(
        self,
        document_id: str,
        status: QuarantineStatus,
        reviewer: Optional[str] = None,
        notes: Optional[str] = None,
        fixed_data: Optional[Dict[str, Any]] = None
    ) -> bool:
        """Update quarantine record status.
        
        Args:
            document_id: Document identifier
            status: New status
            reviewer: Reviewer name/ID
            notes: Review notes
            fixed_data: Fixed/corrected data
            
        Returns:
            True if updated successfully
        """
        record = self.get_quarantine_record(document_id)
        if not record:
            return False
        
        record["status"] = status.value
        record["updated_at"] = datetime.now().isoformat()
        
        if reviewer:
            record["reviewer"] = reviewer
        
        if notes:
            record["review_notes"] = notes
        
        if fixed_data:
            record["fixed_data"] = fixed_data
        
        # Save updated record
        record_file = self.quarantine_dir / f"{document_id}.json"
        with open(record_file, "w") as f:
            json.dump(record, f, indent=2)
        
        return True
    
    def list_quarantine_records(
        self,
        status: Optional[QuarantineStatus] = None
    ) -> List[Dict[str, Any]]:
        """List all quarantine records, optionally filtered by status.
        
        Args:
            status: Optional status filter
            
        Returns:
            List of quarantine records
        """
        records = []
        for file_path in self.quarantine_dir.glob("*.json"):
            if file_path.name == "status":
                continue
            try:
                with open(file_path, "r") as f:
                    record = json.load(f)
                    if status is None or record.get("status") == status.value:
                        records.append(record)
            except Exception:
                continue
        
        # Sort by quarantine date (newest first)
        records.sort(key=lambda x: x.get("quarantined_at", ""), reverse=True)
        return records
    
    def release_from_quarantine(
        self,
        document_id: str,
        reviewer: str,
        notes: Optional[str] = None
    ) -> bool:
        """Release a record from quarantine after human review.
        
        Args:
            document_id: Document identifier
            reviewer: Reviewer name/ID
            notes: Release notes
            
        Returns:
            True if released successfully
        """
        return self.update_status(
            document_id=document_id,
            status=QuarantineStatus.RESOLVED,
            reviewer=reviewer,
            notes=notes
        )
