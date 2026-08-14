-- Normalize the legacy Book columns used by the Reading Nook and seed a
-- dependable starter library. Every source is a public-domain EPUB.
ALTER TABLE "Book" ADD COLUMN IF NOT EXISTS source_library TEXT;
ALTER TABLE "Book" ADD COLUMN IF NOT EXISTS total_pages INTEGER;
ALTER TABLE "Book" ADD COLUMN IF NOT EXISTS created_at TIMESTAMPTZ NOT NULL DEFAULT now();
ALTER TABLE "Book" ADD COLUMN IF NOT EXISTS "coverUrl" TEXT;
ALTER TABLE "Book" ADD COLUMN IF NOT EXISTS "sourceLibrary" TEXT;
ALTER TABLE "Book" ADD COLUMN IF NOT EXISTS "isDownloaded" BOOLEAN NOT NULL DEFAULT FALSE;
ALTER TABLE "Book" ADD COLUMN IF NOT EXISTS format TEXT NOT NULL DEFAULT 'epub';
ALTER TABLE "Book" ADD COLUMN IF NOT EXISTS "storageKey" TEXT;
ALTER TABLE "Book" ADD COLUMN IF NOT EXISTS "gutenbergId" TEXT;

UPDATE "Book" SET
  source_library = COALESCE(source_library, "sourceLibrary"),
  total_pages = COALESCE(total_pages, "totalPages"),
  "coverUrl" = COALESCE("coverUrl", "coverImageUrl"),
  lexile_level = COALESCE(lexile_level, "lexileLevel"),
  grade_band = COALESCE(grade_band, "gradeBand"),
  source_url = COALESCE(source_url, "sourceUrl")
WHERE source_library IS NULL OR total_pages IS NULL OR "coverUrl" IS NULL
   OR lexile_level IS NULL OR grade_band IS NULL OR source_url IS NULL;

