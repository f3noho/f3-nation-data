"""Test the F3 test fixtures from conftest.py."""

from sqlalchemy.orm import Session

from f3_nation_data.models.sql.ao import SqlAOModel
from f3_nation_data.models.sql.beatdown import SqlBeatDownModel
from f3_nation_data.models.sql.user import SqlUserModel


def test_f3_fixtures_basic_functionality(f3_test_session: Session) -> None:
    """Test that our F3 fixtures work correctly with basic queries."""
    # Test that we can query each table and get data
    ao_count = f3_test_session.query(SqlAOModel).count()
    user_count = f3_test_session.query(SqlUserModel).count()
    beatdown_count = f3_test_session.query(SqlBeatDownModel).count()

    # Verify we have data (based on our JSON fixtures)
    assert ao_count > 0, 'Should have AO records'
    assert user_count > 0, 'Should have user records'
    assert beatdown_count > 0, 'Should have beatdown records'

    # Test specific records exist
    depot = f3_test_session.query(SqlAOModel).filter_by(ao='The Depot').first()
    assert depot is not None, 'Should find The Depot AO'
    assert depot.channel_id == 'C04PD48V9KR'

    steubie = f3_test_session.query(SqlUserModel).filter_by(user_name='Steubie').first()
    assert steubie is not None, 'Should find Steubie user'
    assert steubie.user_id == 'U04SUMEGFRV'

    # Test beatdown with composite primary key
    beatdown = (
        f3_test_session.query(SqlBeatDownModel)
        .filter_by(
            ao_id='C04PD48V9KR',
            bd_date='2024-03-09',
            q_user_id='U04SUMEGFRV',
        )
        .first()
    )
    assert beatdown is not None, 'Should find specific beatdown'
    assert beatdown.pax_count == 7


def test_f3_fixtures_data_relationships(f3_test_session: Session) -> None:
    """Test that the fixture data has proper relationships."""
    # Get a beatdown and verify its related AO and user exist
    beatdown = f3_test_session.query(SqlBeatDownModel).first()
    assert beatdown is not None

    # Verify the AO exists
    ao = f3_test_session.query(SqlAOModel).filter_by(channel_id=beatdown.ao_id).first()
    assert ao is not None, f'AO {beatdown.ao_id} should exist'

    # Verify the Q user exists
    q_user = f3_test_session.query(SqlUserModel).filter_by(user_id=beatdown.q_user_id).first()
    assert q_user is not None, f'Q user {beatdown.q_user_id} should exist'

    # If there's a COQ user, verify they exist too
    if beatdown.coq_user_id:
        coq_user = f3_test_session.query(SqlUserModel).filter_by(user_id=beatdown.coq_user_id).first()
        assert coq_user is not None, f'COQ user {beatdown.coq_user_id} should exist'
