# api_v1/tasks.py
import time
import logging
from celery import shared_task
from .models import Execution, Plan

logger = logging.getLogger(__name__)

@shared_task
def execute_plan_task(execution_id):
    """Simulate on-chain execution of a plan.
    
    In production, this will use the Relayer private key to sign and send transactions.
    """
    logger.info(f"Starting execution for ID: {execution_id}")
    
    try:
        execution = Execution.objects.get(id=execution_id)
        
        # 1. Simulate "Submitting to Mempool"
        execution.status = Execution.Status.SUBMITTED
        execution.save()
        logger.info(f"[Task] Execution {execution_id} status: SUBMITTED")
        
        # Simulate network latency (2 seconds for BlockDAG speed!)
        time.sleep(2) 
        
        # 2. Simulate "Transaction Confirmed"
        # We generate a fake hash for the demo
        fake_tx_hash = f"0x{execution.id.hex}123456789"
        
        execution.tx_hash = fake_tx_hash
        execution.status = Execution.Status.CONFIRMED
        
        # Create a mock receipt
        execution.receipt = {
            "blockNumber": 12345,
            "gasUsed": 21000,
            "status": 1,
            "logs": ["Transfer", "Stake", "IntentExecuted"]
        }
        execution.save()
        
        # Update the parent Plan status too
        execution.plan.status = Plan.Status.EXECUTED
        execution.plan.save()
        
        logger.info(f"Execution {execution_id} completed. Hash: {fake_tx_hash}")
        
    except Execution.DoesNotExist:
        logger.error(f"Execution {execution_id} not found")
    except Exception as e:
        logger.error(f"Execution failed: {e}")
        if 'execution' in locals():
            execution.status = Execution.Status.FAILED
            execution.save()