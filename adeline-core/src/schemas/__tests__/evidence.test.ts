import { describe, it, expect } from 'vitest';
import {
  SourceType,
  SOURCE_TYPE_LABELS,
  DECLASSIFIED_COLLECTIONS,
} from '../evidence';

describe('SourceType enum and constants', () => {
  it('should export SourceType enum with all required values', () => {
    expect(SourceType.PRIMARY_SOURCE).toBe('PRIMARY_SOURCE');
    expect(SourceType.DECLASSIFIED_GOV).toBe('DECLASSIFIED_GOV');
    expect(SourceType.ARCHIVE_ORG).toBe('ARCHIVE_ORG');
    expect(SourceType.ACADEMIC_JOURNAL).toBe('ACADEMIC_JOURNAL');
    expect(SourceType.PERSONAL_COLLECTION).toBe('PERSONAL_COLLECTION');
  });

  it('should export SOURCE_TYPE_LABELS mapping', () => {
    expect(SOURCE_TYPE_LABELS['PRIMARY_SOURCE']).toBe('Primary Source');
    expect(SOURCE_TYPE_LABELS['DECLASSIFIED_GOV']).toBe('Declassified Document');
    expect(SOURCE_TYPE_LABELS['ARCHIVE_ORG']).toBe('Archive.org');
    expect(SOURCE_TYPE_LABELS['ACADEMIC_JOURNAL']).toBe('Academic Journal');
    expect(SOURCE_TYPE_LABELS['PERSONAL_COLLECTION']).toBe('Personal Collection');
  });

  it('should export DECLASSIFIED_COLLECTIONS with archive URLs', () => {
    expect(DECLASSIFIED_COLLECTIONS['NARA']).toContain('catalog.archives.gov');
    expect(DECLASSIFIED_COLLECTIONS['CIA_FOIA']).toContain('cia.gov');
    expect(DECLASSIFIED_COLLECTIONS['FBI_VAULT']).toContain('vault.fbi.gov');
    expect(DECLASSIFIED_COLLECTIONS['CONGRESSIONAL_RECORD']).toContain('congress.gov');
    expect(DECLASSIFIED_COLLECTIONS['FEDERAL_REGISTER']).toContain('federalregister.gov');
    expect(DECLASSIFIED_COLLECTIONS['DNSA']).toContain('nsarchive.gwu.edu');
  });

  it('should have all SOURCE_TYPE_LABELS keys match SourceType values', () => {
    const sourceTypeValues = Object.values(SourceType);
    const labelKeys = Object.keys(SOURCE_TYPE_LABELS);
    expect(labelKeys.sort()).toEqual(sourceTypeValues.sort());
  });
});
