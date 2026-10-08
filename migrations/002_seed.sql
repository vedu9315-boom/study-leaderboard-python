INSERT INTO sessions (student, subject, day, seconds)
SELECT s.name, sub.subject, CURRENT_DATE - (g % 10),
       (1200 + (random()*5400))::int
FROM (VALUES ('Asha'),('Vikram'),('Priya'),('Rahul'),('Fatima')) AS s(name),
     (VALUES ('DBMS'),('Operating Systems'),('Networks')) AS sub(subject),
     generate_series(0, 4) AS g
ON CONFLICT DO NOTHING;
