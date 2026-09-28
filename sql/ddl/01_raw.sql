CREATE TABLE IF NOT EXISTS `${project}.raw.orders` (
  order_id STRING, customer_id STRING, product_id STRING, order_ts TIMESTAMP,
  quantity INT64, amount FLOAT64, status STRING,
  _batch_date DATE, _run_id STRING, _ingested_at TIMESTAMP
) PARTITION BY _batch_date;

CREATE TABLE IF NOT EXISTS `${project}.raw.inventory` (
  product_id STRING, warehouse_id STRING, stock_level INT64, reorder_level INT64, snapshot_ts TIMESTAMP,
  _batch_date DATE, _run_id STRING, _ingested_at TIMESTAMP
) PARTITION BY _batch_date;

CREATE TABLE IF NOT EXISTS `${project}.raw.customers` (
  customer_id STRING, name STRING, email STRING, country STRING, signup_ts TIMESTAMP, segment STRING,
  _batch_date DATE, _run_id STRING, _ingested_at TIMESTAMP
) PARTITION BY _batch_date;
