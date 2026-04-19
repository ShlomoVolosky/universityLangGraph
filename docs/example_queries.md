# Example Queries

Ten representative questions with their generated SQL and real answers, organized by complexity.
All outputs are from a live run against `db/university.db` using `claude-sonnet-4-6`.

---

## Single-table queries

### 1. Student count

**Question:** How many students are there?

**Generated SQL:**
```sql
SELECT COUNT(*) FROM students;
```

**Answer:** There are **15 students** in total.

---

### 2. Course with the most credits

**Question:** Which course has the most credits?

**Generated SQL:**
```sql
SELECT title, credits FROM courses ORDER BY credits DESC LIMIT 1
```

**Answer:** Based on the query results, **MA201: Calculus I** has the most credits, with **4 credits**.

---

### 3. Students enrolled in a specific year

**Question:** List all students who enrolled in 2023 and their enrollment year.

**Generated SQL:**
```sql
SELECT id, name, enrollment_year
FROM students
WHERE enrollment_year = 2023
```

**Answer:** A total of **5 students** enrolled in 2023: Ethan Garcia, Sophia Anderson, Mason Thomas, Isabella Taylor, and James Jackson.

---

## Join queries

### 4. Teacher with the most course offerings

**Question:** Which teacher teaches the most courses?

**Generated SQL:**
```sql
SELECT t.name, COUNT(co.id) AS course_count
FROM teachers t
JOIN course_offerings co ON co.teacher_id = t.id
GROUP BY t.id, t.name
ORDER BY course_count DESC
LIMIT 1
```

**Answer:** Based on the data, **Dr. Alice Nguyen** teaches the most courses, with a total of **6 courses**.

---

### 5. Courses offered in a given semester

**Question:** Which courses were offered in 2025-Spring?

**Generated SQL:**
```sql
SELECT c.id, c.title, c.credits
FROM courses c
JOIN course_offerings co ON c.id = co.course_id
WHERE co.semester = '2025-Spring'
```

**Answer:** Four courses were offered in 2025-Spring: CS101: Intro to Programming, MA201: Calculus I, CS301: Data Structures, and MA301: Linear Algebra.

---

### 6. Teacher with no course offerings (LEFT JOIN edge case)

**Question:** Which teacher has no course offerings?

**Generated SQL:**
```sql
SELECT t.id, t.name
FROM teachers t
LEFT JOIN course_offerings co ON t.id = co.teacher_id
WHERE co.id IS NULL;
```

**Answer:** Based on the query results, **Dr. Carol Diaz** (ID: 3) is the teacher who has no course offerings.

---

## Aggregation queries

### 7. Top student by average grade (3-table join)

**Question:** Which student has the highest average grade?

**Generated SQL:**
```sql
SELECT s.name, AVG(e.grade) AS avg_grade
FROM students s
JOIN enrollments e ON s.id = e.student_id
GROUP BY s.id, s.name
ORDER BY avg_grade DESC
LIMIT 1
```

**Answer:** Based on the query results, **Emma Wilson** has the highest average grade with an average of **86.75**.

---

### 8. Average grade per semester (GROUP BY)

**Question:** What is the average grade per semester?

**Generated SQL:**
```sql
SELECT co.semester, AVG(e.grade) AS average_grade
FROM enrollments e
JOIN course_offerings co ON e.offering_id = co.id
GROUP BY co.semester;
```

**Answer:** The average grade for the **2024-Fall** semester was **76.5**, and for the **2025-Spring** semester it was approximately **76.42**.

---

### 9. Student enrolled in the most courses

**Question:** Which student is enrolled in the most courses?

**Generated SQL:**
```sql
SELECT s.name, COUNT(e.id) AS course_count
FROM students s
JOIN enrollments e ON e.student_id = s.id
GROUP BY s.id, s.name
ORDER BY course_count DESC
LIMIT 1
```

**Answer:** Based on the query results, **Olivia Brown** is enrolled in the most courses, with a total of **5 courses**.

---

## Edge-case queries

### 10. Enrollments with no grade recorded (NULL handling)

**Question:** How many enrollments have no grade recorded?

**Generated SQL:**
```sql
SELECT COUNT(*) FROM enrollments WHERE grade IS NULL;
```

**Answer:** Based on the query results, there are **3 enrollments** that have no grade recorded.
