USE restaurant_db;

INSERT INTO restaurant_tables (table_number, capacity)
VALUES
    (1, 2),
    (2, 2),
    (3, 4),
    (4, 4),
    (5, 6),
    (6, 8);

INSERT INTO time_slots (start_time, end_time)
VALUES
    ('17:00:00', '18:30:00'),
    ('18:30:00', '20:00:00'),
    ('20:00:00', '21:30:00');