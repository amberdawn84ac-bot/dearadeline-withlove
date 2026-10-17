from contextlib import asynccontextmanager
from datetime import datetime
import re
from unittest.mock import AsyncMock

import pytest
from fastapi import HTTPException
from app.api import reading_session as api


def record(**changes):
    row = dict(id='session-1', studentId='student-1', bookId='book-1',
               status='reading', startedAt=datetime(2026, 10, 17), completedAt=None,
               pagesRead=0, totalPages=None, currentLocation=None,
               studentReflection=None, minutesRead=0)
    return row | changes


def connection(monkeypatch, rows):
    conn = AsyncMock()
    conn.fetchrow.side_effect = rows
    @asynccontextmanager
    async def get_conn():
        yield conn
    monkeypatch.setattr(api, '_get_conn', get_conn)
    monkeypatch.setattr(api, '_ensure_reading_session_columns', AsyncMock())
    return conn


@pytest.mark.asyncio
async def test_add_book_uses_database_clock(monkeypatch):
    conn = connection(monkeypatch, [{'id': 'book-1'}, record(status='wishlist')])
    result = await api.create_reading_session(api.SessionCreateRequest(book_id='book-1', status='wishlist'), 'student-1')
    query, *values = conn.fetchrow.call_args.args
    assert len(values) == 4
    assert 'NOW()' in query
    assert result.status == 'wishlist'


@pytest.mark.asyncio
@pytest.mark.parametrize('changes', [{}, {'status': 'reading'}, {'pages_read': 12, 'reading_minutes': 9, 'current_location': 'chapter-2'}, {'status': 'finished', 'pages_read': 80, 'total_pages': 80}])
async def test_progress_parameters_match_text_ids_and_supplied_fields(monkeypatch, changes):
    conn = connection(monkeypatch, [record(), record(**({'status': changes['status']} if 'status' in changes else {}))])
    await api.update_reading_session('session-1', api.SessionUpdateRequest(**changes), 'student-1')
    query, *values = conn.fetchrow.call_args.args
    assert sorted(set(map(int, re.findall(r'\$(\d+)', query)))) == list(range(1, len(values) + 1))
    assert values[-2:] == ['session-1', 'student-1']
    assert '::uuid' not in query
    assert 'NOW()' in query


@pytest.mark.asyncio
async def test_progress_keeps_student_ownership_check(monkeypatch):
    conn = connection(monkeypatch, [record(studentId='another-student')])
    with pytest.raises(HTTPException) as error:
        await api.update_reading_session('session-1', api.SessionUpdateRequest(status='reading'), 'student-1')
    assert error.value.status_code == 403
    assert conn.fetchrow.call_count == 1


def test_imported_book_can_open_before_reading_level_is_assigned():
    from app.api.books import BookDetailResponse
    book = BookDetailResponse(id='book-1', title='A classic', author='Author',
                              track='ENGLISH_LITERATURE', lexile_level=None, grade_band=None)
    assert book.lexile_level is None
