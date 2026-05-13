-- Fix null emails and roles in User table before schema migration
UPDATE "User" SET email = CONCAT('user_', id, '@placeholder.com') WHERE email IS NULL;
UPDATE "User" SET role = 'STUDENT' WHERE role IS NULL;
