# Everett Fox Bible Translation Data

This directory contains text files for the Everett Fox translation of the Hebrew Bible.

## File Format

Each book should be a `.txt` file with the following format:

```
Chapter 1
1 In the beginning, God created the heavens and the earth.
2 And the earth was formless and void...

Chapter 2
1 Thus the heavens and the earth were finished...
```

## How to Add Books

1. Create a text file named after the book (e.g., `genesis.txt`, `exodus.txt`)
2. Format the text with chapter headers and verse numbers
3. Run the seed script:

```bash
# Seed a single book
python scripts/seed_bible_everett_fox.py --book genesis

# Seed all available books
python scripts/seed_bible_everett_fox.py --all
```

## Supported Books

See `scripts/seed_bible_everett_fox.py` for the full list of supported books and their metadata.

## Track Assignments

- **TRUTH_HISTORY**: Genesis, Exodus, Numbers, Joshua, Judges, Samuel
- **DISCIPLESHIP**: Leviticus, Deuteronomy
- **ENGLISH_LITERATURE**: Psalms

## Source

Everett Fox's translations are published by Schocken Books:
- *The Five Books of Moses* (1995)
- *The Early Prophets* (2014)
- *The Book of Psalms* (2023)
