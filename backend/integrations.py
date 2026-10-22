"""Capability boundaries: no browser/session scraping and no credential collection."""
import os
import base64
from pathlib import Path
import httpx

def capabilities():
    return dict(session_capture=False, attempt_tracking=False, manual_submission=True,
                evaluator_configured=bool(os.getenv('EVALUATOR_URL')),
                reason='Session capture has not been verified in this browser. Use your own ChatGPT account and upload your selected result. Generation attempts cannot be independently counted.')

def evaluate(submission, task, asset, storage):
    endpoint = os.getenv('EVALUATOR_URL')
    if not endpoint:
        return 'unavailable', dict(message='No authorized vision evaluator configured. Score this submission using the rubric.')
    if not endpoint.startswith('https://'):
        return 'failed', dict(message='Evaluator must use HTTPS.')
    try:
        payload = dict(submission_id=submission.id, revision=submission.revision, round=task.round,
                       prompt=submission.prompt, rationale=submission.rationale, brief=task.brief,
                       rubric=task.rubric, image_base64=base64.b64encode(storage.read(asset.id)).decode(), mime=asset.mime)
        if task.reference_id:
            payload['reference_base64'] = base64.b64encode(storage.read(task.reference_id)).decode()
        response = httpx.post(endpoint, json=payload, headers={'Authorization': 'Bearer ' + os.getenv('EVALUATOR_SECRET', '')}, timeout=25, follow_redirects=False)
        response.raise_for_status()
        result = response.json()
        scores = result.get('scores', [])
        if len(scores) != len(task.rubric) or any(isinstance(v, bool) or not isinstance(v, (int, float)) or not 0 <= v <= 100 for v in scores):
            raise ValueError('Invalid criterion scores')
        if not isinstance(result.get('explanations'), list) or len(result['explanations']) != len(scores) or not all(isinstance(v, str) and len(v) <= 4000 for v in result['explanations']):
            raise ValueError('Missing criterion explanations')
        return 'evaluated', dict(scores=scores, explanations=result['explanations'])
    except Exception:
        return 'failed', dict(message='The evaluator did not return a valid response. Your submission is preserved; retry or use manual review.')
