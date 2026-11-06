"""Deterministic approaches and affordable contract buyouts for CPU clubs."""
from math import ceil

DEFAULTS=dict(approach_bps=2400,approach_gap=.5,approach_min_days=60,
              approach_cooldown_days=30,approach_fee_months=3,
              approach_fee_budget_bps=1000)

def buyout(appointment,today,days_remaining,policy):
 months=max(0,min(int(policy['approach_fee_months']),ceil(days_remaining/30)))
 return max(0,int(appointment['monthly_wage'])*months)

def willingness(coach,source,destination,salary,old_salary):
 prestige=destination['reputation']-source['reputation'];raise_ratio=salary/max(1,old_salary)-1
 return max(500,min(8500,round(3500+prestige*1500+max(-.5,min(.5,raise_ratio))*2500)))
