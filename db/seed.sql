-- Teachers (3, across 2 departments; teacher 3 has no offerings — intentional)
INSERT INTO teachers VALUES
    (1, 'Dr. Alice Nguyen',  'Computer Science'),
    (2, 'Prof. Bob Carter',  'Mathematics'),
    (3, 'Dr. Carol Diaz',    'Computer Science');

-- Students (15, across 3 enrollment years)
INSERT INTO students VALUES
    (1,  'Emma Wilson',    2022),
    (2,  'Liam Johnson',   2022),
    (3,  'Olivia Brown',   2022),
    (4,  'Noah Davis',     2022),
    (5,  'Ava Martinez',   2022),
    (6,  'Ethan Garcia',   2023),
    (7,  'Sophia Anderson',2023),
    (8,  'Mason Thomas',   2023),
    (9,  'Isabella Taylor',2023),
    (10, 'James Jackson',  2023),
    (11, 'Mia White',      2024),
    (12, 'Oliver Harris',  2024),
    (13, 'Charlotte Lewis',2024),
    (14, 'Elijah Clark',   2024),
    (15, 'Amelia Robinson',2024);

-- Courses (5; course 5 has no offerings — intentional)
INSERT INTO courses VALUES
    (1, 'CS101: Intro to Programming', 3),
    (2, 'MA201: Calculus I',           4),
    (3, 'CS301: Data Structures',      3),
    (4, 'MA301: Linear Algebra',       3),
    (5, 'CS401: Operating Systems',    3);

-- Course offerings (12, spanning 2 semesters)
-- CS101 offered in both semesters by different teachers
-- MA201 offered in both semesters by same teacher (different offering rows)
INSERT INTO course_offerings VALUES
    (1,  1, 1, '2024-Fall'),    -- CS101 by Nguyen, Fall 2024
    (2,  2, 2, '2024-Fall'),    -- MA201 by Carter, Fall 2024
    (3,  3, 1, '2024-Fall'),    -- CS301 by Nguyen, Fall 2024
    (4,  4, 2, '2024-Fall'),    -- MA301 by Carter, Fall 2024
    (5,  1, 2, '2025-Spring'),  -- CS101 by Carter, Spring 2025 (same course, different teacher)
    (6,  2, 2, '2025-Spring'),  -- MA201 by Carter, Spring 2025
    (7,  3, 1, '2025-Spring'),  -- CS301 by Nguyen, Spring 2025
    (8,  4, 2, '2025-Spring'),  -- MA301 by Carter, Spring 2025
    (9,  1, 1, '2025-Spring'),  -- CS101 by Nguyen, Spring 2025 (Nguyen teaches CS101 again)
    (10, 2, 1, '2024-Fall'),    -- MA201 by Nguyen, Fall 2024
    (11, 3, 2, '2024-Fall'),    -- CS301 by Carter, Fall 2024
    (12, 4, 1, '2025-Spring');  -- MA301 by Nguyen, Spring 2025

-- Enrollments (65 total; mean ~75, stddev ~12; some NULLs; tricky edge cases)
-- Tricky: student 1 enrolled in CS101 in BOTH semesters (offerings 1 and 5)
-- Tricky: some grades are NULL (not yet graded)
INSERT INTO enrollments VALUES
    -- offering 1: CS101 Fall 2024 (Nguyen) — students 1-8
    (1,  1,  1, 88.0),
    (2,  2,  1, 74.5),
    (3,  3,  1, 91.0),
    (4,  4,  1, 63.0),
    (5,  5,  1, 77.5),
    (6,  6,  1, 55.0),
    (7,  7,  1, 82.0),
    (8,  8,  1, 70.0),

    -- offering 2: MA201 Fall 2024 (Carter) — students 2-7
    (9,  2,  2, 68.0),
    (10, 3,  2, 85.5),
    (11, 4,  2, 72.0),
    (12, 5,  2, 90.0),
    (13, 6,  2, 61.5),
    (14, 7,  2, 78.0),

    -- offering 3: CS301 Fall 2024 (Nguyen) — students 1-5
    (15, 1,  3, 95.0),
    (16, 2,  3, 80.0),
    (17, 3,  3, 67.5),
    (18, 4,  3, 73.0),
    (19, 5,  3, 88.5),

    -- offering 4: MA301 Fall 2024 (Carter) — students 3-7
    (20, 3,  4, 79.0),
    (21, 4,  4, 65.0),
    (22, 5,  4, 84.0),
    (23, 6,  4, 71.5),
    (24, 7,  4, 92.0),

    -- offering 5: CS101 Spring 2025 (Carter) — students 1,9-13
    -- student 1 re-enrolls in CS101 (different semester/offering — intentional edge case)
    (25, 1,  5, 76.0),
    (26, 9,  5, 83.0),
    (27, 10, 5, 58.5),
    (28, 11, 5, 94.0),
    (29, 12, 5, 69.5),
    (30, 13, 5, 77.0),

    -- offering 6: MA201 Spring 2025 (Carter) — students 8-12
    (31, 8,  6, 86.0),
    (32, 9,  6, 64.0),
    (33, 10, 6, 75.5),
    (34, 11, 6, 89.0),
    (35, 12, 6, NULL),  -- not yet graded

    -- offering 7: CS301 Spring 2025 (Nguyen) — students 6-10
    (36, 6,  7, 71.0),
    (37, 7,  7, 88.0),
    (38, 8,  7, 60.5),
    (39, 9,  7, 79.0),
    (40, 10, 7, NULL),  -- not yet graded

    -- offering 8: MA301 Spring 2025 (Carter) — students 11-15
    (41, 11, 8, 73.0),
    (42, 12, 8, 81.5),
    (43, 13, 8, 66.0),
    (44, 14, 8, 90.5),
    (45, 15, 8, 55.5),

    -- offering 9: CS101 Spring 2025 (Nguyen) — students 13-15
    (46, 13, 9, 84.0),
    (47, 14, 9, 72.5),
    (48, 15, 9, 68.0),

    -- offering 10: MA201 Fall 2024 (Nguyen) — students 9-13
    (49, 9,  10, 76.5),
    (50, 10, 10, 85.0),
    (51, 11, 10, 62.0),
    (52, 12, 10, 91.5),
    (53, 13, 10, 70.0),

    -- offering 11: CS301 Fall 2024 (Carter) — students 8-12
    (54, 8,  11, 78.0),
    (55, 9,  11, 66.5),
    (56, 10, 11, 83.0),
    (57, 11, 11, 57.0),
    (58, 12, 11, 74.5),

    -- offering 12: MA301 Spring 2025 (Nguyen) — students 1-4
    (59, 1,  12, 88.0),
    (60, 2,  12, 75.0),
    (61, 3,  12, NULL),  -- not yet graded
    (62, 4,  12, 69.5),

    -- extra enrollments to reach 65
    (63, 14, 2,  81.0),
    (64, 15, 4,  77.5),
    (65, 5,  7,  92.5);
