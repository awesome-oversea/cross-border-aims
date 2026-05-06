import sys
sys.path.insert(0, 'skills/skill-gate')
from main import SkillGate

gate = SkillGate()

r1 = gate.evaluate('listing_gen', 'ecommerce', 0.95)
print('Test1 Low:', r1['level'], r1['action'], r1['allowed'])

r2 = gate.evaluate('ad_adjust_price', 'ecommerce', 0.85)
print('Test2 Medium:', r2['level'], r2['action'], r2['allowed'])

r3 = gate.evaluate('refund', 'ecommerce', 0.55)
print('Test3 High:', r3['level'], r3['action'], r3['allowed'])

gate.register('ad_adjust_price', 'ecommerce', 'medium', [{'field': 'price_change_pct', 'operator': '>', 'value': 20, 'level': 'high'}], 'ad condition')
r4 = gate.evaluate('ad_adjust_price', 'ecommerce', 0.85, {'price_change_pct': 25})
print('Test4 Condition:', r4['level'], r4['action'], r4['allowed'])

r5 = gate.approve(r3['gate_id'], 'admin', 'ok')
print('Test5 Approve:', r5['success'], r5['status'])

stats = gate.get_stats()
print('Test6 Stats:', stats['total_records'], stats['total_rules'], stats['pending_approvals'])

pending = gate.list_pending()
print('Test7 Pending:', pending['total'])

r8 = gate.evaluate('negative_sentiment', 'cs', 0.3)
print('Test8 CS:', r8['level'], r8['action'], r8['allowed'])

r9 = gate.reject('gate-nonexist', 'admin', 'no')
print('Test9 Reject nonexist:', r9['success'])

print('\nAll tests passed!')
