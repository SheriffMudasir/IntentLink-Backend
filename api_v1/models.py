# api_v1/models.py
import uuid
from django.db import models

class Intent(models.Model):
    class Status(models.TextChoices):
        PARSED = 'parsed', 'Parsed'
        PLANNED = 'planned', 'Planned'
        SIMULATED = 'simulated', 'Simulated'
        SIGNED = 'signed', 'Signed'
        EXECUTING = 'executing', 'Executing'
        COMPLETED = 'completed', 'Completed'
        FAILED = 'failed', 'Failed'
        CLARIFY = 'clarify', 'Clarify'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user_wallet = models.CharField(max_length=42)
    chain_id = models.IntegerField(default=1043)
    input_text = models.TextField(blank=True, null=True)
    intent_json = models.JSONField()
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PARSED)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Intent {self.id} for {self.user_wallet}"


class Plan(models.Model):
    class Status(models.TextChoices):
        READY = 'ready', 'Ready'
        SIMULATED = 'simulated', 'Simulated'
        APPROVED = 'approved', 'Approved'
        EXECUTED = 'executed', 'Executed'
        FAILED = 'failed', 'Failed'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    intent = models.ForeignKey(Intent, on_delete=models.CASCADE, related_name='plans')
    plan_json = models.JSONField()
    utility_scores = models.JSONField(blank=True, null=True)
    chosen_contract_address = models.CharField(max_length=42, blank=True, null=True)
    simulation_result = models.JSONField(blank=True, null=True)
    ipfs_cid = models.CharField(max_length=255, blank=True, null=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.READY)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Plan {self.id} for Intent {self.intent_id}"


class Execution(models.Model):
    class Status(models.TextChoices):
        PENDING = 'pending', 'Pending'
        SUBMITTED = 'submitted', 'Submitted'
        CONFIRMED = 'confirmed', 'Confirmed'
        FAILED = 'failed', 'Failed'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    plan = models.OneToOneField(Plan, on_delete=models.CASCADE, related_name='execution')
    tx_hash = models.CharField(max_length=66, blank=True, null=True, unique=True)
    relayer_address = models.CharField(max_length=42, blank=True, null=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    receipt = models.JSONField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Execution {self.id} for Plan {self.plan_id}"