-- Day-grain time spine required by MetricFlow. DuckDB syntax; swap for dbt_utils.date_spine on other warehouses.
select cast(range as date) as date_day
from range(date '2000-01-01', date '2036-01-01', interval 1 day)
