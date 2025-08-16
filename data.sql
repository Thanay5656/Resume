CREATE TABLE candidates (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255),
    email VARCHAR(255),
    phone VARCHAR(50)
);

CREATE TABLE skills (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) UNIQUE
);

CREATE TABLE candidate_skills (
    candidate_id INT REFERENCES candidates(id),
    skill_id INT REFERENCES skills(id),
    PRIMARY KEY (candidate_id, skill_id)
);

CREATE TABLE education (
    id SERIAL PRIMARY KEY,
    candidate_id INT REFERENCES candidates(id),
    degree VARCHAR(255),
    institution VARCHAR(255),
    year VARCHAR(10)
);
