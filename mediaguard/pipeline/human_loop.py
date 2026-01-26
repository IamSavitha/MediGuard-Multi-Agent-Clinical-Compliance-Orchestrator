"""
Human-in-the-Loop Queue

Manages documents requiring human review and validation.
"""

from typing import Dict, Any, List, Optional
from pathlib import Path
import json
from datetime import datetime
from enum import Enum


class ReviewStatus(str, Enum):
    """Status of human review items."""
    PENDING = "pending"
    IN_REVIEW = "in_review"
    APPROVED = "approved"
    REJECTED = "rejected"
    NEEDS_CORRECTION = "needs_correction"
    RESOLVED = "resolved"


class HumanInTheLoopQueue:
    """Manages human-in-the-loop review queue."""
    
    def __init__(self, queue_dir: str = "data/human_review"):
        """Initialize human review queue.
        
        Args:
            queue_dir: Directory for storing review queue items
        """
        self.queue_dir = Path(queue_dir)
        self.queue_dir.mkdir(parents=True, exist_ok=True)
    
    def add_to_queue(
        self,
        document_id: str,
        document_text: str,
        reason: str,
        processing_result: Dict[str, Any],
        priority: str = "normal"
    ) -> Dict[str, Any]:
        """Add document to human review queue.
        
        Args:
            document_id: Document identifier
            document_text: Document text
            reason: Reason for human review
            processing_result: Processing result
            priority: Priority level (low, normal, high, critical)
            
        Returns:
            Review queue item
        """
        queue_item = {
            "document_id": document_id,
            "document_text": document_text,
            "reason": reason,
            "status": ReviewStatus.PENDING.value,
            "priority": priority,
            "added_at": datetime.now().isoformat(),
            "processing_result": processing_result
        }
        
        # Save to queue
        queue_file = self.queue_dir / f"{document_id}.json"
        with open(queue_file, "w") as f:
            json.dump(queue_item, f, indent=2)
        
        return queue_item
    
    def get_pending_items(
        self,
        priority: Optional[str] = None,
        limit: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """Get pending review items.
        
        Args:
            priority: Optional priority filter
            limit: Optional limit on number of items
            
        Returns:
            List of pending review items
        """
        items = []
        for file_path in self.queue_dir.glob("*.json"):
            try:
                with open(file_path, "r") as f:
                    item = json.load(f)
                    if item.get("status") == ReviewStatus.PENDING.value:
                        if priority is None or item.get("priority") == priority:
                            items.append(item)
            except Exception:
                continue
        
        # Sort by priority and date
        priority_order = {"critical": 0, "high": 1, "normal": 2, "low": 3}
        items.sort(key=lambda x: (
            priority_order.get(x.get("priority", "normal"), 3),
            x.get("added_at", "")
        ))
        
        if limit:
            items = items[:limit]
        
        return items
    
    def get_item(self, document_id: str) -> Optional[Dict[str, Any]]:
        """Get a review queue item by ID.
        
        Args:
            document_id: Document identifier
            
        Returns:
            Review queue item or None
        """
        queue_file = self.queue_dir / f"{document_id}.json"
        if queue_file.exists():
            with open(queue_file, "r") as f:
                return json.load(f)
        return None
    
    def update_review(
        self,
        document_id: str,
        status: ReviewStatus,
        reviewer: str,
        notes: Optional[str] = None,
        corrections: Optional[Dict[str, Any]] = None
    ) -> bool:
        """Update review status.
        
        Args:
            document_id: Document identifier
            status: New review status
            reviewer: Reviewer name/ID
            notes: Review notes
            corrections: Corrected data
            
        Returns:
            True if updated successfully
        """
        item = self.get_item(document_id)
        if not item:
            return False
        
        item["status"] = status.value
        item["reviewer"] = reviewer
        item["reviewed_at"] = datetime.now().isoformat()
        
        if notes:
            item["review_notes"] = notes
        
        if corrections:
            item["corrections"] = corrections
        
        # Save updated item
        queue_file = self.queue_dir / f"{document_id}.json"
        with open(queue_file, "w") as f:
            json.dump(item, f, indent=2)
        
        return True
    
    def approve(
        self,
        document_id: str,
        reviewer: str,
        notes: Optional[str] = None
    ) -> bool:
        """Approve a document after review.
        
        Args:
            document_id: Document identifier
            reviewer: Reviewer name/ID
            notes: Approval notes
            
        Returns:
            True if approved successfully
        """
        return self.update_review(
            document_id=document_id,
            status=ReviewStatus.APPROVED,
            reviewer=reviewer,
            notes=notes
        )
    
    def reject(
        self,
        document_id: str,
        reviewer: str,
        notes: Optional[str] = None,
        corrections: Optional[Dict[str, Any]] = None
    ) -> bool:
        """Reject a document and request corrections.
        
        Args:
            document_id: Document identifier
            reviewer: Reviewer name/ID
            notes: Rejection notes
            corrections: Suggested corrections
            
        Returns:
            True if rejected successfully
        """
        return self.update_review(
            document_id=document_id,
            status=ReviewStatus.NEEDS_CORRECTION,
            reviewer=reviewer,
            notes=notes,
            corrections=corrections
        )
