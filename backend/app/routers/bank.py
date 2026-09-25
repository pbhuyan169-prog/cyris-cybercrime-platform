from fastapi import APIRouter, HTTPException, Depends
from typing import Dict, Any
from backend.app.schemas import TransactionResponse
from backend.app.services.bank_service import get_bank_transaction_details

router = APIRouter(prefix="/api/transactions", tags=["Bank Module"])

@router.get("/{transaction_id}", response_model=TransactionResponse)
def get_transaction_info(transaction_id: str):
    tx_data = get_bank_transaction_details(transaction_id)
    if not tx_data:
        raise HTTPException(status_code=404, detail="Transaction ID not found in bank records")
    return tx_data
