-- Minimal starter catalog for local/dev testing. Not exhaustive — more
-- items/achievements get added by the dev team directly as content grows
-- (no create-item API in v1, per the design spec).
INSERT INTO "Item" (name, type, description) VALUES
    ('Hammer', 'tool', 'For building and repairing.'),
    ('Plywood Sheet', 'material', 'Sturdy building material.'),
    ('Seed Packet', 'material', 'Plant something with this.')
ON CONFLICT DO NOTHING;

INSERT INTO "Achievement" (key, name, description, icon) VALUES
    ('first_town', 'Town Founder', 'Created or joined your first town.', '🏘️'),
    ('first_trade', 'First Trade', 'Contributed an item to the town supply.', '🤝')
ON CONFLICT (key) DO NOTHING;
