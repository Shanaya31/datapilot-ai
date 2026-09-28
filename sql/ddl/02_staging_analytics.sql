CREATE TABLE IF NOT EXISTS `${project}.staging.orders` (
  order_id STRING, customer_id STRING, product_id STRING, order_ts TIMESTAMP,
  quantity INT64, amount FLOAT64, status STRING, _batch_date DATE
) PARTITION BY _batch_date;

CREATE TABLE IF NOT EXISTS `${project}.staging.inventory` (
  product_id STRING, warehouse_id STRING, stock_level INT64, reorder_level INT64,
  snapshot_ts TIMESTAMP, _batch_date DATE
) PARTITION BY _batch_date;

CREATE TABLE IF NOT EXISTS `${project}.staging.customers` (
  customer_id STRING, name STRING, email STRING, country STRING, signup_ts TIMESTAMP,
  segment STRING, _batch_date DATE
) PARTITION BY _batch_date;

CREATE TABLE IF NOT EXISTS `${project}.analytics.orders_daily` (
  batch_date DATE, orders INT64, gross_revenue FLOAT64, distinct_customers INT64, cancelled_orders INT64
);

CREATE TABLE IF NOT EXISTS `${project}.analytics.inventory_daily` (
  batch_date DATE, sku_warehouse_pairs INT64, below_reorder_level INT64, total_units INT64
);

CREATE TABLE IF NOT EXISTS `${project}.analytics.customers_by_country` (
  batch_date DATE, country STRING, customers INT64
);
