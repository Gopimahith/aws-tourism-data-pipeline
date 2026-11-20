-- Athena DDL and analysis queries for the cleaned tourism visits table.
-- Replace YOUR_BUCKET with the bucket created by the SAM template.

CREATE DATABASE IF NOT EXISTS tourism;

CREATE EXTERNAL TABLE IF NOT EXISTS tourism.visits_clean (
  visit_id         string,
  user_id          string,
  attraction_id    string,
  attraction_type  string,
  country          string,
  visit_year       int,
  visit_month      int,
  visit_mode       string,
  rating           int
)
ROW FORMAT DELIMITED FIELDS TERMINATED BY ','
STORED AS TEXTFILE
LOCATION 's3://YOUR_BUCKET/clean/'
TBLPROPERTIES ('skip.header.line.count' = '1');

-- 1. Average rating and volume by attraction type
SELECT attraction_type,
       COUNT(*)                 AS visits,
       ROUND(AVG(rating), 2)    AS avg_rating
FROM tourism.visits_clean
GROUP BY attraction_type
ORDER BY avg_rating DESC;

-- 2. Seasonality: visits per month
SELECT visit_month, COUNT(*) AS visits
FROM tourism.visits_clean
GROUP BY visit_month
ORDER BY visit_month;

-- 3. Which visit mode rates attractions highest, per country (min 30 visits)
SELECT country, visit_mode,
       COUNT(*)              AS visits,
       ROUND(AVG(rating), 2) AS avg_rating
FROM tourism.visits_clean
GROUP BY country, visit_mode
HAVING COUNT(*) >= 30
ORDER BY country, avg_rating DESC;

-- 4. Low-rated attractions to review (avg rating below 3.5, at least 20 visits)
SELECT attraction_id, attraction_type,
       COUNT(*)              AS visits,
       ROUND(AVG(rating), 2) AS avg_rating
FROM tourism.visits_clean
GROUP BY attraction_id, attraction_type
HAVING COUNT(*) >= 20 AND AVG(rating) < 3.5
ORDER BY avg_rating;