INSERT INTO "Book" (
  id, title, author, description, track, "gradeBand", "lexileLevel",
  "coverImageUrl", "sourceUrl", "totalPages", "createdAt", "updatedAt",
  source_url, lexile_level, grade_band, source_library, total_pages, "coverUrl"
) VALUES
('da-book-alice','Alice''s Adventures in Wonderland','Lewis Carroll','A curious child follows a white rabbit into a playful world of logic, language, and imagination.','ENGLISH_LITERATURE','3-5',590,'https://www.gutenberg.org/cache/epub/11/pg11.cover.medium.jpg','https://www.gutenberg.org/ebooks/11.epub3.images',160,now(),now(),'https://www.gutenberg.org/ebooks/11.epub3.images',590,'3-5','Project Gutenberg',160,'https://www.gutenberg.org/cache/epub/11/pg11.cover.medium.jpg'),
('da-book-secret-garden','The Secret Garden','Frances Hodgson Burnett','A neglected garden and an unlikely friendship become a story of healing, responsibility, and renewal.','HOMESTEADING','4-6',710,'https://www.gutenberg.org/cache/epub/17396/pg17396.cover.medium.jpg','https://www.gutenberg.org/ebooks/17396.epub3.images',270,now(),now(),'https://www.gutenberg.org/ebooks/17396.epub3.images',710,'4-6','Project Gutenberg',270,'https://www.gutenberg.org/cache/epub/17396/pg17396.cover.medium.jpg'),
('da-book-black-beauty','Black Beauty','Anna Sewell','A horse tells his own life story, inviting careful thought about stewardship, work, kindness, and cruelty.','JUSTICE_CHANGEMAKING','4-7',700,'https://www.gutenberg.org/cache/epub/271/pg271.cover.medium.jpg','https://www.gutenberg.org/ebooks/271.epub3.images',250,now(),now(),'https://www.gutenberg.org/ebooks/271.epub3.images',700,'4-7','Project Gutenberg',250,'https://www.gutenberg.org/cache/epub/271/pg271.cover.medium.jpg'),
('da-book-wind-willows','The Wind in the Willows','Kenneth Grahame','Friendship, home, nature, and adventure along an English riverbank.','ENGLISH_LITERATURE','5-8',830,'https://www.gutenberg.org/cache/epub/27805/pg27805.cover.medium.jpg','https://www.gutenberg.org/ebooks/27805.epub3.images',250,now(),now(),'https://www.gutenberg.org/ebooks/27805.epub3.images',830,'5-8','Project Gutenberg',250,'https://www.gutenberg.org/cache/epub/27805/pg27805.cover.medium.jpg'),
('da-book-anne','Anne of Green Gables','L. M. Montgomery','An imaginative orphan transforms a household and community while learning about belonging and responsibility.','ENGLISH_LITERATURE','6-9',900,'https://www.gutenberg.org/cache/epub/45/pg45.cover.medium.jpg','https://www.gutenberg.org/ebooks/45.epub3.images',320,now(),now(),'https://www.gutenberg.org/ebooks/45.epub3.images',900,'6-9','Project Gutenberg',320,'https://www.gutenberg.org/cache/epub/45/pg45.cover.medium.jpg'),
('da-book-treasure-island','Treasure Island','Robert Louis Stevenson','A fast-moving adventure about courage, loyalty, greed, and moral choices.','ENGLISH_LITERATURE','6-9',850,'https://www.gutenberg.org/cache/epub/120/pg120.cover.medium.jpg','https://www.gutenberg.org/ebooks/120.epub3.images',240,now(),now(),'https://www.gutenberg.org/ebooks/120.epub3.images',850,'6-9','Project Gutenberg',240,'https://www.gutenberg.org/cache/epub/120/pg120.cover.medium.jpg'),
('da-book-around-world','Around the World in Eighty Days','Jules Verne','A race around the globe opens conversations about geography, technology, empire, and culture.','TRUTH_HISTORY','6-9',880,'https://www.gutenberg.org/cache/epub/103/pg103.cover.medium.jpg','https://www.gutenberg.org/ebooks/103.epub3.images',220,now(),now(),'https://www.gutenberg.org/ebooks/103.epub3.images',880,'6-9','Project Gutenberg',220,'https://www.gutenberg.org/cache/epub/103/pg103.cover.medium.jpg'),
('da-book-little-women','Little Women','Louisa May Alcott','Four sisters grow through work, creativity, hardship, faith, and family life.','ENGLISH_LITERATURE','7-10',950,'https://www.gutenberg.org/cache/epub/514/pg514.cover.medium.jpg','https://www.gutenberg.org/ebooks/514.epub3.images',500,now(),now(),'https://www.gutenberg.org/ebooks/514.epub3.images',950,'7-10','Project Gutenberg',500,'https://www.gutenberg.org/cache/epub/514/pg514.cover.medium.jpg'),
('da-book-douglass','Narrative of the Life of Frederick Douglass','Frederick Douglass','A primary-source autobiography about slavery, literacy, resistance, and freedom.','JUSTICE_CHANGEMAKING','8-12',1050,'https://www.gutenberg.org/cache/epub/23/pg23.cover.medium.jpg','https://www.gutenberg.org/ebooks/23.epub3.images',160,now(),now(),'https://www.gutenberg.org/ebooks/23.epub3.images',1050,'8-12','Project Gutenberg',160,'https://www.gutenberg.org/cache/epub/23/pg23.cover.medium.jpg'),
('da-book-pride-prejudice','Pride and Prejudice','Jane Austen','A sharp study of character, family, class, money, judgment, and marriage.','ENGLISH_LITERATURE','9-12',1000,'https://www.gutenberg.org/cache/epub/1342/pg1342.cover.medium.jpg','https://www.gutenberg.org/ebooks/1342.epub3.images',430,now(),now(),'https://www.gutenberg.org/ebooks/1342.epub3.images',1000,'9-12','Project Gutenberg',430,'https://www.gutenberg.org/cache/epub/1342/pg1342.cover.medium.jpg'),
('da-book-frankenstein','Frankenstein','Mary Shelley','A foundational novel about creation, responsibility, scientific ambition, isolation, and human dignity.','CREATION_SCIENCE','9-12',1070,'https://www.gutenberg.org/cache/epub/84/pg84.cover.medium.jpg','https://www.gutenberg.org/ebooks/84.epub3.images',280,now(),now(),'https://www.gutenberg.org/ebooks/84.epub3.images',1070,'9-12','Project Gutenberg',280,'https://www.gutenberg.org/cache/epub/84/pg84.cover.medium.jpg'),
('da-book-federalist','The Federalist Papers','Alexander Hamilton, James Madison, and John Jay','Primary arguments for the United States Constitution, best read critically beside Anti-Federalist writings.','GOVERNMENT_ECONOMICS','10-12',1200,'https://www.gutenberg.org/cache/epub/1404/pg1404.cover.medium.jpg','https://www.gutenberg.org/ebooks/1404.epub3.images',650,now(),now(),'https://www.gutenberg.org/ebooks/1404.epub3.images',1200,'10-12','Project Gutenberg',650,'https://www.gutenberg.org/cache/epub/1404/pg1404.cover.medium.jpg')
ON CONFLICT (id) DO UPDATE SET
  title=EXCLUDED.title, author=EXCLUDED.author, description=EXCLUDED.description,
  track=EXCLUDED.track, "gradeBand"=EXCLUDED."gradeBand", "lexileLevel"=EXCLUDED."lexileLevel",
  "coverImageUrl"=EXCLUDED."coverImageUrl", "sourceUrl"=EXCLUDED."sourceUrl",
  source_url=EXCLUDED.source_url, lexile_level=EXCLUDED.lexile_level,
  grade_band=EXCLUDED.grade_band, source_library=EXCLUDED.source_library,
  total_pages=EXCLUDED.total_pages, "coverUrl"=EXCLUDED."coverUrl", "updatedAt"=now();
