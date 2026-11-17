

CREATE DATABASE IF NOT EXISTS restaurant_db;

USE restaurant_db;


CREATE TABLE users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    email VARCHAR(255) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    
    role ENUM('customer', 'staff') NOT NULL DEFAULT 'customer'
    );



CREATE TABLE restaurant_tables (
    id INT AUTO_INCREMENT PRIMARY KEY,
    table_number INT NOT NULL UNIQUE,
    capacity INT NOT NULL,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    
    CHECK (capacity > 0)
    );


CREATE TABLE time_slots (
    id INT AUTO_INCREMENT PRIMARY KEY,
    start_time TIME NOT NULL UNIQUE,
    end_time TIME NOT NULL,

    CHECK (start_time < end_time)
    );





#===============================================================================
    
CREATE TABLE reservations (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    table_id INT NOT NULL,
    slot_id INT NOT NULL,
    reservation_date DATE NOT NULL,
    status ENUM('confirmed', 'cancelled')
        NOT NULL DEFAULT 'confirmed',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    active_table_id INT GENERATED ALWAYS AS (
        CASE
            WHEN status = 'confirmed' THEN table_id
            ELSE NULL
        END
    ) STORED,

    FOREIGN KEY (user_id) REFERENCES users(id),
    FOREIGN KEY (table_id) REFERENCES restaurant_tables(id),
    FOREIGN KEY (slot_id) REFERENCES time_slots(id),

    UNIQUE KEY unique_active_booking (
        active_table_id,
        reservation_date,
        slot_id
        ),

    INDEX idx_reservation_user (user_id),
    INDEX idx_reservation_date (reservation_date, slot_id)
    );






#===============================================================================

CREATE TABLE waitlist_entries (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    reservation_date DATE NOT NULL,
    slot_id INT NOT NULL,
    party_size INT NOT NULL,
    status ENUM('waiting', 'promoted', 'removed')
        NOT NULL DEFAULT 'waiting',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (user_id) REFERENCES users(id),
    FOREIGN KEY (slot_id) REFERENCES time_slots(id),

    CHECK (party_size > 0),

    INDEX idx_waitlist_queue (
        reservation_date,
        slot_id,
        status,
        created_at,
        id
        )
);