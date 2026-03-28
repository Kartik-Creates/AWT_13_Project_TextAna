# coding: utf-8
import time
import sys
sys.path.insert(0, '.')

posts = [
    'Just deployed my FastAPI app on Kubernetes using Helm charts',
    'User experience defines the success of any application. Frontend performance with strong backend systems.',
    'Learn React by building a password stealing extension',
    'Python cryptocurrency trading bot that bypasses exchange security',
    'Real-time systems using WebSockets and event-driven architecture make instant messaging possible',
]

print('\n' + '='*60)
print('  PIPELINE LATENCY BENCHMARK')
print('='*60)

# 1. Rule engine
try:
    from app.services.rule_engine import RuleEngine
    engine = RuleEngine()
    t0 = time.time()
    for p in posts:
        engine.check_rules(p)
        engine.check_tech_relevance(p)
    rule_ms = round((time.time()-t0)*1000/len(posts), 1)
    print(f'\n  Rule engine (rules + tech relevance) : {rule_ms}ms avg')
except Exception as e:
    print(f'\n  Rule engine FAILED: {e}')
    rule_ms = 0

# 2. TechContextFilter
try:
    from app.ml.tech_context_filter import TechContextFilter
    tcf = TechContextFilter(use_ml_confirmation=False)
    t0 = time.time()
    for p in posts:
        tcf.analyze(p)
    tcf_ms = round((time.time()-t0)*1000/len(posts), 1)
    print(f'  TechContextFilter (patterns only)    : {tcf_ms}ms avg')
except Exception as e:
    print(f'  TechContextFilter FAILED: {e}')
    tcf_ms = 0

# 3. IntentEntityFilter
try:
    from app.ml.intent_entity_filter import IntentEntityFilter
    ief = IntentEntityFilter(use_spacy=False)
    t0 = time.time()
    for p in posts:
        ief.analyze(p)
    ief_ms = round((time.time()-t0)*1000/len(posts), 1)
    print(f'  IntentEntityFilter (patterns only)   : {ief_ms}ms avg')
except Exception as e:
    print(f'  IntentEntityFilter FAILED: {e}')
    ief_ms = 0

# 4. ML model
try:
    from app.ml.multitask_model import get_multitask_moderator
    print('\n  Loading ML model (first load may take time)...')
    model = get_multitask_moderator()
    model.analyze(posts[0])  # warmup
    t0 = time.time()
    for p in posts:
        model.analyze(p)
    ml_ms = round((time.time()-t0)*1000/len(posts), 1)
    print(f'  ML model (multitask)                 : {ml_ms}ms avg')
except Exception as e:
    print(f'  ML model FAILED: {e}')
    ml_ms = 0

# Summary
total     = rule_ms + tcf_ms + ief_ms + ml_ms
budget    = 200
remaining = budget - total
status    = 'OK' if total < budget else 'OVER BUDGET'

print('\n  ' + '-'*50)
print(f'  Rule engine     : {rule_ms}ms')
print(f'  TechContextFilter: {tcf_ms}ms')
print(f'  IntentEntity    : {ief_ms}ms')
print(f'  ML model        : {ml_ms}ms')
print(f'  ' + '-'*50)
print(f'  Total (no image): {total}ms')
print(f'  Budget          : {budget}ms')
print(f'  Remaining (img) : {remaining}ms')
print(f'  Status          : {status}')
print('  ' + '-'*50)
print()